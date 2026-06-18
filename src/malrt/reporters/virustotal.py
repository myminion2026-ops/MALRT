"""VirusTotal reporter — submit URLs, domains, IPs, and hashes."""

from __future__ import annotations

import hashlib
from urllib.parse import urlencode

import httpx

from malrt.config import settings
from malrt.core.models import Indicator, IndicatorType, SubmissionResult, SubmissionStatus
from malrt.reporters.base import BaseReporter

_VT_BASE = "https://www.virustotal.com/api/v3"


class VirusTotalReporter(BaseReporter):
    name = "virustotal"
    enabled = True

    def __init__(self) -> None:
        self.enabled = bool(settings.VT_API_KEY)

    async def submit(
        self, indicator: Indicator, submission_id: str
    ) -> SubmissionResult:
        if not settings.VT_API_KEY:
            return self.make_result(
                status=SubmissionStatus.failed,
                error="VT_API_KEY not configured",
            )

        headers = {"x-apikey": settings.VT_API_KEY}
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                if indicator.type == IndicatorType.url:
                    return await self._submit_url(client, headers, indicator)
                elif indicator.type == IndicatorType.hash:
                    return await self._lookup_hash(client, headers, indicator)
                elif indicator.type in (IndicatorType.domain, IndicatorType.ip):
                    return await self._lookup_entity(client, headers, indicator)
                else:
                    return self.make_result(
                        status=SubmissionStatus.failed,
                        error=f"Unsupported indicator type: {indicator.type}",
                    )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    return self.make_result(
                        status=SubmissionStatus.rate_limited,
                        error="VirusTotal rate limit hit (429)",
                    )
                return self.make_result(
                    status=SubmissionStatus.failed,
                    error=f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
                )
            except Exception as exc:
                return self.make_result(
                    status=SubmissionStatus.failed,
                    error=str(exc),
                )

    async def _submit_url(
        self, client: httpx.AsyncClient, headers: dict, indicator: Indicator
    ) -> SubmissionResult:
        # VT requires URL to be base64-encoded (no padding) for the GET endpoint,
        # but POST /urls accepts form-encoded url parameter.
        post_headers = {**headers, "Content-Type": "application/x-www-form-urlencoded"}
        resp = await client.post(
            f"{_VT_BASE}/urls",
            headers=post_headers,
            content=urlencode({"url": indicator.value}),
        )
        resp.raise_for_status()
        data = resp.json()
        analysis_id = data.get("data", {}).get("id", "")
        return self.make_result(
            status=SubmissionStatus.submitted,
            response_data={"analysis_id": analysis_id, "provider": "virustotal"},
        )

    async def _lookup_hash(
        self, client: httpx.AsyncClient, headers: dict, indicator: Indicator
    ) -> SubmissionResult:
        resp = await client.get(
            f"{_VT_BASE}/files/{indicator.value}", headers=headers
        )
        resp.raise_for_status()
        data = resp.json()
        attrs = data.get("data", {}).get("attributes", {})
        return self.make_result(
            status=SubmissionStatus.completed,
            response_data={
                "type": attrs.get("type_description"),
                "detection_rate": f"{attrs.get('last_analysis_stats', {}).get('malicious', 0)}/{sum(attrs.get('last_analysis_stats', {}).values())}",
                "reputation": attrs.get("reputation"),
            },
        )

    async def _lookup_entity(
        self, client: httpx.AsyncClient, headers: dict, indicator: Indicator
    ) -> SubmissionResult:
        endpoint = "domains" if indicator.type == IndicatorType.domain else "ip_addresses"
        resp = await client.get(
            f"{_VT_BASE}/{endpoint}/{indicator.value}", headers=headers
        )
        resp.raise_for_status()
        data = resp.json()
        stats = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
        return self.make_result(
            status=SubmissionStatus.completed,
            response_data={
                "malicious": stats.get("malicious", 0),
                "suspicious": stats.get("suspicious", 0),
                "harmless": stats.get("harmless", 0),
                "undetected": stats.get("undetected", 0),
            },
        )
