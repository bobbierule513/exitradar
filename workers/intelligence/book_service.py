"""Book of Work orchestration — generate, merge, complete, skip, optional brief."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from workers.intelligence.book_of_work import (
    build_week_plan,
    estimate_research_lift,
    iso_week_label,
    promote_on_skip,
    resolve_cadence,
)

logger = logging.getLogger(__name__)


def _enrich_slots_with_companies(store: Any, plan: Dict[str, Any]) -> Dict[str, Any]:
    """Attach company summaries to slots for API/UI."""
    slots = []
    for s in plan.get("slots") or []:
        company = store.get_company(s["company_id"])
        sibling = None
        if s.get("chosen_sibling_id"):
            sibling = store.get_company(s["chosen_sibling_id"])
        slots.append(
            {
                **s,
                "company": company,
                "chosen_sibling": sibling,
            }
        )
    out = {**plan, "slots": slots}
    return out


def ensure_book_of_work(
    store: Any,
    thesis_id: str,
    *,
    force: bool = False,
    with_brief: bool = False,
    iso_week: Optional[str] = None,
    merge_only: bool = False,
) -> Dict[str, Any]:
    """Return active week plan, generating or merging as needed."""
    thesis = store.get_thesis(thesis_id)
    if not thesis:
        raise ValueError("Thesis not found")
    workspace_id = thesis["workspace_id"]
    week = iso_week or iso_week_label()
    existing = store.get_book_plan(thesis_id, week)

    if existing and not force:
        if merge_only:
            draft = _compute_draft(store, thesis, week)
            existing_ids = {s["company_id"] for s in existing.get("slots") or []}
            to_merge = [s for s in draft["slots"] if s["company_id"] not in existing_ids]
            if to_merge:
                plan = store.merge_companies_into_book_plan(existing["id"], to_merge)
            else:
                plan = existing
            return _enrich_slots_with_companies(store, plan)
        return _enrich_slots_with_companies(store, existing)

    if force and existing:
        store.supersede_book_plans(thesis_id, week)

    draft = _compute_draft(store, thesis, week)
    for edge in draft.get("substitute_edges") or []:
        store.add_company_relationship(
            edge["company_id"],
            edge["related_company_id"],
            edge["relationship_type"],
            confidence=edge.get("confidence", 0.75),
        )

    brief_text = None
    if with_brief:
        brief_text = _maybe_weekly_brief(store, thesis, draft)

    plan = store.save_book_plan(thesis_id, workspace_id, draft, brief=brief_text)
    return _enrich_slots_with_companies(store, plan)


def _compute_draft(store: Any, thesis: Dict[str, Any], week: str) -> Dict[str, Any]:
    """Build a week plan draft from current opportunities."""
    from workers.intelligence.book_of_work import is_expired as bow_expired

    opps = store.list_opportunities(thesis["id"])
    # Include open recommendations even if expired (for stale slots)
    ws = store.get_workspace(thesis["workspace_id"]) or {}
    cadence = resolve_cadence(ws.get("settings"), thesis.get("strategy"))

    research_tasks: Dict[str, List[Dict[str, Any]]] = {}
    for opp in opps:
        company = opp.get("company") or {}
        cid = opp.get("company_id") or company.get("id")
        if not cid:
            continue
        rec = opp.get("recommendation") or {}
        if bow_expired(rec):
            continue
        signals = store.list_signals(cid)
        contacts = store.list_contacts(cid)
        tasks = estimate_research_lift(
            opp, company, thesis, signals, contacts, peer_count=max(3, len(opps))
        )
        if tasks:
            research_tasks[cid] = tasks

    return build_week_plan(
        opps,
        thesis,
        cadence,
        research_tasks=research_tasks,
        iso_week=week,
    )


def complete_slot(
    store: Any,
    slot_id: str,
    *,
    outcome: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Mark slot completed, log activity, bump pipeline."""
    slot = store.get_book_slot(slot_id)
    if not slot:
        raise ValueError("Slot not found")
    if slot.get("status") != "open":
        return _enrich_slots_with_companies(
            store, store.get_book_plan_by_id(slot["plan_id"])  # type: ignore[arg-type]
        )

    store.update_book_slot(slot_id, status="completed")
    plan = store.get_book_plan_by_id(slot["plan_id"])
    thesis_id = (plan or {}).get("thesis_id")
    company_id = slot["company_id"]

    if slot.get("recommendation_id"):
        store.update_recommendation(slot["recommendation_id"], status="completed")

    stage = "outreach" if slot.get("kind") == "outreach" else "researching"
    if thesis_id:
        store.upsert_pipeline(company_id, thesis_id, stage=stage, notes=notes or "")

    store.add_activity(
        company_id=company_id,
        recommendation_id=slot.get("recommendation_id"),
        activity_type="book_of_work_complete",
        outcome=outcome or "completed",
        metadata={
            "slot_id": slot_id,
            "kind": slot.get("kind"),
            "plan_id": slot.get("plan_id"),
            "notes": notes,
        },
    )
    return _enrich_slots_with_companies(store, store.get_book_plan_by_id(slot["plan_id"]))  # type: ignore[arg-type]


