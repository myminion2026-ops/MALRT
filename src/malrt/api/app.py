"""FastAPI application — serves API + dashboard."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from malrt.core.database import init_db
from malrt.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="M.A.L.R.T",
    description="Malware & Abuse Liaison Reporting Tool",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api")

# Serve dashboard static files
import os

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def dashboard():
    return FileResponse(os.path.join(_STATIC_DIR, "index.html"))
