"""Abstract base for all reporters (vendor integrations)."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from malrt.core.models import (
    Indicator,
    SubmissionResult,
    SubmissionStatus,
)


class BaseReporter(ABC):
    """Base class every reporter must extend."""

    name: str = "base"
    enabled: bool = True

    @abstractmethod
    async def submit(
        self, indicator: Indicator, submission_id: str
    ) -> SubmissionResult:
        """Submit indicator to the vendor. Return a SubmissionResult."""
        ...

    async def health_check(self) -> bool:
        """Return True if the reporter's API is reachable."""
        return True

    def make_result(
        self,
        status: SubmissionStatus = SubmissionStatus.pending,
        response_data: dict | None = None,
        error: str | None = None,
    ) -> SubmissionResult:
        """Helper to build a result with standard fields."""
        return SubmissionResult(
            id=uuid.uuid4().hex[:12],
            provider=self.name,
            status=status,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            response_data=response_data,
            error=error,
        )
