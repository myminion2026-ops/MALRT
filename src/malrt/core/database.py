"""Async SQLite persistence for submissions and results."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import aiosqlite

from malrt.core.models import (
    Indicator,
    IndicatorType,
    Submission,
    SubmissionResult,
    SubmissionStatus,
)

def _db_path() -> str:
    return os.environ.get("MALRT_DB_PATH", "malrt.db")

_DDL = """
CREATE TABLE IF NOT EXISTS submissions (
    id TEXT PRIMARY KEY,
    indicator_type TEXT NOT NULL,
    indicator_value TEXT NOT NULL,
    raw_value TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS submission_results (
    id TEXT PRIMARY KEY,
    submission_id TEXT NOT NULL REFERENCES submissions(id),
    provider TEXT NOT NULL,
    status TEXT NOT NULL,
    submitted_at TEXT,
    response_data TEXT,
    error TEXT
);
"""


async def init_db() -> None:
    async with aiosqlite.connect(_db_path()) as db:
        await db.executescript(_DDL)
        await db.commit()


async def create_submission(sub: Submission) -> Submission:
    async with aiosqlite.connect(_db_path()) as db:
        await db.execute(
            "INSERT INTO submissions VALUES (?,?,?,?,?,?,?)",
            (
                sub.id,
                sub.indicator.type.value,
                sub.indicator.value,
                sub.indicator.raw_value,
                sub.status.value,
                sub.created_at,
                sub.updated_at,
            ),
        )
        await db.commit()
    return sub


async def get_submission(sub_id: str) -> Submission | None:
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM submissions WHERE id = ?", (sub_id,)
        )
        row = await cur.fetchone()
        if not row:
            return None
        results = await _get_results(db, sub_id)
        return _row_to_submission(row, results)


async def list_submissions(limit: int = 50) -> list[Submission]:
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM submissions ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cur.fetchall()
        subs = []
        for row in rows:
            results = await _get_results(db, row["id"])
            subs.append(_row_to_submission(row, results))
        return subs


async def update_submission_status(
    sub_id: str, status: SubmissionStatus
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(_db_path()) as db:
        await db.execute(
            "UPDATE submissions SET status=?, updated_at=? WHERE id=?",
            (status.value, now, sub_id),
        )
        await db.commit()


async def add_result(result: SubmissionResult, submission_id: str) -> None:
    async with aiosqlite.connect(_db_path()) as db:
        await db.execute(
            "INSERT INTO submission_results VALUES (?,?,?,?,?,?,?)",
            (
                result.id,
                submission_id,
                result.provider,
                result.status.value,
                result.submitted_at,
                json.dumps(result.response_data) if result.response_data else None,
                result.error,
            ),
        )
        await db.commit()


async def get_results(submission_id: str) -> list[SubmissionResult]:
    async with aiosqlite.connect(_db_path()) as db:
        return await _get_results(db, submission_id)


# --- helpers ---


async def _get_results(db: aiosqlite.Connection, sub_id: str) -> list[SubmissionResult]:
    db.row_factory = aiosqlite.Row
    cur = await db.execute(
        "SELECT * FROM submission_results WHERE submission_id = ?", (sub_id,)
    )
    rows = await cur.fetchall()
    return [
        SubmissionResult(
            id=r["id"],
            provider=r["provider"],
            status=SubmissionStatus(r["status"]),
            submitted_at=r["submitted_at"],
            response_data=json.loads(r["response_data"]) if r["response_data"] else None,
            error=r["error"],
        )
        for r in rows
    ]


def _row_to_submission(row: aiosqlite.Row, results: list[SubmissionResult]) -> Submission:
    return Submission(
        id=row["id"],
        indicator=Indicator(
            type=IndicatorType(row["indicator_type"]),
            value=row["indicator_value"],
            raw_value=row["raw_value"],
        ),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        status=SubmissionStatus(row["status"]),
        results=results,
    )
