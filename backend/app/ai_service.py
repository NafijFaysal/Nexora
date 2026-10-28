"""Gemini-backed AI service boundary for decision drafting.

This module never fabricates final numbers or rankings. It helps turn a natural
language description into a reviewable draft that can be edited before the
existing decision engine is run.
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
import time
from collections.abc import Sequence
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError, ServerError
from pydantic import ValidationError

from app.api.schemas import AIChatMessage, AIChatResponse, AIDecisionDraft

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
logger = logging.getLogger(__name__)

AI_PROVIDER_ENV = "AI_PROVIDER"
AI_API_KEY_ENV = "AI_API_KEY"
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
AI_MODEL_ENV = "AI_MODEL"
GEMINI_MODEL_ENV = "GEMINI_MODEL"
AI_API_BASE_URL_ENV = "AI_API_BASE_URL"
AI_PARSING_ENABLED_ENV = "AI_PARSING_ENABLED"
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
MAX_GEMINI_RETRIES = 3
MAX_TOTAL_RETRY_WAIT_SECONDS = 15.0
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class AIServiceError(RuntimeError):
    """Raised when the configured provider fails or returns invalid data."""


class AIServiceUnavailableError(RuntimeError):
    """Raised when the AI feature is disabled or not set up."""


class AIServiceRateLimitError(AIServiceError):
    """Raised when the provider rejects requests due to rate limiting."""


class AIServiceTransientError(AIServiceError):
    """Raised when the provider is overloaded or temporarily unavailable."""


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _effective_provider() -> str:
    return (os.environ.get(AI_PROVIDER_ENV) or "gemini").strip().lower() or "gemini"


def _effective_api_key() -> str:
    return (os.environ.get(GEMINI_API_KEY_ENV) or os.environ.get(AI_API_KEY_ENV) or "").strip()


def _effective_model() -> str:
    return (os.environ.get(AI_MODEL_ENV) or os.environ.get(GEMINI_MODEL_ENV) or DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL


def _status_code_for_exception(exc: Exception) -> int | None:
    for attr in ("status_code", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    if response is not None:
        status = getattr(response, "status_code", None)
        if isinstance(status, int):
            return status
        status = getattr(response, "status", None)
        if isinstance(status, int):
            return status
    details = getattr(exc, "details", None)
    if isinstance(details, dict):
        status = details.get("status")
        if isinstance(status, int):
            return status
    return None


def _is_retry_after_header(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _retry_after_seconds(exc: Exception) -> float | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    retry_after = None
    if isinstance(headers, dict):
        retry_after = headers.get("Retry-After")
    elif headers is not None:
        retry_after = getattr(headers, "get", lambda *_args, **_kwargs: None)("Retry-After")
    if not _is_retry_after_header(retry_after):
        return None

    raw = str(retry_after).strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        pass

    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    delta = parsed - datetime.now(timezone.utc)
    return max(0.0, delta.total_seconds())


def _transient_error_message(message: str) -> bool:
    lowered = message.lower()
    transient_patterns = (
        "429",
        "rate limit",
        "quota",
        "too many requests",
        "temporarily unavailable",
        "temporarily overloaded",
        "high demand",
        "overloaded",
        "timeout",
        "timed out",
        "network",
        "connection reset",
        "connection aborted",
        "503",
        "500",
        "502",
        "504",
    )
    return any(pattern in lowered for pattern in transient_patterns)


def _should_retry(exc: Exception) -> bool:
    status_code = _status_code_for_exception(exc)
    if status_code in RETRYABLE_STATUS_CODES:
        return True
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True
    message = _friendly_error_message(str(exc))
    return _transient_error_message(message)


def _compute_retry_delay(attempt_index: int, exc: Exception) -> float:
    retry_after = _retry_after_seconds(exc)
    if retry_after is not None:
        return min(max(retry_after, 0.0), MAX_TOTAL_RETRY_WAIT_SECONDS)

    base_delay = min(0.75 * (2 ** attempt_index), 6.0)
    jitter = random.uniform(0.0, min(base_delay * 0.35, 1.5))
    return min(base_delay + jitter, MAX_TOTAL_RETRY_WAIT_SECONDS)


def get_ai_status() -> dict[str, Any]:
    """Return the runtime AI configuration state for the UI and API."""
    enabled = _truthy(os.environ.get(AI_PARSING_ENABLED_ENV)) or bool(_effective_api_key())
    provider = _effective_provider()
    api_key = _effective_api_key()
    model = _effective_model()
    if not enabled:
        return {
            "available": False,
            "provider": "not-configured",
            "requires_configuration": True,
            "message": "AI Assistant is unavailable. Manual Setup remains fully available without a configured AI provider.",
        }
    if not api_key:
        return {
            "available": False,
            "provider": provider,
            "requires_configuration": True,
            "message": "Gemini API key is missing. Add GEMINI_API_KEY to backend/.env and restart the backend to enable AI assistance.",
        }
    if not model:
        return {
            "available": False,
            "provider": provider,
            "requires_configuration": True,
            "message": "No Gemini model is configured. Set AI_MODEL or GEMINI_MODEL in the backend environment.",
        }
    return {
        "available": True,
        "provider": provider,
        "requires_configuration": False,
        "message": "AI Assistant is ready to help build a structured decision draft.",
    }


def _build_system_prompt() -> str:
    return (
        "You help a user build a structured decision draft for a decision-intelligence workflow. "
        "Never invent facts, prices, measurements, scores, evidence, deadlines, or real-world facts. "
        "When a user asks for a random or example decision, prefer a realistic personal academic scenario such as prioritizing study tasks before exams unless they explicitly ask about universities or graduate programs. "
        "For example, a good random academic study example is: 'Which study task should I focus on first before upcoming exams?' with options like Mathematics practice, Chemistry revision, Biology revision; criteria like Exam urgency, Topic difficulty, Current preparation gap, and Marks importance. "
        "If a criterion is defined as being higher when more urgent, more difficult, more important, or more behind, then direction should be 'benefit'. Use 'cost' only for criteria where lower is better, such as time required or cost. "
        "Use null for any unknown numeric value and leave missing information explicitly unknown. "
        "Do not ask for information already provided. Ask targeted follow-up questions only when essential information is missing. "
        "For explicit hypothetical examples, use illustrative numbers only and note that they are illustrative in the notes field. "
        "For real personal decisions, leave unknowns empty and ask focused questions instead of guessing. "
        "Return valid JSON only with this exact shape: "
        "{\"title\":\"string\",\"description\":\"string\",\"options\":[\"string\"],\"criteria\":[{\"name\":\"string\",\"direction\":\"benefit|cost\",\"weight\":number|null,\"unit\":\"string\"}],\"values\":{\"optionName\":{\"criterionName\":number|null}},\"constraints\":[{\"criterion\":\"string\",\"operator\":\"<=|>=\",\"threshold\":number}],\"unknowns\":[\"string\"],\"notes\":\"string\"}. "
        "If the user has not provided a budget, deadline, or measurement, leave them out or call them out in unknowns. "
        "Keep every suggested option, criterion, and constraint reviewable by the user. "
        "Do not produce scores or final rankings. "
        "If the user is vague, propose a few reasonable candidate options and criteria but clearly label unknown values and avoid invented fact patterns."
    )


def _gemini_payload(messages: Sequence[AIChatMessage]) -> tuple[str, dict[str, Any]]:
    prompt = "\n\n".join(f"{message.role}: {message.content}" for message in messages)
    config = types.GenerateContentConfig(
        system_instruction=_build_system_prompt(),
        temperature=0.2,
        max_output_tokens=2048,
        response_mime_type="application/json",
    )
    return prompt, {"config": config}


def _extract_text(response: Any) -> str:
    if response is None:
        raise AIServiceError("The Gemini response was empty.")
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()
    if isinstance(response, dict):
        for key in ("text", "content", "output_text"):
            value = response.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    candidates = getattr(response, "candidates", None)
    if isinstance(candidates, list):
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            if content is None and isinstance(candidate, dict):
                content = candidate.get("content")
            if hasattr(content, "parts"):
                parts = content.parts
                strings = []
                for part in parts:
                    part_text = getattr(part, "text", None)
                    if isinstance(part_text, str) and part_text.strip():
                        strings.append(part_text)
                    elif isinstance(part, dict):
                        part_text = part.get("text")
                        if isinstance(part_text, str) and part_text.strip():
                            strings.append(part_text)
                if strings:
                    return "\n".join(strings)
    raise AIServiceError("The Gemini response did not include usable text.")


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL)
        if match:
            text = match.group(1)
    if not text.startswith("{"):
        if text.startswith("["):
            text = text[1:]
        raise AIServiceError("The AI response was not valid JSON for a decision draft.")
    try:
        candidate = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AIServiceError(f"The AI response was not valid JSON: {exc.msg}") from exc
    if not isinstance(candidate, dict):
        raise AIServiceError("The AI response must be a JSON object.")
    return candidate


def _friendly_error_message(message: str) -> str:
    cleaned = message
    for secret_name in (GEMINI_API_KEY_ENV, AI_API_KEY_ENV):
        value = os.environ.get(secret_name, "")
        if value:
            cleaned = cleaned.replace(value, "[REDACTED]")
    cleaned = cleaned.replace("\n", " ")
    return cleaned.strip() or "Gemini API request failed."


def _classify_gemini_exception(exc: Exception) -> RuntimeError:
    message = _friendly_error_message(str(exc))
    lowered = message.lower()
    status_code = _status_code_for_exception(exc)

    if status_code == 429 or "rate limit" in lowered or "quota" in lowered or "too many requests" in lowered:
        return AIServiceRateLimitError("The Gemini API is rate-limited right now. Please wait a moment and try again.")
    if status_code in {401, 403} or "api key" in lowered or "authentication" in lowered or "forbidden" in lowered:
        return AIServiceUnavailableError("The Gemini API key is invalid or missing. Check backend/.env and restart the backend.")
    if status_code in {400, 422} or "malformed" in lowered or "invalid request" in lowered or "bad request" in lowered:
        return AIServiceError("The Gemini request was rejected because the payload or model request was invalid. Review the prompt and try again.")
    if status_code in {404} or "model_not_found" in lowered or "not found" in lowered:
        return AIServiceError("The configured Gemini model is unavailable. The backend is set to the supported stable model 'gemini-3.8-flash'. Check that the account can access it and that the backend is restarted after the .env change.")
    if status_code in {500, 502, 503, 504} or _transient_error_message(message):
        return AIServiceTransientError("The Gemini API is temporarily overloaded or unavailable. Please wait a moment and try again.")
    return AIServiceError(f"Gemini API request failed: {message}")


def _request_provider(messages: Sequence[AIChatMessage]) -> dict[str, Any]:
    status = get_ai_status()
    if not status["available"]:
        raise AIServiceUnavailableError(str(status["message"]))

    provider = _effective_provider().lower()
    if provider not in {"gemini", "google"}:
        raise AIServiceUnavailableError(
            "This project is configured for the Gemini API. Set AI_PROVIDER=gemini or remove the custom provider setting."
        )

    api_key = _effective_api_key()
    if not api_key:
        raise AIServiceUnavailableError("Gemini API key is missing. Add GEMINI_API_KEY to backend/.env.")

    model = _effective_model() or DEFAULT_GEMINI_MODEL
    client = genai.Client(api_key=api_key)
    content, extra = _gemini_payload(messages)

    last_exc: Exception | None = None
    for attempt in range(MAX_GEMINI_RETRIES + 1):
        try:
            response = client.models.generate_content(model=model, contents=content, **extra)
            return _extract_json_object(_extract_text(response))
        except (TypeError, ValueError) as exc:
            logger.warning("Gemini API returned an invalid payload: %s", _friendly_error_message(str(exc)))
            raise AIServiceError(f"The Gemini API returned an invalid response: {_friendly_error_message(str(exc))}") from exc
        except (APIError, ClientError, ServerError) as exc:
            last_exc = exc
            if not _should_retry(exc):
                raise _classify_gemini_exception(exc) from exc
            if attempt >= MAX_GEMINI_RETRIES:
                raise _classify_gemini_exception(exc) from exc
            delay = _compute_retry_delay(attempt, exc)
            logger.warning(
                "Transient Gemini API failure. attempt=%s/%s delay=%.2fs status=%s message=%s",
                attempt + 1,
                MAX_GEMINI_RETRIES + 1,
                delay,
                _status_code_for_exception(exc),
                _friendly_error_message(str(exc)),
            )
            time.sleep(delay)
        except Exception as exc:  # pragma: no cover - defensive guard for transport-level failures
            last_exc = exc
            if not _should_retry(exc):
                raise _classify_gemini_exception(exc) from exc
            if attempt >= MAX_GEMINI_RETRIES:
                raise _classify_gemini_exception(exc) from exc
            delay = _compute_retry_delay(attempt, exc)
            logger.warning("Transient Gemini transport failure. attempt=%s/%s delay=%.2fs message=%s", attempt + 1, MAX_GEMINI_RETRIES + 1, delay, _friendly_error_message(str(exc)))
            time.sleep(delay)

    if last_exc is not None:
        raise _classify_gemini_exception(last_exc) from last_exc
    raise AIServiceError("Gemini API request failed without a response.")


def build_ai_response(messages: Sequence[AIChatMessage]) -> AIChatResponse:
    """Use Gemini to draft a decision structure from chat history."""
    if not messages:
        raise AIServiceUnavailableError("At least one message is required to build a decision draft.")
    payload = _request_provider(messages)
    try:
        draft = AIDecisionDraft.model_validate(payload)
    except ValidationError as exc:
        logger.warning("Gemini draft validation failed: %s", payload)
        raise AIServiceError(
            "The AI-generated draft did not match the expected decision schema. Review the assistant output and try again."
        ) from exc
    return AIChatResponse(
        available=True,
        message=(draft.notes or "I’ve drafted a structured decision for review. You can accept, reject, or revise it."),
        draft=draft,
        warnings=[
            "AI suggestions are reviewable and may require your validation before analysis.",
            "Unknown values remain explicitly unknown instead of being invented.",
        ],
        follow_up_questions=[
            "Do these options and criteria match your real decision?",
            "Are there any missing facts, budget limits, or deadlines we still need to capture?",
        ],
        unknown_fields=list(draft.unknowns or []),
    )
