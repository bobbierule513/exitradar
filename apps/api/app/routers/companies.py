"""Company intelligence routes."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.app.core.auth import AuthUser, get_current_user
from apps.api.app.core.store import get_store
from apps.api.app.core.tenancy import require_company_access, require_membership

router = APIRouter(tags=["companies"])


@router.get("/companies/{company_id}")
def get_company(
    company_id: str,
    workspace_id: Optional[str] = Query(None),
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Company detail with contacts."""
    company = require_company_access(store, company_id, user, workspace_id)
    return {
        **company,
        "contacts": store.list_contacts(company_id),
        "seller_readiness": store.latest_seller_score(company_id),
    }


@router.get("/companies/{company_id}/evidence")
def company_evidence(
    company_id: str,
    workspace_id: Optional[str] = Query(None),
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> List[Dict[str, Any]]:
    """Evidence items for a company."""
    require_company_access(store, company_id, user, workspace_id)
    return store.list_evidence(company_id)


@router.get("/companies/{company_id}/signals")
def company_signals(
    company_id: str,
    workspace_id: Optional[str] = Query(None),
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> List[Dict[str, Any]]:
    """Current signals."""
    require_company_access(store, company_id, user, workspace_id)
    return store.list_signals(company_id)


@router.get("/companies/{company_id}/timeline")
def company_timeline(
    company_id: str,
    workspace_id: Optional[str] = Query(None),
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Signal events + activities timeline."""
    require_company_access(store, company_id, user, workspace_id)
    return {
        "signal_events": store.list_signal_events(company_id),
        "activities": store.list_activities(company_id),
    }


@router.get("/companies/{company_id}/relationships")
def company_relationships(
    company_id: str,
    workspace_id: Optional[str] = Query(None),
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> List[Dict[str, Any]]:
    """Company relationship edges."""
    require_company_access(store, company_id, user, workspace_id)
    return store.list_relationships(company_id)


@router.post("/companies/{company_id}/refresh")
async def refresh_company(
    company_id: str,
    thesis_id: str = Query(...),
    workspace_id: Optional[str] = Query(None),
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Re-score a company against a thesis."""
    company = require_company_access(store, company_id, user, workspace_id)
    thesis = store.get_thesis(thesis_id)
    if not thesis or thesis.get("workspace_id") != company.get("workspace_id"):
        raise HTTPException(status_code=404, detail="Thesis not found")
    require_membership(store, thesis["workspace_id"], user)
    from workers.discovery.run_search_job import score_company

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, score_company, company_id, thesis_id)
    return result


@router.post("/companies/{company_id}/score")
async def score_company_route(
    company_id: str,
    thesis_id: str = Query(...),
    workspace_id: Optional[str] = Query(None),
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Alias for refresh/score."""
    return await refresh_company(company_id, thesis_id, workspace_id, user, store)


@router.get("/companies/{company_id}/opportunities/{thesis_id}")
def company_opportunity(
    company_id: str,
    thesis_id: str,
    workspace_id: Optional[str] = Query(None),
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Latest opportunity score for company × thesis."""
    company = require_company_access(store, company_id, user, workspace_id)
    thesis = store.get_thesis(thesis_id)
    if not thesis or thesis.get("workspace_id") != company.get("workspace_id"):
        raise HTTPException(status_code=404, detail="Opportunity not found")
    opp = store.get_opportunity(company_id, thesis_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    from workers.intelligence.book_of_work import iso_week_label
    from workers.intelligence.book_service import ensure_book_of_work

    try:
        ensure_book_of_work(store, thesis_id, force=False, with_brief=False)
    except Exception:  # noqa: BLE001
        pass
    book_slot = store.company_book_slot(company_id, thesis_id, iso_week_label())
    return {
        **opp,
        "company": company,
        "recommendation": store.get_recommendation(company_id, thesis_id),
        "evidence": store.list_evidence(company_id),
        "signals": store.list_signals(company_id),
        "pipeline": store.get_pipeline(company_id, thesis_id),
        "book_slot": book_slot,
        "relationships": store.list_relationships(company_id),
    }


@router.get("/companies/{company_id}/recommendation")
def company_recommendation(
    company_id: str,
    thesis_id: Optional[str] = Query(None),
    workspace_id: Optional[str] = Query(None),
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Next-best-action recommendation."""
    require_company_access(store, company_id, user, workspace_id)
    rec = store.get_recommendation(company_id, thesis_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return rec
