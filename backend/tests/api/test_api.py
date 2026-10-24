"""API tests using FastAPI's in-process TestClient (no server is started)."""

import copy

import pytest
from fastapi.testclient import TestClient

from app.api.routes import TEMPLATES_DIR, load_templates
from app.config import Settings
from app.main import app, create_app

client = TestClient(app)

LAPTOP_PAYLOAD = {
    "title": "Laptop",
    "options": ["A", "B", "C"],
    "criteria": [
        {"name": "Price", "direction": "cost", "weight": 4},
        {"name": "Quality", "direction": "benefit", "weight": 6},
    ],
    "values": {
        "A": {"Price": 800, "Quality": 7},
        "B": {"Price": 1000, "Quality": 9},
        "C": {"Price": 600, "Quality": 5},
    },
}


def payload(**changes):
    data = copy.deepcopy(LAPTOP_PAYLOAD)
    data.update(changes)
    return data


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_reference_example() -> None:
    response = client.post("/api/analyze", json=LAPTOP_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert [o["name"] for o in body["options"]] == ["B", "A", "C"]
    assert [o["rank"] for o in body["options"]] == [1, 2, 3]
    assert [o["score"] for o in body["options"]] == pytest.approx([0.6, 0.5, 0.4])
    assert body["normalized_weights"] == pytest.approx({"Price": 0.4, "Quality": 0.6})
    assert body["has_tie_for_first"] is False
    assert any("B ranks first" in sentence for sentence in body["explanation"])
    assert "relative" in body["method"]


def test_analyze_with_constraint_lists_excluded_option_with_reason() -> None:
    constraints = [{"criterion": "Price", "operator": "<=", "threshold": 900}]
    body = client.post("/api/analyze", json=payload(constraints=constraints)).json()
    assert [o["name"] for o in body["options"]] == ["A", "C", "B"]
    excluded = body["options"][2]
    assert excluded["eligible"] is False
    assert excluded["score"] is None
    assert excluded["violations"] == ["Price is 1000, but must be at most 900."]


def test_missing_value_returns_422_with_clear_problem() -> None:
    values = copy.deepcopy(LAPTOP_PAYLOAD["values"])
    del values["C"]["Quality"]
    response = client.post("/api/analyze", json=payload(values=values))
    assert response.status_code == 422
    assert "Missing value: 'C' on 'Quality'." in response.json()["detail"]["problems"]


def test_all_zero_weights_return_422() -> None:
    criteria = [
        {"name": "Price", "direction": "cost", "weight": 0},
        {"name": "Quality", "direction": "benefit", "weight": 0},
    ]
    response = client.post("/api/analyze", json=payload(criteria=criteria))
    assert response.status_code == 422
    assert any("weight above zero" in p for p in response.json()["detail"]["problems"])


def test_negative_weight_rejected_by_schema() -> None:
    criteria = [
        {"name": "Price", "direction": "cost", "weight": -1},
        {"name": "Quality", "direction": "benefit", "weight": 6},
    ]
    assert client.post("/api/analyze", json=payload(criteria=criteria)).status_code == 422


def test_too_many_options_rejected() -> None:
    names = [f"O{i}" for i in range(21)]
    values = {name: {"Price": 1, "Quality": 1} for name in names}
    response = client.post("/api/analyze", json=payload(options=names, values=values))
    assert response.status_code == 422


def test_value_beyond_limit_rejected() -> None:
    values = copy.deepcopy(LAPTOP_PAYLOAD["values"])
    values["A"]["Price"] = 1e13
    assert client.post("/api/analyze", json=payload(values=values)).status_code == 422


def test_unknown_fields_rejected() -> None:
    assert client.post("/api/analyze", json=payload(surprise=1)).status_code == 422


def test_invalid_json_does_not_crash_the_server() -> None:
    response = client.post(
        "/api/analyze", content=b"{not json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422


def test_oversized_body_is_rejected() -> None:
    big = payload(description="x" * 300_000)
    response = client.post("/api/analyze", json=big)
    assert response.status_code == 413


def test_cors_allows_configured_origin_only() -> None:
    allowed = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"
    other = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in other.headers


def test_cors_origins_come_from_settings() -> None:
    custom = TestClient(create_app(Settings(cors_allow_origins=("http://example.test",))))
    response = custom.get("/api/health", headers={"Origin": "http://example.test"})
    assert response.headers.get("access-control-allow-origin") == "http://example.test"


# ---- Templates ------------------------------------------------------------------------------


def test_every_template_file_loads_and_is_valid() -> None:
    files = list(TEMPLATES_DIR.glob("*.json"))
    assert len(files) >= 3
    assert len(load_templates()) == len(files)


def test_templates_are_labelled_illustrative_and_have_a_positive_weight() -> None:
    for template in load_templates().values():
        assert template.illustrative is True
        assert sum(c.weight for c in template.criteria) > 0


def test_list_and_get_templates() -> None:
    listing = client.get("/api/templates")
    assert listing.status_code == 200
    ids = [t["id"] for t in listing.json()]
    assert "laptop-purchase" in ids
    single = client.get("/api/templates/laptop-purchase")
    assert single.status_code == 200
    assert single.json()["name"] == "Laptop purchase"


def test_unknown_template_returns_404() -> None:
    assert client.get("/api/templates/nope").status_code == 404
    assert client.get("/api/templates/..%2Fsecret").status_code == 404
