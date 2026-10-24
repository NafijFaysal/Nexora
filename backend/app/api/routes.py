"""API routes: health, analysis, templates."""

import json
from functools import cache
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.api.converters import to_engine_model, to_response
from app.api.schemas import AnalysisOut, DecisionIn, TemplateOut
from app.engine import ModelValidationError, analyze

router = APIRouter(prefix="/api")

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/analyze", response_model=AnalysisOut)
def analyze_decision(payload: DecisionIn) -> AnalysisOut:
    try:
        result = analyze(to_engine_model(payload))
    except ModelValidationError as error:
        # Messages come from our own validation rules, never from internal exceptions.
        raise HTTPException(status_code=422, detail={"problems": list(error.problems)}) from error
    return to_response(result)


@cache
def load_templates() -> dict[str, TemplateOut]:
    """Read every bundled template once. The ids come from our own files, never from users."""
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
