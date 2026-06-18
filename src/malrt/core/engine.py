"""Core engine — normalize indicators and dispatch to reporters."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from malrt.core.database import (
    add_result,
    create_submission,
    get_submission,
    update_submission_status,
)
from malrt.core.models import (
    Indicator,
    IndicatorType,
    Submission,
    SubmissionStatus,
)
from malrt.reporters.base import BaseReporter
from malrt.reporters.virustotal import VirusTotalReporter

# Lazy-loaded registry
_REPORTERS: dict[str, type[BaseReporter]] = {
    "virustotal": VirusTotalReporter,
}

_IPV4_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
_HASH_RE = re.compile(r"^[a-fA-F0-9]{32}$|^[a-fA-F0-9]{40}$|^[a-fA-F0-9]{64}$")


def normalize_indicator(raw: str) -> Indicator:
    """Auto-detect indicator type and normalize the value."""
    raw = raw.strip()
    value = raw

    # URL
    if raw.startswith(("http://", "https://")):
        value = raw.rstrip("/")
        return Indicator(type=IndicatorType.url, value=value, raw_value=raw)

    # IPv4
    if _IPV4_RE.match(raw):
        return Indicator(type=IndicatorType.ip, value=raw, raw_value=raw)

    # Hash (MD5=32, SHA1=40, SHA256=64)
    if _HASH_RE.match(raw):
        return Indicator(type=IndicatorType.hash, value=raw.upper(), raw_value=raw)

    # Default: domain
    return Indicator(type=IndicatorType.domain, value=raw.lower(), raw_value=raw)


async def submit_indicator(
    raw: str,
    reporter_names: list[str] | None = None,
) -> Submission:
    """Normalize, persist, and dispatch indicator to reporters."""
    indicator = normalize_indicator(raw)

    sub = Submission(
        indicator=indicator,
        status=SubmissionStatus.pending,
    )
    await create_submission(sub)

    # Resolve reporters
    if reporter_names is None:
        reporter_names = list(_REPORTERS.keys())

    reporters: list[BaseReporter] = []
    for name in reporter_names:
        cls = _REPORTERS.get(name)
        if cls:
            reporters.append(cls())

    if not reporters:
        await update_submission_status(sub.id, SubmissionStatus.completed)
        sub.status = SubmissionStatus.completed
        return sub

    await update_submission_status(sub.id, SubmissionStatus.submitted)
    sub.status = SubmissionStatus.submitted

    for reporter in reporters:
        try:
            result = await reporter.submit(indicator, sub.id)
        except Exception as exc:
            result = reporter.make_result(
                status=SubmissionStatus.failed,
                error=str(exc),
            )
        await add_result(result, sub.id)
        sub.results.append(result)

    # Determine final status
    statuses = {r.status for r in sub.results}
    if statuses == {SubmissionStatus.failed}:
        final = SubmissionStatus.failed
    elif SubmissionStatus.rate_limited in statuses:
        final = SubmissionStatus.rate_limited
    else:
        final = SubmissionStatus.completed

    await update_submission_status(sub.id, final)
    sub.status = final
    return sub


async def get_submission_detail(sub_id: str) -> Submission | None:
    return await get_submission(sub_id)
