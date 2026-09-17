"""ExitRadar FastAPI application."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure repo root on path when running via uvicorn
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.app.core.config import get_settings
from apps.api.app.routers import companies, decisions, discovery, theses, workspaces

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("exitradar.api")

settings = get_settings()

app = FastAPI(
    title="ExitRadar API",
    description="Acquisition Opportunity Engine",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Return standard error envelope on unexpected failures."""
    logger.exception("Unhandled error on %s: %s", request.url.path, exc)
    origin = request.headers.get("origin")
    headers = {}
    if origin and origin in settings.cors_origin_list:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Vary"] = "Origin"
    return JSONResponse(status_code=500, content={"error": str(exc)}, headers=headers)


@app.get("/health")
def health() -> dict:
    """Liveness probe."""
    return {
        "status": "ok",
        "service": "exitradar-api",
        "environment": settings.environment,
        "demo_mode": settings.demo_mode,
        "store": "memory" if settings.demo_mode else "postgres",
    }


API_PREFIX = "/api/v1"
app.include_router(workspaces.router, prefix=API_PREFIX)
app.include_router(theses.router, prefix=API_PREFIX)
app.include_router(discovery.router, prefix=API_PREFIX)
app.include_router(companies.router, prefix=API_PREFIX)
app.include_router(decisions.router, prefix=API_PREFIX)
