"""Journal storage tests for saved decisions."""

import json
from pathlib import Path

from app.storage import delete_decision, get_decision, list_decisions, save_decision


def test_journal_can_save_list_and_delete_decisions(tmp_path: Path) -> None:
    db_path = tmp_path / "journal.sqlite3"
    created = save_decision(
        decision_id="demo-1",
        title="Laptop",
        description="Example",
        decision={"options": ["A", "B"], "criteria": [{"name": "Price", "direction": "cost", "weight": 4}]},
        analysis={"normalized_weights": {"Price": 1.0}, "options": []},
        notes="I keep this one.",
        created_at="2026-10-25T00:00:00Z",
        updated_at="2026-10-25T00:00:00Z",
        path=db_path,
    )
    assert created["title"] == "Laptop"
    assert len(list_decisions(db_path)) == 1
    assert get_decision("demo-1", db_path)["notes"] == "I keep this one."
    assert delete_decision("demo-1", db_path) is True
    assert list_decisions(db_path) == []
