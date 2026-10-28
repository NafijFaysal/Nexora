"""API routes: health, analysis, templates."""

import json
import uuid
from datetime import datetime, timezone
from functools import cache
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.ai_service import (
    AIServiceError,
    AIServiceRateLimitError,
    AIServiceTransientError,
    AIServiceUnavailableError,
    build_ai_response,
    get_ai_status,
)
from app.api.converters import to_engine_model, to_response
from app.api.schemas import AIChatRequest, AIChatResponse, AnalysisOut, DecisionIn, TemplateOut
from app.engine import ModelValidationError, analyze
from app.storage import delete_decision, get_decision, list_decisions, save_decision

router = APIRouter(prefix="/api")

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ai/status")
def get_ai_configuration() -> dict[str, object]:
    """Expose whether the optional AI assistant is available for the frontend."""
    return get_ai_status()


@router.post("/ai/chat", response_model=AIChatResponse)
def ai_chat(payload: AIChatRequest) -> AIChatResponse:
    """Ask the AI assistant to help shape a structured decision draft."""
    try:
        return build_ai_response(payload.messages)
    except AIServiceUnavailableError as error:
        raise HTTPException(status_code=503, detail={"problems": [str(error)]}) from error
    except AIServiceRateLimitError as error:
        raise HTTPException(status_code=429, detail={"problems": [str(error)]}) from error
    except AIServiceTransientError as error:
        raise HTTPException(status_code=503, detail={"problems": [str(error)]}) from error
    except AIServiceError as error:
        raise HTTPException(status_code=502, detail={"problems": [str(error)]}) from error


@router.post("/analyze", response_model=AnalysisOut)
def analyze_decision(payload: DecisionIn) -> AnalysisOut:
    try:
        result = analyze(to_engine_model(payload))
    except ModelValidationError as error:
        raise HTTPException(status_code=422, detail={"problems": list(error.problems)}) from error
    return to_response(result)


@cache
def load_templates() -> dict[str, TemplateOut]:
    templates = {}
    for path in sorted(TEMPLATES_DIR.glob("*.json")):
        template = TemplateOut.model_validate(json.loads(path.read_text(encoding="utf-8")))
        templates[template.id] = template
    return templates


@router.get("/templates", response_model=list[TemplateOut])
def list_templates() -> list[TemplateOut]:
    return list(load_templates().values())


@router.get("/templates/{template_id}", response_model=TemplateOut)
def get_template(template_id: str) -> TemplateOut:
    template = load_templates().get(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found.")
    return template


@router.get("/journal/decisions")
def list_journal_decisions() -> list[dict]:
    return list_decisions()


@router.get("/journal/decisions/{decision_id}")
def get_journal_decision(decision_id: str) -> dict:
    decision = get_decision(decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found.")
    return decision


@router.post("/journal/decisions")
def save_journal_decision(payload: dict) -> dict:
    title = str(payload.get("title") or "Untitled decision").strip() or "Untitled decision"
    description = str(payload.get("description") or "").strip()
    decision = payload.get("decision")
    analysis = payload.get("analysis")
    notes = str(payload.get("notes") or "").strip()
    if not isinstance(decision, dict):
        raise HTTPException(status_code=422, detail={"problems": ["A saved decision needs a valid payload."]})
    created_at = payload.get("created_at") or datetime.now(timezone.utc).isoformat()
    updated_at = payload.get("updated_at") or created_at
    decision_id = str(payload.get("id") or uuid.uuid4())
    return save_decision(
        decision_id=decision_id,
        title=title,
        description=description,
        decision=decision,
        analysis=analysis if isinstance(analysis, dict) else None,
        notes=notes,
        created_at=created_at,
        updated_at=updated_at,
    )


@router.put("/journal/decisions/{decision_id}")
def update_journal_decision(decision_id: str, payload: dict) -> dict:
    existing = get_decision(decision_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Decision not found.")
    new_payload = {**existing, **payload}
    return save_journal_decision(
        {
            "id": decision_id,
            "title": new_payload.get("title", existing["title"]),
            "description": new_payload.get("description", existing["description"]),
            "decision": new_payload.get("decision", existing["decision"]),
            "analysis": new_payload.get("analysis", existing["analysis"]),
            "notes": new_payload.get("notes", existing["notes"]),
            "created_at": existing["created_at"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )


@router.delete("/journal/decisions/{decision_id}")
def delete_journal_decision(decision_id: str) -> dict:
    if not delete_decision(decision_id):
        raise HTTPException(status_code=404, detail="Decision not found.")
    return {"deleted": True, "id": decision_id}
