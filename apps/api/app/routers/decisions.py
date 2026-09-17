"""Scoring list, outreach, pipeline, activities, exports, Book of Work."""

from __future__ import annotations

import asyncio
import csv
import io
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from apps.api.app.core.auth import AuthUser, get_current_user
from apps.api.app.core.store import get_store
from apps.api.app.core.tenancy import require_company_access, require_membership
from apps.api.app.schemas.models import (
    ActivityCreate,
    BookOfWorkGenerate,
    BookSlotComplete,
    BookSlotSkip,
    ExportCreate,
    OutreachCreate,
    PipelineUpdate,
)

router = APIRouter(tags=["decisions"])


@router.get("/theses/{thesis_id}/opportunities")
def list_opportunities(
    thesis_id: str,
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> List[Dict[str, Any]]:
    """Ranked opportunities for a thesis."""
    thesis = store.get_thesis(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    require_membership(store, thesis["workspace_id"], user)
    opps = store.list_opportunities(thesis_id)
    from workers.intelligence.book_of_work import iso_week_label
    from workers.intelligence.book_service import ensure_book_of_work

    try:
        ensure_book_of_work(store, thesis_id, force=False, with_brief=False)
    except Exception:  # noqa: BLE001
        pass
    plan = store.get_book_plan(thesis_id, iso_week_label())
    slot_by_company: Dict[str, Dict[str, Any]] = {}
    if plan:
        for s in plan.get("slots") or []:
            slot_by_company[s["company_id"]] = s
    for o in opps:
        cid = o.get("company_id")
        slot = slot_by_company.get(cid) if cid else None
        if slot:
            o["book_slot"] = slot.get("kind")
            o["window_closes_at"] = slot.get("window_closes_at")
            o["cluster_id"] = slot.get("cluster_id")
        else:
            o["book_slot"] = None
            o["window_closes_at"] = (o.get("recommendation") or {}).get("expires_at")
            o["cluster_id"] = None
    return opps


@router.get("/theses/{thesis_id}/book-of-work")
def get_book_of_work(
    thesis_id: str,
    week: Optional[str] = Query(None),
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Latest Book of Work for ISO week; generate if missing."""
    thesis = store.get_thesis(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    require_membership(store, thesis["workspace_id"], user)
    from workers.intelligence.book_service import ensure_book_of_work

    return ensure_book_of_work(store, thesis_id, force=False, with_brief=False, iso_week=week)


@router.post("/theses/{thesis_id}/book-of-work", status_code=201)
async def generate_book_of_work(
    thesis_id: str,
    body: BookOfWorkGenerate,
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Regenerate (or create) this week's Book of Work."""
    thesis = store.get_thesis(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    require_membership(store, thesis["workspace_id"], user)
    from workers.intelligence.book_service import ensure_book_of_work

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: ensure_book_of_work(
            store,
            thesis_id,
            force=body.force,
            with_brief=body.with_brief,
            iso_week=body.week,
        ),
    )


@router.post("/book-of-work/slots/{slot_id}/complete")
def complete_book_slot(
    slot_id: str,
    body: BookSlotComplete,
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Complete a Book of Work slot."""
    slot = store.get_book_slot(slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    plan = store.get_book_plan_by_id(slot["plan_id"])
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    require_membership(store, plan["workspace_id"], user)
    from workers.intelligence.book_service import complete_slot

    return complete_slot(store, slot_id, outcome=body.outcome, notes=body.notes)


@router.post("/book-of-work/slots/{slot_id}/skip")
def skip_book_slot(
    slot_id: str,
    body: BookSlotSkip,
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Skip an outreach slot; promote substitute when available."""
    slot = store.get_book_slot(slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    plan = store.get_book_plan_by_id(slot["plan_id"])
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    require_membership(store, plan["workspace_id"], user)
    from workers.intelligence.book_service import skip_slot

    return skip_slot(store, slot_id, notes=body.notes)


@router.post("/companies/{company_id}/outreach", status_code=201)
async def create_outreach(
    company_id: str,
    body: OutreachCreate,
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Generate evidence-grounded outreach draft."""
    require_company_access(store, company_id, user)
    company = store.get_company(company_id)
    evidence = store.list_evidence(company_id)
    rec = store.get_recommendation(company_id, body.thesis_id)

    from workers.llm.client import generate_outreach

    loop = asyncio.get_event_loop()
    draft = await loop.run_in_executor(None, generate_outreach, company, evidence, rec)
    return store.create_outreach(
        company_id,
        body.contact_id,
        channel=body.channel,
        subject=draft.get("subject"),
        body=draft.get("body"),
        evidence_refs=draft.get("evidence_refs") or [e["id"] for e in evidence],
        prompt_version="outreach-v1",
    )


@router.get("/companies/{company_id}/outreach")
def list_outreach(
    company_id: str,
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> List[Dict[str, Any]]:
    """List outreach drafts."""
    require_company_access(store, company_id, user)
    return store.list_outreach(company_id)


@router.post("/companies/{company_id}/pipeline")
def update_pipeline(
    company_id: str,
    body: PipelineUpdate,
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Upsert deal pipeline stage."""
    require_company_access(store, company_id, user)
    return store.upsert_pipeline(
        company_id,
        body.thesis_id,
        stage=body.stage,
        probability=body.probability,
        notes=body.notes,
    )


@router.post("/companies/{company_id}/activities", status_code=201)
def create_activity(
    company_id: str,
    body: ActivityCreate,
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Log an activity / outcome."""
    require_company_access(store, company_id, user)
    return store.add_activity(
        company_id=company_id,
        recommendation_id=body.recommendation_id,
        activity_type=body.activity_type,
        outcome=body.outcome,
        metadata=body.metadata,
    )


@router.post("/companies/{company_id}/deal-brief")
async def deal_brief(
    company_id: str,
    thesis_id: str,
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Generate a deal brief from scores + evidence."""
    company = require_company_access(store, company_id, user)
    opp = store.get_opportunity(company_id, thesis_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Company or opportunity not found")
    evidence = store.list_evidence(company_id)
    from workers.llm.client import generate_deal_brief

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, generate_deal_brief, company, opp, evidence)


@router.post("/exports", status_code=201)
def create_export(
    body: ExportCreate,
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
) -> Dict[str, Any]:
    """Export ranked opportunities for a thesis."""
    require_membership(store, body.workspace_id, user)
    opps = store.list_opportunities(body.thesis_id)
    from workers.intelligence.book_of_work import iso_week_label

    plan = store.get_book_plan(body.thesis_id, iso_week_label())
    slot_by_company: Dict[str, Dict[str, Any]] = {}
    if plan:
        for s in plan.get("slots") or []:
            slot_by_company[s["company_id"]] = s
    rows = []
    for o in opps:
        c = o.get("company") or {}
        rec = o.get("recommendation") or {}
        slot = slot_by_company.get(o.get("company_id") or "")
        rows.append(
            {
                "company": c.get("canonical_name"),
                "domain": c.get("domain"),
                "industry": c.get("industry"),
                "opportunity_score": o.get("opportunity_score"),
                "fit": o.get("fit"),
                "seller": o.get("seller"),
                "timing": o.get("timing"),
                "access": o.get("access"),
                "competition": o.get("competition"),
                "next_action": rec.get("action"),
                "reason": rec.get("reason"),
                "book_slot": (slot or {}).get("kind"),
                "window_closes_at": (slot or {}).get("window_closes_at") or rec.get("expires_at"),
                "cluster_id": (slot or {}).get("cluster_id"),
            }
        )
    meta = store.create_export(
        body.workspace_id, {"thesis_id": body.thesis_id, "format": body.format}, rows
    )
    return meta


@router.get("/exports/{export_id}")
def get_export(
    export_id: str,
    format: str = "json",
    user: AuthUser = Depends(get_current_user),
    store: Any = Depends(get_store),
):
    """Download export as JSON or CSV."""
    exp = store.get_export(export_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Export not found")
    require_membership(store, exp["workspace_id"], user)
    rows = exp.get("rows") or []
    if format == "csv":
        if not rows:
            return Response(content="", media_type="text/csv")
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{export_id}.csv"'},
        )
    return exp
