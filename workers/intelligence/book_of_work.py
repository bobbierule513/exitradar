"""Weekly Book of Work planner — capacity-aware sequencing of outreach and research.

Policy version: bow-v1. Pure deterministic functions; LLM never picks slots.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import uuid4

from apps.api.app.core.scoring import (
    BOOK_OF_WORK_VERSION,
    DEFAULT_CADENCE,
    RESEARCH_GAP_HOURS,
    REVENUE_BAND_RATIO,
    SUBSTITUTE_RADIUS_MILES,
)
from workers.intelligence.engines import compute_opportunity

logger = logging.getLogger(__name__)

OUTREACH_ACTIONS = frozenset({"CONTACT_NOW", "RELATIONSHIP_FIRST"})
SLOT_KINDS = ("outreach", "research", "hold", "stale")


def iso_week_label(when: Optional[datetime] = None) -> str:
    """Return ISO week string like 2026-W38."""
    when = when or datetime.now(timezone.utc)
    year, week, _ = when.isocalendar()
    return f"{year}-W{week:02d}"


def _parse_dt(value: Any) -> Optional[datetime]:
    """Parse ISO datetime string or datetime into aware UTC datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in miles between two WGS84 points."""
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def resolve_cadence(
    workspace_settings: Optional[Dict[str, Any]] = None,
    thesis_strategy: Optional[Dict[str, Any]] = None,
) -> Dict[str, int]:
    """Merge default, workspace, and thesis cadence overrides."""
    cadence = dict(DEFAULT_CADENCE)
    ws = (workspace_settings or {}).get("cadence") or {}
    for key in DEFAULT_CADENCE:
        if key in ws and ws[key] is not None:
            cadence[key] = int(ws[key])
    ts = (thesis_strategy or {}).get("cadence") or {}
    for key in DEFAULT_CADENCE:
        if key in ts and ts[key] is not None:
            cadence[key] = int(ts[key])
    return cadence


def revenue_same_band(a: Optional[float], b: Optional[float]) -> bool:
    """True when revenues are within REVENUE_BAND_RATIO of each other (or both missing)."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return True  # incomplete size → allow geo+industry cluster
    lo, hi = min(float(a), float(b)), max(float(a), float(b))
    if lo <= 0:
        return True
    return (hi - lo) / lo <= REVENUE_BAND_RATIO


def are_substitutes(company_a: Dict[str, Any], company_b: Dict[str, Any]) -> bool:
    """Same industry + within SUBSTITUTE_RADIUS_MILES + similar revenue band."""
    if company_a.get("id") == company_b.get("id"):
        return False
    ind_a = (company_a.get("industry") or "").strip().lower()
    ind_b = (company_b.get("industry") or "").strip().lower()
    if not ind_a or not ind_b or ind_a != ind_b:
        return False
    geo_a = company_a.get("geo") or {}
    geo_b = company_b.get("geo") or {}
    try:
        lat1, lon1 = float(geo_a["lat"]), float(geo_a["lng"])
        lat2, lon2 = float(geo_b["lat"]), float(geo_b["lng"])
    except (KeyError, TypeError, ValueError):
        # Fallback: same city+state counts as substitute metro
        city_a = (geo_a.get("city") or "").strip().lower()
        city_b = (geo_b.get("city") or "").strip().lower()
        state_a = (geo_a.get("state") or "").strip().upper()
        state_b = (geo_b.get("state") or "").strip().upper()
        if not (city_a and city_b and state_a == state_b):
            # Phoenix/Scottsdale: treat same state metro loosely via city aliases
            metro_aliases = {
                "phoenix": "phx_metro",
                "scottsdale": "phx_metro",
                "mesa": "phx_metro",
                "tempe": "phx_metro",
            }
            m1 = metro_aliases.get(city_a)
            m2 = metro_aliases.get(city_b)
            if not (m1 and m2 and m1 == m2 and state_a == state_b):
                return False
        if not revenue_same_band(company_a.get("revenue_est"), company_b.get("revenue_est")):
            return False
        return True
    if haversine_miles(lat1, lon1, lat2, lon2) > SUBSTITUTE_RADIUS_MILES:
        return False
    return revenue_same_band(company_a.get("revenue_est"), company_b.get("revenue_est"))


