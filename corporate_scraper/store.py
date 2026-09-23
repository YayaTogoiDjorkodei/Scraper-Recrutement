"""Transactional local study persistence backed by standard-library SQLite."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from typing import Iterator
from uuid import uuid4

from .models import FieldEvidence, JobObservation, RunCounters, RunSpec, TaskKind, TaskStatus
from .extraction import requirement_summary
from .text import description_text


SCHEMA_VERSION = 4


class StudyStore:
    """Owns short-lived SQLite connections so UI and workers never share one."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    state TEXT NOT NULL,
                    spec_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                    task_key TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    completed_at TEXT,
                    UNIQUE(run_id, task_key)
                );
                CREATE TABLE IF NOT EXISTS offers (
                    id INTEGER PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                    source TEXT NOT NULL,
                    source_key TEXT NOT NULL,
                    canonical_url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    company TEXT,
                    location TEXT,
                    posted_text TEXT,
                    skills_json TEXT NOT NULL,
                    experience TEXT,
                    contract TEXT,
                    description TEXT,
                    description_status TEXT NOT NULL,
                    quality TEXT NOT NULL,
                    selection_status TEXT NOT NULL DEFAULT 'selected',
                    qualification_status TEXT NOT NULL DEFAULT 'matching',
                    collected_at TEXT NOT NULL,
                    UNIQUE(run_id, source, source_key)
                );
                CREATE INDEX IF NOT EXISTS offers_run_metadata_idx
                    ON offers(run_id, source, location, description_status);
                CREATE TABLE IF NOT EXISTS evidence (
                    id INTEGER PRIMARY KEY,
                    offer_id INTEGER NOT NULL REFERENCES offers(id) ON DELETE CASCADE,
                    field TEXT NOT NULL,
                    value TEXT NOT NULL,
                    excerpt TEXT NOT NULL,
                    method TEXT NOT NULL,
                    score REAL,
                    rule_version TEXT NOT NULL
                );
                """
            )
            connection.execute(
                "INSERT INTO metadata(key, value) VALUES('schema_version', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (str(SCHEMA_VERSION),),
            )
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(offers)")}
            if "qualification_status" not in columns:
                connection.execute("ALTER TABLE offers ADD COLUMN qualification_status TEXT NOT NULL DEFAULT 'matching'")
            for column in ("education", "raw_description"):
                if column not in columns:
                    connection.execute(f"ALTER TABLE offers ADD COLUMN {column} TEXT")
            for column, definition in (
                ("contact_email", "TEXT"), ("contact_level", "TEXT"), ("contact_url", "TEXT"),
                ("contact_status", "TEXT NOT NULL DEFAULT 'not_requested'"), ("contact_checked_at", "TEXT"),
            ):
                if column not in columns:
                    connection.execute(f"ALTER TABLE offers ADD COLUMN {column} {definition}")

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    def create_run(self, spec: RunSpec) -> str:
        run_id = uuid4().hex
        now = self._now()
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO runs(id, name, state, spec_json, created_at, updated_at) VALUES(?, ?, 'ready', ?, ?, ?)",
                (run_id, spec.name, json.dumps(spec.to_dict(), ensure_ascii=False), now, now),
            )
        return run_id

    def set_run_state(self, run_id: str, state: str) -> None:
        with self._connection() as connection:
            result = connection.execute("UPDATE runs SET state = ?, updated_at = ? WHERE id = ?", (state, self._now(), run_id))
            if result.rowcount != 1:
                raise KeyError(f"Unknown run: {run_id}")

    def task_complete(self, run_id: str, task_key: str) -> bool:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT status FROM tasks WHERE run_id = ? AND task_key = ?", (run_id, task_key)
            ).fetchone()
            return bool(row and row["status"] == TaskStatus.COMPLETE)

    def commit_discovery(self, run_id: str, task_key: str, observations: list[JobObservation],
                         max_selected: int | None = None) -> tuple[int, int]:
        """Persist a search page and its completion marker in one transaction.

        Returns ``(new_unique_offers, duplicates)``. A repeated completed page is
        a no-op, which makes resume safe after a process interruption.
        """
        now = self._now()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                task = connection.execute("SELECT status FROM tasks WHERE run_id = ? AND task_key = ?", (run_id, task_key)).fetchone()
                if task and task["status"] == TaskStatus.COMPLETE:
                    connection.execute("COMMIT")
                    return 0, 0
                inserted = 0
                duplicates = 0
                selected_count = connection.execute(
                    "SELECT COUNT(*) FROM offers WHERE run_id = ? AND selection_status = 'selected'", (run_id,)
                ).fetchone()[0]
                for observation in observations:
                    selection_status = "selected" if max_selected is None or selected_count < max_selected else "overflow"
                    result = connection.execute(
                        """INSERT INTO offers(
                            run_id, source, source_key, canonical_url, title, company, location, posted_text,
                            skills_json, experience, contract, description, description_status, quality, selection_status, collected_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(run_id, source, source_key) DO NOTHING""",
                        (run_id, observation.source, observation.source_key, observation.canonical_url, observation.title,
                         observation.company, observation.location, observation.posted_text,
                         json.dumps(observation.skills, ensure_ascii=False), observation.experience, observation.contract,
                         observation.description, observation.description_status, observation.quality, selection_status, now),
                    )
                    if result.rowcount:
                        inserted += 1
                        if selection_status == "selected":
                            selected_count += 1
                    else:
                        duplicates += 1
                connection.execute(
                    """INSERT INTO tasks(run_id, task_key, kind, status, payload_json, completed_at)
                       VALUES (?, ?, ?, ?, '{}', ?)
                       ON CONFLICT(run_id, task_key) DO UPDATE SET status = excluded.status, completed_at = excluded.completed_at""",
                    (run_id, task_key, TaskKind.SEARCH, TaskStatus.COMPLETE, now),
                )
                connection.execute("UPDATE runs SET updated_at = ? WHERE id = ?", (now, run_id))
                connection.execute("COMMIT")
                return inserted, duplicates
            except BaseException:
                connection.execute("ROLLBACK")
                raise

    def commit_detail(self, run_id: str, offer_key: str, description: str, status: str, quality: str,
                      evidence: tuple[FieldEvidence, ...], qualification_status: str = "matching",
                      source: str | None = None) -> None:
        """Persist detail text, its evidence, and its task completion atomically."""
        now = self._now()
        fields = requirement_summary(evidence)
        task_key = f"detail:{source}:{offer_key}" if source else f"detail:{offer_key}"
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                query = "SELECT id FROM offers WHERE run_id = ? AND source_key = ?"
                parameters = (run_id, offer_key)
                if source:
                    query += " AND source = ?"
                    parameters += (source,)
                matches = connection.execute(query, parameters).fetchall()
                if not matches:
                    raise KeyError(f"Unknown offer key: {offer_key}")
                if len(matches) != 1:
                    raise ValueError("A source is required for an ambiguous offer key")
                offer = matches[0]
                connection.execute(
                    """UPDATE offers SET raw_description = COALESCE(raw_description, description, ?),
                       description = ?, description_status = ?, quality = ?, qualification_status = ?,
                       skills_json = ?, experience = ?, contract = ?, education = ? WHERE id = ?""",
                    (description, description_text(description), status, quality, qualification_status,
                     json.dumps(fields["skills"], ensure_ascii=False), fields["experience"] or None,
                     fields["contract"] or None, fields["education"] or None, offer["id"]),
                )
                connection.execute("DELETE FROM evidence WHERE offer_id = ?", (offer["id"],))
                connection.executemany(
                    "INSERT INTO evidence(offer_id, field, value, excerpt, method, score, rule_version) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [(offer["id"], item.field, item.value, item.excerpt, item.method, item.score, item.rule_version) for item in evidence],
                )
                connection.execute(
                    """INSERT INTO tasks(run_id, task_key, kind, status, payload_json, completed_at)
                       VALUES (?, ?, ?, ?, '{}', ?)
                       ON CONFLICT(run_id, task_key) DO UPDATE SET status = excluded.status, completed_at = excluded.completed_at""",
                    (run_id, task_key, TaskKind.DETAIL, TaskStatus.COMPLETE, now),
                )
                connection.execute("UPDATE runs SET updated_at = ? WHERE id = ?", (now, run_id))
                connection.execute("COMMIT")
            except BaseException:
                connection.execute("ROLLBACK")
                raise

    def commit_contact(self, run_id: str, offer_key: str, *, status: str, email: str | None = None,
                       level: str | None = None, url: str | None = None, source: str | None = None) -> None:
        """Persist the outcome of an optional public-contact check."""
        if status not in {"found", "not_found", "unavailable", "not_requested"}:
            raise ValueError(f"Unknown contact status: {status}")
        with self._connection() as connection:
            query = "UPDATE offers SET contact_email = ?, contact_level = ?, contact_url = ?, contact_status = ?, contact_checked_at = ? WHERE run_id = ? AND source_key = ?"
            parameters: tuple[object, ...] = (email, level, url, status, self._now(), run_id, offer_key)
            if source:
                query += " AND source = ?"
                parameters += (source,)
            result = connection.execute(query, parameters)
            if result.rowcount != 1:
                raise KeyError(f"Unknown or ambiguous offer key: {offer_key}")

    def counters(self, run_id: str, target_mode: str = "descriptions") -> RunCounters:
        with self._connection() as connection:
            row = connection.execute(
                """SELECT COUNT(*) AS found_count,
                          SUM(CASE WHEN selection_status = 'selected' THEN 1 ELSE 0 END) AS selected_count,
                          SUM(CASE WHEN selection_status = 'selected' AND description_status = 'available' THEN 1 ELSE 0 END) AS details,
                          SUM(CASE WHEN selection_status = 'selected' AND description_status = 'available' AND qualification_status = 'matching' THEN 1 ELSE 0 END) AS matching_details,
                          SUM(CASE WHEN selection_status = 'selected' AND description_status != 'available' THEN 1 ELSE 0 END) AS incomplete
                   FROM offers WHERE run_id = ?""", (run_id,)
            ).fetchone()
            found = int(row["found_count"])
            unique = int(row["selected_count"] or 0)
            descriptions = int(row["details"] or 0)
            incomplete = int(row["incomplete"] or 0)
            target_count = int(row["matching_details"] or 0) if target_mode == "descriptions" else unique
            tasks = connection.execute("SELECT COUNT(*) AS count FROM tasks WHERE run_id = ? AND kind = ?", (run_id, TaskKind.SEARCH)).fetchone()
            return RunCounters(found=found, unique=unique, descriptions=descriptions, matching_target=target_count,
                               duplicates=0, incomplete=incomplete)

    def qualification_counts(self, run_id: str) -> dict[str, int]:
        """Return qualification outcomes for descriptions that were retrieved.

        This powers honest completion messaging: a retrieved description and a
        target-qualifying offer are different facts when filters are active.
        """
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT qualification_status, COUNT(*) AS count FROM offers
                   WHERE run_id = ? AND selection_status = 'selected'
                     AND description_status = 'available'
                   GROUP BY qualification_status""", (run_id,)
            ).fetchall()
        return {str(row["qualification_status"]): int(row["count"]) for row in rows}

    def run(self, run_id: str) -> sqlite3.Row:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            if row is None:
                raise KeyError(f"Unknown run: {run_id}")
            return row

    def list_runs(self) -> list[sqlite3.Row]:
        with self._connection() as connection:
            return connection.execute(
                "SELECT id, name, state, created_at, updated_at FROM runs ORDER BY updated_at DESC"
            ).fetchall()

    def offers(self, run_id: str, include_overflow: bool = False, offer_ids: tuple[int, ...] | None = None) -> list[sqlite3.Row]:
        with self._connection() as connection:
            query = "SELECT * FROM offers WHERE run_id = ?"
            parameters: list[object] = [run_id]
            if not include_overflow:
                query += " AND selection_status = 'selected'"
            if offer_ids is not None:
                if not offer_ids:
                    return []
                query += " AND id IN (" + ", ".join("?" for _ in offer_ids) + ")"
                parameters.extend(offer_ids)
            return connection.execute(query + " ORDER BY collected_at, id", parameters).fetchall()

    def evidence_for_offer(self, offer_id: int) -> list[sqlite3.Row]:
        with self._connection() as connection:
            return connection.execute("SELECT * FROM evidence WHERE offer_id = ? ORDER BY id", (offer_id,)).fetchall()

    def incomplete_detail_keys(self, run_id: str) -> list[str]:
        with self._connection() as connection:
            return [row["source_key"] for row in connection.execute(
                """SELECT source_key FROM offers
                   WHERE run_id = ? AND selection_status = 'selected' AND description_status != 'available' ORDER BY id""", (run_id,)
            )]

    def pending_detail_offers(self, run_id: str) -> list[sqlite3.Row]:
        with self._connection() as connection:
            return connection.execute(
                """SELECT * FROM offers WHERE run_id = ? AND selection_status = 'selected'
                   AND description_status = 'pending' ORDER BY id""", (run_id,)
            ).fetchall()
