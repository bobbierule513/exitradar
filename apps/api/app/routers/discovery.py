"""Discovery / search job / company list routes."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.app.core.auth import AuthUser, get_current_user
from apps.api.app.core.store import get_store
from apps.api.app.core.tenancy import require_membership
from apps.api.app.schemas.models import SearchJobCreate

router = APIRouter(tags=["discovery"])


@router.post("/search-jobs", status_code=201)
async def create_search_job(
    body: SearchJobCreate,
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Enqueue a discovery job for a thesis."""
    thesis = store.get_thesis(body.thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    require_membership(store, thesis["workspace_id"], user)

    query = body.query_override or {
        "location": body.location,
        "max_results": body.max_results,
        "thesis_id": body.thesis_id,
    }
    job = store.create_search_job(body.thesis_id, query)

    from workers.discovery.run_search_job import run_search_job
    from workers.queue import enqueue

    loop = asyncio.get_event_loop()

    def _run() -> Any:
        return enqueue("standard", run_search_job, job["id"])

    result = await loop.run_in_executor(None, _run)
    # If sync, job already completed
    refreshed = store.get_search_job(job["id"])
    return {**(refreshed or job), "enqueue": result}


@router.get("/search-jobs/{job_id}")
def get_search_job(
    job_id: str,
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Poll search job status."""
    job = store.get_search_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    thesis = store.get_thesis(job["thesis_id"])
    if not thesis:
        raise HTTPException(status_code=404, detail="Job not found")
    require_membership(store, thesis["workspace_id"], user)
    return job


@router.get("/companies")
def list_companies(
    workspace_id: str = Query(...),
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> List[Dict[str, Any]]:
    """List canonical companies for a workspace."""
    require_membership(store, workspace_id, user)
    return store.list_companies(workspace_id)
