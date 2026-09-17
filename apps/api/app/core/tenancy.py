"""Workspace tenancy helpers for API routes.

Never trust a client-supplied workspace_id without membership. Company routes
must resolve the company's workspace and check membership there.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from apps.api.app.core.auth import AuthUser


def require_membership(store: Any, workspace_id: str, user: AuthUser) -> None:
    """Ensure the user belongs to the workspace.

    DemoStore may auto-join; Postgres/prod must already have a membership row.
    """
    if not workspace_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workspace_id is required")
    member = store.get_workspace_member(workspace_id, user.user_id)
    if member is not None:
        return
    if getattr(store, "demo_mode", False):
        store.ensure_membership(workspace_id, user.user_id, "member")
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a workspace member")


def require_company_access(
    store: Any,
    company_id: str,
    user: AuthUser,
    workspace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Load a company and verify the caller is a member of its workspace.

    If workspace_id is provided, it must match the company's workspace.
    Unknown or cross-workspace companies return 404 to avoid existence leaks.
    """
    company = store.get_company(company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    company_ws = company.get("workspace_id")
    if not company_ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    if workspace_id and workspace_id != company_ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    require_membership(store, company_ws, user)
    return company
