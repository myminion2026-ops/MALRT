"""REST API routes for submissions and providers."""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from malrt.core.database import get_submission, list_submissions
from malrt.core.engine import submit_indicator, get_submission_detail

router = APIRouter()


class SubmitRequest(BaseModel):
    indicator: str
    reporters: list[str] | None = None


@router.post("/submit")
async def api_submit(req: SubmitRequest):
    """Submit an indicator (URL, domain, IP, hash) for reporting."""
    result = await submit_indicator(req.indicator, req.reporters)
    return result.model_dump()


@router.get("/submissions")
async def api_list_submissions(limit: int = 50):
    """List recent submissions with status."""
    subs = await list_submissions(limit)
    return [s.model_dump() for s in subs]


@router.get("/submissions/{submission_id}")
async def api_get_submission(submission_id: str):
    """Get detailed submission info including all provider results."""
    sub = await get_submission_detail(submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sub.model_dump()


@router.get("/providers")
async def api_list_providers():
    """List available reporters and their status."""
    from malrt.reporters.virustotal import VirusTotalReporter
    from malrt.config import settings

    providers = []
    vt = VirusTotalReporter()
    providers.append({
        "name": "virustotal",
        "enabled": vt.enabled,
        "configured": bool(settings.VT_API_KEY),
    })
    return providers


@router.get("/stream")
async def api_stream():
    """SSE endpoint for real-time submission updates."""

    async def event_generator() -> AsyncGenerator[str, None]:
        last_count = 0
        while True:
            subs = await list_submissions(limit=10)
            if len(subs) != last_count or (subs and subs[0].status.value != "pending"):
                last_count = len(subs)
                data = json.dumps([s.model_dump() for s in subs])
                yield f"data: {data}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
