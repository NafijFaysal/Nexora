"""SQLite-backed journal storage for saved decision records."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "whatif_journal.db"


def initialize_database(path: str | Path | None = None) -> str:
    """Create the journal table if needed and return the database path."""
    db_path = Path(path) if path is not None else DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                decision_json TEXT NOT NULL,
                analysis_json TEXT,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.commit()
    return str(db_path)


def get_connection(path: str | Path | None = None) -> sqlite3.Connection:
    db_path = initialize_database(path)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    payload = {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "decision": json.loads(row["decision_json"]),
        "analysis": json.loads(row["analysis_json"]) if row["analysis_json"] else None,
        "notes": row["notes"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    return payload


def list_decisions(path: str | Path | None = None) -> list[dict[str, Any]]:
    with get_connection(path) as connection:
        rows = connection.execute(
            "SELECT * FROM decisions ORDER BY updated_at DESC, created_at DESC"
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_decision(decision_id: str, path: str | Path | None = None) -> dict[str, Any] | None:
    with get_connection(path) as connection:
        row = connection.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,)).fetchone()
    return None if row is None else _row_to_dict(row)


def save_decision(
    *,
    decision_id: str,
    title: str,
    description: str,
    decision: dict[str, Any],
    analysis: dict[str, Any] | None,
    notes: str,
    created_at: str,
    updated_at: str,
    path: str | Path | None = None,
) -> dict[str, Any]:
    with get_connection(path) as connection:
        connection.execute(
            """
            INSERT INTO decisions (id, title, description, decision_json, analysis_json, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                description = excluded.description,
                decision_json = excluded.decision_json,
                analysis_json = excluded.analysis_json,
                notes = excluded.notes,
                updated_at = excluded.updated_at
            """,
            (
                decision_id,
                title,
                description,
                json.dumps(decision, ensure_ascii=False),
                json.dumps(analysis, ensure_ascii=False) if analysis is not None else None,
                notes,
                created_at,
                updated_at,
            ),
        )
        connection.commit()
    return get_decision(decision_id, path) or {}


def delete_decision(decision_id: str, path: str | Path | None = None) -> bool:
    with get_connection(path) as connection:
        cursor = connection.execute("DELETE FROM decisions WHERE id = ?", (decision_id,))
        connection.commit()
    return cursor.rowcount > 0
