"""Domain models for indicators, submissions, and results."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class IndicatorType(str, enum.Enum):
    url = "url"
    domain = "domain"
    ip = "ip"
    hash = "hash"
    file = "file"


class SubmissionStatus(str, enum.Enum):
    pending = "pending"
    submitted = "submitted"
    completed = "completed"
    failed = "failed"
    rate_limited = "rate_limited"


class Indicator(BaseModel):
    type: IndicatorType
    value: str  # normalized
    raw_value: str  # original input


class SubmissionResult(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    provider: str
    status: SubmissionStatus = SubmissionStatus.pending
    submitted_at: str | None = None
    response_data: dict | None = None
    error: str | None = None


class Submission(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    indicator: Indicator
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: SubmissionStatus = SubmissionStatus.pending
    results: list[SubmissionResult] = Field(default_factory=list)
