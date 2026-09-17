"""Workspace and command-center routes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.app.core.auth import AuthUser, get_current_user
from apps.api.app.core.store import get_store
from apps.api.app.core.tenancy import require_membership
from apps.api.app.schemas.models import CadenceUpdate

router = APIRouter(tags=["workspaces"])


@router.get("/workspaces")
def list_workspaces(
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> List[Dict[str, Any]]:
    """List workspaces for the authenticated user."""
    return store.list_workspaces(user.user_id)


@router.get("/workspaces/{workspace_id}/command-center")
def command_center(
    workspace_id: str,
    thesis_id: Optional[str] = Query(None),
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Acquisition command center aggregates."""
    require_membership(store, workspace_id, user)
    return store.command_center(workspace_id, thesis_id)


@router.get("/workspaces/{workspace_id}/cadence")
def get_cadence(
    workspace_id: str,
    thesis_id: Optional[str] = Query(None),
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Resolved weekly cadence for the workspace (thesis may override)."""
    require_membership(store, workspace_id, user)
    if not store.get_workspace(workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found")
    return store.get_cadence(workspace_id, thesis_id)


@router.patch("/workspaces/{workspace_id}/cadence")
def patch_cadence(
    workspace_id: str,
    body: CadenceUpdate,
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Update workspace cadence settings."""
    require_membership(store, workspace_id, user)
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    if not patch:
        return store.get_cadence(workspace_id)
    ws = store.update_workspace_settings(workspace_id, {"cadence": patch})
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return store.get_cadence(workspace_id)
