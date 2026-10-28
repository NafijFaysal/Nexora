"""Tests for Gemini retry classification and transient handling."""

from types import SimpleNamespace

import pytest
from google.genai.errors import APIError, ClientError, ServerError

from app.ai_service import (
    AIServiceRateLimitError,
    AIServiceTransientError,
    AIServiceUnavailableError,
    MAX_GEMINI_RETRIES,
    _request_provider,
)
from app.api.schemas import AIChatMessage


def _build_success_response() -> SimpleNamespace:
    text = (
        '{'
        '"title":"Test decision",'
        '"description":"Example scenario",'
        '"options":["A","B"],'
        '"criteria":[{"name":"Score","direction":"benefit","weight":1,"unit":""}],'
        '"values":{"A":{"Score":1},"B":{"Score":2}},'
        '"constraints":[],'
        '"unknowns":[],'
        '"notes":"Illustrative only"'
        '}'
    )
    return SimpleNamespace(text=text)


@pytest.fixture
def ai_messages() -> list[AIChatMessage]:
    return [AIChatMessage(role="user", content="Which option should I choose?")]


def _install_fake_client(monkeypatch, generate_content):
    class FakeClient:
        def __init__(self, api_key: str):
            self.api_key = api_key
            self.models = SimpleNamespace(generate_content=generate_content)

    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("AI_MODEL", "gemini-3.8-flash")
    monkeypatch.setattr("app.ai_service.genai.Client", FakeClient)


def test_retry_on_transient_server_error(monkeypatch, ai_messages) -> None:
    attempts = {"count": 0}

    def generate_content(*args, **kwargs):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ServerError(503, {"error": {"message": "This model is currently experiencing high demand."}}, None)
        return _build_success_response()

    _install_fake_client(monkeypatch, generate_content)

    response = _request_provider(ai_messages)

    assert response["title"] == "Test decision"
    assert attempts["count"] == 3


def test_rate_limit_is_classified_as_429(monkeypatch, ai_messages) -> None:
    def generate_content(*args, **kwargs):
        raise APIError(429, {"error": {"message": "Rate limit exceeded"}}, None)

    _install_fake_client(monkeypatch, generate_content)

    with pytest.raises(AIServiceRateLimitError, match="rate-limited|rate limit"):
        _request_provider(ai_messages)


def test_invalid_credentials_are_not_retried(monkeypatch, ai_messages) -> None:
    attempts = {"count": 0}

    def generate_content(*args, **kwargs):
        attempts["count"] += 1
        raise ClientError(401, {"error": {"message": "API key invalid"}}, None)

    _install_fake_client(monkeypatch, generate_content)

    with pytest.raises(AIServiceUnavailableError, match="invalid or missing"):
        _request_provider(ai_messages)

    assert attempts["count"] == 1


def test_retry_exhaustion_raises_transient_error(monkeypatch, ai_messages) -> None:
    attempts = {"count": 0}

    def generate_content(*args, **kwargs):
        attempts["count"] += 1
        raise ServerError(503, {"error": {"message": "Service is overloaded"}}, None)

    _install_fake_client(monkeypatch, generate_content)

    with pytest.raises(AIServiceTransientError, match="temporarily overloaded|temporarily unavailable"):
        _request_provider(ai_messages)

    assert attempts["count"] == MAX_GEMINI_RETRIES + 1