def skip_slot(store: Any, slot_id: str, *, notes: Optional[str] = None) -> Dict[str, Any]:
    """Skip an outreach slot and optionally promote a substitute hold."""
    slot = store.get_book_slot(slot_id)
    if not slot:
        raise ValueError("Slot not found")
    plan = store.get_book_plan_by_id(slot["plan_id"])
    if not plan:
        raise ValueError("Plan not found")

    if slot.get("status") != "open":
        return _enrich_slots_with_companies(store, plan)

    store.update_book_slot(slot_id, status="skipped")
    store.add_activity(
        company_id=slot["company_id"],
        recommendation_id=slot.get("recommendation_id"),
        activity_type="book_of_work_skip",
        outcome="skipped",
        metadata={"slot_id": slot_id, "kind": slot.get("kind"), "notes": notes},
    )

    # Re-read slots after status update
    plan = store.get_book_plan_by_id(slot["plan_id"])
    slots = plan.get("slots") or []
    promote = promote_on_skip(slots, slot_id)
    if promote:
        # Promote hold → outreach with next rank
        outreach_ranks = [s.get("rank") or 0 for s in slots if s.get("kind") == "outreach"]
        next_rank = max(outreach_ranks or [0]) + 1
        store.update_book_slot(
            promote["id"],
            kind="outreach",
            rank=next_rank,
            reason=f"Promoted after skip of sibling — {promote.get('reason') or ''}",
            status="open",
        )
        store.add_activity(
            company_id=promote["company_id"],
            recommendation_id=promote.get("recommendation_id"),
            activity_type="book_of_work_promote",
            outcome="promoted",
            metadata={"slot_id": promote["id"], "from_skip": slot_id},
        )

    return _enrich_slots_with_companies(store, store.get_book_plan_by_id(slot["plan_id"]))  # type: ignore[arg-type]


def _maybe_weekly_brief(store: Any, thesis: Dict[str, Any], draft: Dict[str, Any]) -> Optional[str]:
    """Generate LLM weekly brief from already-chosen slots; never invent companies."""
    try:
        from workers.llm.client import generate_weekly_brief

        slots = draft.get("slots") or []
        packed = [s for s in slots if s.get("kind") in ("outreach", "research")]
        companies = []
        evidence_refs = []
        for s in packed[:12]:
            c = store.get_company(s["company_id"])
            if c:
                companies.append(
                    {
                        "name": c.get("canonical_name"),
                        "kind": s.get("kind"),
                        "reason": s.get("reason"),
                        "window_closes_at": s.get("window_closes_at"),
                    }
                )
            for e in store.list_evidence(s["company_id"])[:2]:
                if e.get("id"):
                    evidence_refs.append(e["id"])
        result = generate_weekly_brief(
            thesis_name=thesis.get("name") or "Thesis",
            iso_week=draft.get("iso_week"),
            cadence=draft.get("cadence") or {},
            slots=companies,
            evidence_ids=evidence_refs,
        )
        return result.get("brief") or result.get("weekly_brief")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Weekly brief skipped: %s", exc)
        return None
