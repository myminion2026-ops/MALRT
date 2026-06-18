"""CLI entry point — malrt serve / malrt submit."""

from __future__ import annotations

import asyncio
import json

import typer

app = typer.Typer(help="M.A.L.R.T — Malware & Abuse Liaison Reporting Tool")


@app.command()
def serve(
    host: str = typer.Option(None, help="Bind host"),
    port: int = typer.Option(None, help="Bind port"),
) -> None:
    """Start the MALRT web server and dashboard."""
    import uvicorn

    from malrt.config import settings

    uvicorn.run(
        "malrt.api.app:app",
        host=host or settings.HOST,
        port=port or settings.PORT,
        reload=False,
    )


@app.command()
def submit(indicator: str = typer.Argument(..., help="URL, domain, IP, or hash to submit")) -> None:
    """Submit a single indicator and print the result."""
    from malrt.core.database import init_db
    from malrt.core.engine import submit_indicator

    async def _run() -> None:
        await init_db()
        result = await submit_indicator(indicator)
        print(json.dumps(result.model_dump(), indent=2))

    asyncio.run(_run())


if __name__ == "__main__":
    app()
