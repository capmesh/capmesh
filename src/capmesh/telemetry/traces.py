from __future__ import annotations

import json
import sqlite3

from capmesh.models.resolution import ResolutionTrace

_TRACE_SCHEMA = """
CREATE TABLE IF NOT EXISTS resolution_traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT UNIQUE NOT NULL,
    timestamp TEXT NOT NULL,
    data TEXT NOT NULL
);
"""


class TraceStore:
    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db

    def init_schema(self) -> None:
        self._db.executescript(_TRACE_SCHEMA)

    def save_trace(self, trace: ResolutionTrace) -> None:
        data = trace.model_dump_json()
        self._db.execute(
            "INSERT OR REPLACE INTO resolution_traces (trace_id, timestamp, data) VALUES (?, ?, ?)",
            (trace.trace_id, trace.timestamp.isoformat(), data),
        )
        self._db.commit()

    def get_trace(self, trace_id: str) -> ResolutionTrace | None:
        row = self._db.execute(
            "SELECT data FROM resolution_traces WHERE trace_id=?",
            (trace_id,),
        ).fetchone()
        if row is None:
            return None
        return ResolutionTrace.model_validate_json(row["data"])

    def list_traces(self, limit: int = 50) -> list[ResolutionTrace]:
        rows = self._db.execute(
            "SELECT data FROM resolution_traces ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [ResolutionTrace.model_validate_json(r["data"]) for r in rows]
