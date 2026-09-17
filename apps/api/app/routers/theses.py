"""Acquisition thesis routes."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from apps.api.app.core.auth import AuthUser, get_current_user
from apps.api.app.core.store import get_store
from apps.api.app.core.tenancy import require_membership
from apps.api.app.schemas.models import ThesisCreate, ThesisOut, ThesisUpdate

router = APIRouter(tags=["theses"])


@router.get("/theses")
def list_theses(
    workspace_id: str,
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> List[Dict[str, Any]]:
    """List theses for a workspace."""
    require_membership(store, workspace_id, user)
    return store.list_theses(workspace_id)


@router.post("/theses", status_code=201)
async def create_thesis(
    body: ThesisCreate,
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Create a thesis, optionally parsing natural language via LLM."""
    require_membership(store, body.workspace_id, user)
    criteria = body.criteria or {}
    strategy = body.strategy or {}
    name = body.name

    if body.natural_language:
        from workers.llm.client import parse_thesis_nl

        loop = asyncio.get_event_loop()
        parsed = await loop.run_in_executor(None, parse_thesis_nl, body.natural_language)
        name = body.name or parsed.get("name") or name
        criteria = {**(parsed.get("criteria") or {}), **(body.criteria or {})}
        strategy = {**(parsed.get("strategy") or {}), **(body.strategy or {})}

    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    return store.create_thesis(body.workspace_id, name, criteria, strategy)


@router.get("/theses/{thesis_id}")
def get_thesis(
    thesis_id: str,
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Fetch a single thesis."""
    thesis = store.get_thesis(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    require_membership(store, thesis["workspace_id"], user)
    return thesis


@router.patch("/theses/{thesis_id}")
def patch_thesis(
    thesis_id: str,
    body: ThesisUpdate,
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Update thesis fields."""
    thesis = store.get_thesis(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    require_membership(store, thesis["workspace_id"], user)
    updated = store.update_thesis(
        thesis_id,
        name=body.name,
        criteria=body.criteria,
        strategy=body.strategy,
    )
    return updated
