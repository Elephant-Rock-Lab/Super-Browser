"""SessionDB — SQLite + FTS5 session storage and cost analytics queries."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from super_browser.tracing.types import CostRecord, SessionSummary, TraceEvent


class SessionDB:

    def __init__(
        self,
        db_path: Path = Path.home() / ".super-browser" / "sessions.db",
    ) -> None:
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                trace_id TEXT NOT NULL,
                started_at REAL NOT NULL,
                ended_at REAL NOT NULL,
                duration_s REAL NOT NULL,
                status TEXT NOT NULL,
                total_actions INTEGER NOT NULL,
                total_cdp_calls INTEGER NOT NULL,
                total_llm_calls INTEGER NOT NULL,
                total_tokens_input INTEGER NOT NULL,
                total_tokens_output INTEGER NOT NULL,
                total_cost_usd REAL NOT NULL,
                error_count INTEGER NOT NULL,
                urls_visited TEXT NOT NULL DEFAULT '[]',
                summary_text TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS cost_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT NOT NULL,
                step_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                token_input INTEGER NOT NULL,
                token_output INTEGER NOT NULL,
                cost_usd REAL NOT NULL,
                timestamp REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS trace_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT NOT NULL,
                step_id INTEGER NOT NULL,
                span_id TEXT NOT NULL,
                span_kind TEXT NOT NULL,
                name TEXT NOT NULL,
                timestamp REAL NOT NULL,
                duration_ms REAL NOT NULL,
                status TEXT NOT NULL,
                parent_span_id TEXT,
                session_id TEXT,
                attributes TEXT NOT NULL DEFAULT '{}',
                token_input INTEGER NOT NULL DEFAULT 0,
                token_output INTEGER NOT NULL DEFAULT 0,
                token_cost_usd REAL NOT NULL DEFAULT 0.0
            );
        """)
        try:
            self._conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts
                USING fts5(summary_text, urls_visited, content=sessions, content_rowid=rowid)
            """)
        except sqlite3.OperationalError:
            pass
        self._conn.commit()

    def _ensure_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.initialize()
        return self._conn  # type: ignore

    def insert_events(self, events: list[TraceEvent]) -> None:
        conn = self._ensure_conn()
        for e in events:
            conn.execute(
                "INSERT INTO trace_events (trace_id, step_id, span_id, span_kind, name, "
                "timestamp, duration_ms, status, parent_span_id, session_id, attributes, "
                "token_input, token_output, token_cost_usd) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (e.trace_id, e.step_id, e.span_id, str(e.span_kind), e.name,
                 e.timestamp, e.duration_ms, str(e.status), e.parent_span_id,
                 e.session_id, json.dumps(e.attributes), e.token_input,
                 e.token_output, e.token_cost_usd),
            )
        conn.commit()

    def save_session(self, summary: SessionSummary) -> None:
        conn = self._ensure_conn()
        urls_json = json.dumps(summary.urls_visited)
        conn.execute(
            "INSERT OR REPLACE INTO sessions "
            "(session_id, trace_id, started_at, ended_at, duration_s, status, "
            "total_actions, total_cdp_calls, total_llm_calls, total_tokens_input, "
            "total_tokens_output, total_cost_usd, error_count, urls_visited, summary_text) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (summary.session_id, summary.trace_id, summary.started_at,
             summary.ended_at, summary.duration_s, summary.status,
             summary.total_actions, summary.total_cdp_calls, summary.total_llm_calls,
             summary.total_tokens_input, summary.total_tokens_output,
             summary.total_cost_usd, summary.error_count, urls_json,
             summary.summary_text),
        )
        try:
            conn.execute(
                "INSERT OR REPLACE INTO sessions_fts (rowid, summary_text, urls_visited) "
                "VALUES ((SELECT rowid FROM sessions WHERE session_id = ?), ?, ?)",
                (summary.session_id, summary.summary_text, urls_json),
            )
        except sqlite3.OperationalError:
            pass
        conn.commit()

    def get_session(self, session_id: str) -> Optional[SessionSummary]:
        conn = self._ensure_conn()
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_summary(row)

    def list_sessions(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> list[SessionSummary]:
        conn = self._ensure_conn()
        if status:
            rows = conn.execute(
                "SELECT * FROM sessions WHERE status = ? ORDER BY started_at DESC LIMIT ? OFFSET ?",
                (status, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [self._row_to_summary(r) for r in rows]

    def search(self, query: str, *, limit: int = 20) -> list[SessionSummary]:
        conn = self._ensure_conn()
        try:
            rows = conn.execute(
                "SELECT s.* FROM sessions s JOIN sessions_fts f ON s.rowid = f.rowid "
                "WHERE sessions_fts MATCH ? LIMIT ?",
                (query, limit),
            ).fetchall()
            return [self._row_to_summary(r) for r in rows]
        except sqlite3.OperationalError:
            rows = conn.execute(
                "SELECT * FROM sessions WHERE summary_text LIKE ? OR urls_visited LIKE ? LIMIT ?",
                (f"%{query}%", f"%{query}%", limit),
            ).fetchall()
            return [self._row_to_summary(r) for r in rows]

    def total_cost(self, *, since: Optional[float] = None) -> float:
        conn = self._ensure_conn()
        if since:
            row = conn.execute(
                "SELECT COALESCE(SUM(total_cost_usd), 0) FROM sessions WHERE started_at >= ?",
                (since,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COALESCE(SUM(total_cost_usd), 0) FROM sessions"
            ).fetchone()
        return row[0] if row else 0.0

    def cost_by_provider(self, session_id: str) -> dict[str, float]:
        conn = self._ensure_conn()
        rows = conn.execute(
            "SELECT provider, SUM(cost_usd) FROM cost_records "
            "WHERE trace_id = (SELECT trace_id FROM sessions WHERE session_id = ?) "
            "GROUP BY provider",
            (session_id,),
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    def cost_by_period(self, start: float, end: float) -> dict[str, float]:
        conn = self._ensure_conn()
        rows = conn.execute(
            "SELECT date(started_at, 'unixepoch') as day, SUM(total_cost_usd) "
            "FROM sessions WHERE started_at BETWEEN ? AND ? GROUP BY day",
            (start, end),
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    def top_expensive_sessions(self, *, limit: int = 10) -> list[SessionSummary]:
        conn = self._ensure_conn()
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY total_cost_usd DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_summary(r) for r in rows]

    def delete_sessions_before(self, timestamp: float) -> int:
        conn = self._ensure_conn()
        cursor = conn.execute(
            "DELETE FROM sessions WHERE ended_at < ?", (timestamp,)
        )
        conn.commit()
        return cursor.rowcount

    def insert_cost_record(self, record: CostRecord) -> None:
        conn = self._ensure_conn()
        conn.execute(
            "INSERT INTO cost_records "
            "(trace_id, step_id, provider, model, token_input, token_output, cost_usd, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (record.trace_id, record.step_id, record.provider, record.model,
             record.token_input, record.token_output, record.cost_usd, record.timestamp),
        )
        conn.commit()

    def _row_to_summary(self, row: tuple) -> SessionSummary:
        urls = json.loads(row[13]) if isinstance(row[13], str) else []
        return SessionSummary(
            session_id=row[0], trace_id=row[1], started_at=row[2],
            ended_at=row[3], duration_s=row[4], status=row[5],
            total_actions=row[6], total_cdp_calls=row[7], total_llm_calls=row[8],
            total_tokens_input=row[9], total_tokens_output=row[10],
            total_cost_usd=row[11], error_count=row[12], urls_visited=urls,
            summary_text=row[14],
        )