def build_substitute_clusters(
    companies: Sequence[Dict[str, Any]],
) -> Tuple[Dict[str, str], List[Dict[str, Any]]]:
    """Union-find clusters of substitute companies.

    Returns (company_id → cluster_id, undirected relationship edge dicts).
    """
    ids = [c["id"] for c in companies]
    parent = {i: i for i in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    edges: List[Dict[str, Any]] = []
    by_id = {c["id"]: c for c in companies}
    for i, cid in enumerate(ids):
        for other in ids[i + 1 :]:
            if are_substitutes(by_id[cid], by_id[other]):
                union(cid, other)
                edges.append(
                    {
                        "company_id": cid,
                        "related_company_id": other,
                        "relationship_type": "substitute",
                        "confidence": 0.75,
                    }
                )
    cluster_map = {cid: find(cid) for cid in ids}
    return cluster_map, edges


def is_expired(recommendation: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    """True when recommendation expires_at is in the past."""
    now = now or datetime.now(timezone.utc)
    exp = _parse_dt(recommendation.get("expires_at"))
    if exp is None:
        return False
    return exp < now


def days_until_expiry(recommendation: Dict[str, Any], now: Optional[datetime] = None) -> float:
    """Days until expires_at; large number if missing."""
    now = now or datetime.now(timezone.utc)
    exp = _parse_dt(recommendation.get("expires_at"))
    if exp is None:
        return 999.0
    return (exp - now).total_seconds() / 86400.0


def estimate_research_lift(
    opportunity: Dict[str, Any],
    company: Dict[str, Any],
    thesis: Dict[str, Any],
    signals: List[Dict[str, Any]],
    contacts: List[Dict[str, Any]],
    peer_count: int = 5,
) -> List[Dict[str, Any]]:
    """Rank missing-field research tasks by expected lift / hours."""
    missing = list((opportunity.get("explanation") or {}).get("missing") or [])
    results: List[Dict[str, Any]] = []
    base_score = float(opportunity.get("opportunity_score") or 0)
    base_conf = float(opportunity.get("confidence") or 0)

    for field in missing:
        if field not in RESEARCH_GAP_HOURS:
            continue
        hours = RESEARCH_GAP_HOURS[field]
        patched_company = dict(company)
        patched_contacts = list(contacts)
        if field == "founded_year" and patched_company.get("founded_year") is None:
            patched_company["founded_year"] = 1995
        elif field == "revenue_est" and patched_company.get("revenue_est") is None:
            criteria = thesis.get("criteria") or {}
            lo = criteria.get("revenue_min") or 2_000_000
            hi = criteria.get("revenue_max") or 10_000_000
            patched_company["revenue_est"] = (float(lo) + float(hi)) / 2.0
        elif field == "contacts" and not patched_contacts:
            patched_contacts = [
                {
                    "id": "hypothetical",
                    "company_id": company["id"],
                    "name": "Owner",
                    "owner_estimate": True,
                    "email": "owner@example.com",
                    "phone": company.get("phone_norm"),
                    "confidence": 0.7,
                }
            ]
        else:
            continue

        replayed = compute_opportunity(
            patched_company, thesis, signals, patched_contacts, peer_count=peer_count
        )
        score_lift = float(replayed["opportunity_score"]) - base_score
        conf_lift = float(replayed["confidence"]) - base_conf
        combined = max(0.0, score_lift) + max(0.0, conf_lift) * 40.0
        results.append(
            {
                "field": field,
                "hours": hours,
                "score_lift": round(score_lift, 2),
                "confidence_lift": round(conf_lift, 3),
                "expected_lift": round(combined, 2),
                "lift_per_hour": round(combined / hours, 2) if hours else 0.0,
                "company_id": company["id"],
            }
        )
    results.sort(key=lambda r: r["lift_per_hour"], reverse=True)
    return results


def _company_name(company: Optional[Dict[str, Any]]) -> str:
    if not company:
        return "peer"
    return company.get("canonical_name") or "peer"


def build_week_plan(
    opportunities: List[Dict[str, Any]],
    thesis: Dict[str, Any],
    cadence: Dict[str, int],
    research_tasks: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    now: Optional[datetime] = None,
    iso_week: Optional[str] = None,
) -> Dict[str, Any]:
    """Pack a weekly Book of Work from ranked opportunities + research ROI.

    opportunities items should include company, recommendation, opportunity_score,
    and explanation (missing, timing_bucket).
    """
    now = now or datetime.now(timezone.utc)
    week = iso_week or iso_week_label(now)
    research_tasks = research_tasks or {}
    companies = [o["company"] for o in opportunities if o.get("company")]
    cluster_map, edges = build_substitute_clusters(companies)
    by_id = {c["id"]: c for c in companies}

    max_outreach = int(cadence.get("max_outreach_per_week", 5))
    max_research = int(cadence.get("max_research_slots", 4))

    stale_slots: List[Dict[str, Any]] = []
    outreach_candidates: List[Dict[str, Any]] = []
    hold_candidates: List[Dict[str, Any]] = []

    for opp in opportunities:
        company = opp.get("company") or {}
        rec = opp.get("recommendation") or {}
        cid = opp.get("company_id") or company.get("id")
        if not cid:
            continue
        action = rec.get("action") or "MONITOR"
        expired = is_expired(rec, now)
        cluster_id = cluster_map.get(cid, cid)

        if expired:
            stale_slots.append(
                {
                    "kind": "stale",
                    "company_id": cid,
                    "recommendation_id": rec.get("id"),
                    "cluster_id": cluster_id,
                    "window_closes_at": rec.get("expires_at"),
                    "reason": f"Window expired — was {action}; downgrade to MONITOR.",
                    "expected_lift": None,
                    "status": "open",
                    "rank": 0,
                    "action": action,
                    "opportunity_score": opp.get("opportunity_score"),
                }
            )
            continue

        if action == "DEPRIORITIZE":
            continue

        if action in OUTREACH_ACTIONS:
            outreach_candidates.append(
                {
                    "opp": opp,
                    "company_id": cid,
                    "rec": rec,
                    "cluster_id": cluster_id,
                    "days_left": days_until_expiry(rec, now),
                    "score": float(opp.get("opportunity_score") or 0),
                }
            )
        else:
            hold_candidates.append(
                {
                    "opp": opp,
                    "company_id": cid,
                    "rec": rec,
                    "cluster_id": cluster_id,
                    "action": action,
                }
            )

    outreach_candidates.sort(key=lambda x: (x["days_left"], -x["score"]))

    slots: List[Dict[str, Any]] = []
    chosen_clusters: Dict[str, str] = {}  # cluster_id → chosen company_id
    outreach_rank = 0

    for cand in outreach_candidates:
        cid = cand["company_id"]
        cluster_id = cand["cluster_id"]
        rec = cand["rec"]
        name = _company_name(by_id.get(cid))
        if cluster_id in chosen_clusters:
            winner_id = chosen_clusters[cluster_id]
            winner_name = _company_name(by_id.get(winner_id))
            slots.append(
                {
                    "kind": "hold",
                    "company_id": cid,
                    "recommendation_id": rec.get("id"),
                    "cluster_id": cluster_id,
                    "window_closes_at": rec.get("expires_at"),
                    "reason": (
                        f"Substitute for {winner_name} — same metro/industry thesis slot."
                    ),
                    "expected_lift": None,
                    "status": "open",
                    "rank": 0,
                    "action": rec.get("action"),
                    "opportunity_score": cand["score"],
                    "chosen_sibling_id": winner_id,
                }
            )
            continue
        if outreach_rank >= max_outreach:
            slots.append(
                {
                    "kind": "hold",
                    "company_id": cid,
                    "recommendation_id": rec.get("id"),
                    "cluster_id": cluster_id,
                    "window_closes_at": rec.get("expires_at"),
                    "reason": f"Over weekly outreach capacity ({max_outreach}).",
                    "expected_lift": None,
                    "status": "open",
                    "rank": 0,
                    "action": rec.get("action"),
                    "opportunity_score": cand["score"],
                }
            )
            continue
        outreach_rank += 1
        chosen_clusters[cluster_id] = cid
        days = cand["days_left"]
        slots.append(
            {
                "kind": "outreach",
                "company_id": cid,
                "recommendation_id": rec.get("id"),
                "cluster_id": cluster_id,
                "window_closes_at": rec.get("expires_at"),
                "reason": (
                    f"{rec.get('action')}: window closes in {max(0, int(days))}d — "
                    f"{rec.get('reason') or name}"
                ),
                "expected_lift": None,
                "status": "open",
                "rank": outreach_rank,
                "action": rec.get("action"),
                "opportunity_score": cand["score"],
            }
        )

    # Research slots from ROI ranking across RESEARCH_MORE / high-lift gaps
    flat_research: List[Dict[str, Any]] = []
    for cid, tasks in research_tasks.items():
        for t in tasks:
            flat_research.append(t)
    # Also pull from opportunity missing when RESEARCH_MORE
    for opp in opportunities:
        company = opp.get("company") or {}
        cid = opp.get("company_id") or company.get("id")
        rec = opp.get("recommendation") or {}
        if not cid or is_expired(rec, now):
            continue
        if cid in research_tasks:
            continue
        # Skip if already computed
        for t in estimate_research_lift(
            opp, company, thesis, [], [], peer_count=5
        ):
            # Without signals this is weak — prefer precomputed research_tasks
            pass

    flat_research.sort(key=lambda r: r.get("lift_per_hour", 0), reverse=True)
    research_rank = 0
    used_research_companies: set[str] = set()
    for task in flat_research:
        if research_rank >= max_research:
            break
        cid = task["company_id"]
        if cid in used_research_companies:
            continue
        # Prefer companies not already in outreach this week
        already_outreach = any(
            s["kind"] == "outreach" and s["company_id"] == cid for s in slots
        )
        if already_outreach:
            continue
        research_rank += 1
        used_research_companies.add(cid)
        rec = next(
            (
                (o.get("recommendation") or {})
                for o in opportunities
                if (o.get("company_id") or (o.get("company") or {}).get("id")) == cid
            ),
            {},
        )
        slots.append(
            {
                "kind": "research",
                "company_id": cid,
                "recommendation_id": rec.get("id"),
                "cluster_id": cluster_map.get(cid, cid),
                "window_closes_at": rec.get("expires_at"),
                "reason": (
                    f"Fill {task['field']} — expected lift {task['expected_lift']} "
                    f"({task['lift_per_hour']}/hr, ~{task['hours']}h)."
                ),
                "expected_lift": task.get("expected_lift"),
                "research_field": task.get("field"),
                "lift_per_hour": task.get("lift_per_hour"),
                "status": "open",
                "rank": research_rank,
                "action": rec.get("action"),
                "opportunity_score": next(
                    (
                        o.get("opportunity_score")
                        for o in opportunities
                        if (o.get("company_id") or (o.get("company") or {}).get("id")) == cid
                    ),
                    None,
                ),
            }
        )

    # Remaining MONITOR / RESEARCH_MORE without research slot → hold
    slotted_ids = {s["company_id"] for s in slots} | {s["company_id"] for s in stale_slots}
    for hold in hold_candidates:
        cid = hold["company_id"]
        if cid in slotted_ids or cid in used_research_companies:
            continue
        rec = hold["rec"]
        slots.append(
            {
                "kind": "hold",
                "company_id": cid,
                "recommendation_id": rec.get("id"),
                "cluster_id": hold["cluster_id"],
                "window_closes_at": rec.get("expires_at"),
                "reason": f"{hold['action']} — not in this week's capacity.",
                "expected_lift": None,
                "status": "open",
                "rank": 0,
                "action": hold["action"],
                "opportunity_score": (hold["opp"] or {}).get("opportunity_score"),
            }
        )

    slots.extend(stale_slots)

    # Assign stable slot ids later in store; planner returns draft slots
    for s in slots:
        s.setdefault("id", str(uuid4()))

    return {
        "iso_week": week,
        "model_version": BOOK_OF_WORK_VERSION,
        "cadence": cadence,
        "generated_at": now.isoformat(),
        "slots": slots,
        "substitute_edges": edges,
        "stats": {
            "outreach": sum(1 for s in slots if s["kind"] == "outreach"),
            "research": sum(1 for s in slots if s["kind"] == "research"),
            "hold": sum(1 for s in slots if s["kind"] == "hold"),
            "stale": sum(1 for s in slots if s["kind"] == "stale"),
        },
    }


def promote_on_skip(
    plan_slots: List[Dict[str, Any]],
    skipped_slot_id: str,
) -> Optional[Dict[str, Any]]:
    """Find a hold slot in the same cluster to promote to outreach.

    Returns the hold slot dict to promote, or None.
    Does not mutate; caller updates status/kind.
    """
    skipped = next((s for s in plan_slots if s.get("id") == skipped_slot_id), None)
    if not skipped or skipped.get("kind") != "outreach":
        return None
    cluster_id = skipped.get("cluster_id")
    holds = [
        s
        for s in plan_slots
        if s.get("kind") == "hold"
        and s.get("cluster_id") == cluster_id
        and s.get("status") == "open"
        and s.get("action") in OUTREACH_ACTIONS
    ]
    if not holds:
        return None
    holds.sort(key=lambda s: (-float(s.get("opportunity_score") or 0),))
    return holds[0]
