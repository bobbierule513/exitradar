"""Seller readiness, thesis fit, timing, access, competition, opportunity, NBA."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from apps.api.app.core.scoring import (
    CONTACT_NOW_WINDOW_CAP_DAYS,
    NBA_ACTIONS,
    NBA_WINDOW_DAYS,
    OPPORTUNITY_SCORE_VERSION,
    OPPORTUNITY_WEIGHTS,
    RECOMMENDATION_VERSION,
    SELLER_READINESS_VERSION,
    SELLER_READINESS_WEIGHTS,
)

logger = logging.getLogger(__name__)


def _signal_map(signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {s["signal_type"]: s for s in signals}


def compute_seller_readiness(
    company: Dict[str, Any],
    signals: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Explainable seller readiness composite (not P(sale))."""
    sm = _signal_map(signals)
    year = company.get("founded_year")
    age = None
    if year:
        age = datetime.now(timezone.utc).year - int(year)
    elif "business_age_years" in sm:
        try:
            age = int(sm["business_age_years"]["value"])
        except (TypeError, ValueError):
            age = None

    # Exit window: older businesses score higher (capped)
    if age is None:
        exit_window, exit_conf = 40.0, 0.3
        exit_note = "Business age unknown — neutral exit window."
    else:
        exit_window = min(100.0, max(0.0, (age - 5) * 4.0))
        exit_conf = 0.85
        exit_note = f"Estimated business age {age} years."

    # Succession vacuum
    owner = sm.get("owner_identified")
    succession_lang = sm.get("succession_indicator")
    if succession_lang and succession_lang.get("value") in ("no_visible_successor", True, "likely"):
        succession = 80.0
        succ_note = "Succession / no-successor language observed."
        succ_conf = float(succession_lang.get("confidence", 0.7))
    elif owner and owner.get("value"):
        succession = 55.0
        succ_note = "Owner/principal identified; successor unknown."
        succ_conf = 0.55
    else:
        succession = 35.0
        succ_note = "No ownership/succession evidence."
        succ_conf = 0.3

    # Digital decay
    freshness = sm.get("website_freshness")
    if freshness and str(freshness.get("value")).lower() in ("stale", "inactive", "decay"):
        digital = 85.0
        dig_note = "Website freshness signal: stale."
        dig_conf = float(freshness.get("confidence", 0.7))
    elif freshness and str(freshness.get("value")).lower() == "active":
        digital = 25.0
        dig_note = "Website appears active."
        dig_conf = float(freshness.get("confidence", 0.7))
    else:
        digital = 45.0
        dig_note = "Website freshness unknown."
        dig_conf = 0.3

    # Stagnation
    hiring = sm.get("hiring_trend")
    reviews = sm.get("review_trend")
    stag = 50.0
    stag_notes = []
    if hiring and str(hiring.get("value")).lower() in ("down", "contracting", "none", "0"):
        stag += 20
        stag_notes.append("Hiring contracted or absent.")
    if reviews and str(reviews.get("value")).lower() in ("flat", "down", "declining"):
        stag += 15
        stag_notes.append(f"Review trend: {reviews.get('value')}.")
    stag = min(100.0, stag)
    stag_note = " ".join(stag_notes) or "Limited stagnation evidence."

    # Recent change
    leadership = sm.get("leadership_change")
    if leadership and leadership.get("value"):
        recent = 75.0
        recent_note = "Leadership change signal present."
        recent_conf = float(leadership.get("confidence", 0.6))
    else:
        recent = 30.0
        recent_note = "No recent leadership change detected."
        recent_conf = 0.4

    w = SELLER_READINESS_WEIGHTS
    total = (
        w["exit_window"] * exit_window
        + w["succession_vacuum"] * succession
        + w["digital_decay"] * digital
        + w["stagnation"] * stag
        + w["recent_change"] * recent
    )
    confidence = min(
        1.0,
        (exit_conf + succ_conf + dig_conf + 0.5 + recent_conf) / 5.0,
    )

    return {
        "company_id": company["id"],
        "exit_window": round(exit_window, 1),
        "succession_vacuum": round(succession, 1),
        "digital_decay": round(digital, 1),
        "stagnation": round(stag, 1),
        "recent_change": round(recent, 1),
        "sri_total": round(total, 1),
        "confidence": round(confidence, 2),
        "model_version": SELLER_READINESS_VERSION,
        "explanation": {
            "exit_window": exit_note,
            "succession_vacuum": succ_note,
            "digital_decay": dig_note,
            "stagnation": stag_note,
            "recent_change": recent_note,
        },
    }


def compute_thesis_fit(company: Dict[str, Any], criteria: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """Deterministic thesis fit with pass/fail explanations."""
    checks = []
    score = 0.0
    weight_sum = 0.0

    def add(name: str, passed: Optional[bool], pts: float, detail: str) -> None:
        nonlocal score, weight_sum
        weight_sum += pts
        if passed is True:
            score += pts
            checks.append({"criterion": name, "passed": True, "detail": detail})
        elif passed is False:
            checks.append({"criterion": name, "passed": False, "detail": detail})
        else:
            # unknown — partial credit
            score += pts * 0.45
            checks.append({"criterion": name, "passed": None, "detail": detail})

    industries = [i.lower() for i in (criteria.get("industries") or [])]
    ind = (company.get("industry") or "").lower()
    if industries:
        passed = any(i in ind or ind in i for i in industries) if ind else None
        add("industry", passed if ind else None, 30, f"company={ind or 'unknown'} thesis={industries}")
    else:
        add("industry", None, 10, "No industry criteria")

    geos = criteria.get("geographies") or []
    geo = company.get("geo") or {}
    if geos:
        states = []
        for g in geos:
            states.extend(g.get("states") or [])
        st = (geo.get("state") or "").upper()
        if states:
            add("geography", (st in [s.upper() for s in states]) if st else None, 25, f"state={st or 'unknown'}")
        else:
            add("geography", True if geo.get("country") else None, 15, "country-level match")
    else:
        add("geography", None, 10, "No geo criteria")

    rmin, rmax = criteria.get("revenue_min"), criteria.get("revenue_max")
    rev = company.get("revenue_est")
    if rmin or rmax:
        if rev is None:
            add("revenue", None, 20, "Revenue unknown")
        else:
            ok = True
            if rmin is not None and rev < rmin:
                ok = False
            if rmax is not None and rev > rmax:
                ok = False
            add("revenue", ok, 20, f"revenue_est={rev}")
    else:
        add("revenue", None, 10, "No revenue band")

    min_years = criteria.get("min_years_in_business")
    year = company.get("founded_year")
    if min_years:
        if year is None:
            add("age", None, 15, "Founded year unknown")
        else:
            age = datetime.now(timezone.utc).year - int(year)
            add("age", age >= int(min_years), 15, f"age={age} min={min_years}")
    else:
        add("age", None, 10, "No min age")

    if criteria.get("owner_operated"):
        # Without hard ownership signal, partial
        add("owner_operated", None, 10, "Owner-operated preferred; evidence partial")

    fit = round(100.0 * score / weight_sum, 1) if weight_sum else 50.0
    return fit, {"checks": checks}


def compute_timing(signals: List[Dict[str, Any]], seller_total: float) -> Tuple[float, str, List[str]]:
    """Timing score + bucket + why_now bullets."""
    sm = _signal_map(signals)
    why = []
    timing = 45.0
    if seller_total >= 80:
        timing += 20
        why.append("Seller readiness elevated.")
    elif seller_total >= 65:
        timing += 10
        why.append("Seller readiness warming.")

    freshness = sm.get("website_freshness")
    if freshness and str(freshness.get("value")).lower() == "stale":
        timing += 12
        why.append("Digital presence appears stale.")

    leadership = sm.get("leadership_change")
    if leadership and leadership.get("value"):
        timing += 15
        why.append("Leadership change detected.")

    hiring = sm.get("hiring_trend")
    if hiring and str(hiring.get("value")).lower() in ("down", "contracting"):
        timing += 8
        why.append("Hiring contracted.")

    timing = min(100.0, timing)
    if timing >= 80:
        bucket = "ready_now"
    elif timing >= 65:
        bucket = "warming_up"
    elif timing >= 45:
        bucket = "watch"
    else:
        bucket = "not_actionable"
    if not why:
        why.append("Limited temporal movement observed.")
    return round(timing, 1), bucket, why


def compute_access(contacts: List[Dict[str, Any]], company: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Access / path-to-decision-maker score."""
    notes = []
    score = 20.0
    if company.get("phone_norm"):
        score += 25
        notes.append("Business phone present.")
    if company.get("domain"):
        score += 10
        notes.append("Domain known.")
    if contacts:
        score += 20
        notes.append(f"{len(contacts)} contact(s) on file.")
        if any(c.get("owner_estimate") for c in contacts):
            score += 15
            notes.append("Owner/principal estimate present.")
        if any(c.get("email") for c in contacts):
            score += 15
            notes.append("Email on file.")
    else:
        notes.append("No contacts — access limited.")
    return min(100.0, score), notes


def compute_competition(company: Dict[str, Any], peer_count: int) -> Tuple[float, List[str]]:
    """Competition advantage: higher when less crowded (low-confidence proxy)."""
    # peer_count = similar companies in same geo/industry from this run
    if peer_count <= 2:
        adv, note = 85.0, f"Low local density proxy (peers={peer_count})."
    elif peer_count <= 6:
        adv, note = 65.0, f"Moderate local density (peers={peer_count})."
    else:
        adv, note = 40.0, f"High local density (peers={peer_count})."
    return adv, [note, "Competition data is incomplete — low confidence."]


def compute_opportunity(
    company: Dict[str, Any],
    thesis: Dict[str, Any],
    signals: List[Dict[str, Any]],
    contacts: List[Dict[str, Any]],
    peer_count: int = 5,
) -> Dict[str, Any]:
    """Versioned opportunity score with explanations and counter-signals."""
    seller = compute_seller_readiness(company, signals)
    fit, fit_expl = compute_thesis_fit(company, thesis.get("criteria") or {})
    timing, bucket, why_now = compute_timing(signals, seller["sri_total"])
    access, access_notes = compute_access(contacts, company)
    competition, comp_notes = compute_competition(company, peer_count)

    w = OPPORTUNITY_WEIGHTS
    total = (
        w["thesis_fit"] * fit
        + w["seller_readiness"] * seller["sri_total"]
        + w["timing"] * timing
        + w["access"] * access
        + w["competition_advantage"] * competition
    )

    counter = []
    sm = _signal_map(signals)
    if sm.get("review_trend") and str(sm["review_trend"].get("value")).lower() in ("up", "increasing"):
        counter.append("Review volume/trend increasing.")
    if timing < 60:
        counter.append("Timing not yet in ready_now band.")
    if access < 50:
        counter.append("Limited verified path to decision-maker.")
    for check in fit_expl.get("checks") or []:
        if check.get("passed") is False:
            counter.append(f"Failed fit: {check['criterion']} — {check['detail']}")

    missing = []
    if company.get("revenue_est") is None:
        missing.append("revenue_est")
    if company.get("founded_year") is None:
        missing.append("founded_year")
    if not contacts:
        missing.append("contacts")

    confidence = round(
        min(
            1.0,
            (seller["confidence"] + (0.8 if company.get("industry") else 0.4) + 0.5) / 3,
        ),
        2,
    )

    return {
        "company_id": company["id"],
        "thesis_id": thesis["id"],
        "fit": fit,
        "seller": seller["sri_total"],
        "timing": timing,
        "access": round(access, 1),
        "competition": round(competition, 1),
        "opportunity_score": round(total, 1),
        "confidence": confidence,
        "model_version": OPPORTUNITY_SCORE_VERSION,
        "seller_breakdown": seller,
        "explanation": {
            "why_now": why_now,
            "counter_signals": counter,
            "missing": missing,
            "timing_bucket": bucket,
            "fit": fit_expl,
            "access_notes": access_notes,
            "competition_notes": comp_notes,
            "seller": seller.get("explanation"),
        },
    }


def recommendation_expires_at(
    action: str,
    now: Optional[datetime] = None,
    trigger_observed_at: Optional[datetime] = None,
) -> Optional[str]:
    """Compute ISO expires_at for an NBA action.

    CONTACT_NOW windows start from the triggering observation when known,
    capped at CONTACT_NOW_WINDOW_CAP_DAYS from now.
    """
    now = now or datetime.now(timezone.utc)
    days = NBA_WINDOW_DAYS.get(action)
    if days is None:
        return None
    if action == "CONTACT_NOW" and trigger_observed_at is not None:
        trigger = trigger_observed_at
        if trigger.tzinfo is None:
            trigger = trigger.replace(tzinfo=timezone.utc)
        expiry = trigger + timedelta(days=days)
        cap = now + timedelta(days=CONTACT_NOW_WINDOW_CAP_DAYS)
        if expiry > cap:
            expiry = cap
        return expiry.isoformat()
    return (now + timedelta(days=days)).isoformat()


def _leadership_trigger_at(signals: Optional[List[Dict[str, Any]]]) -> Optional[datetime]:
    """Best-effort leadership-change observation time for window start."""
    if not signals:
        return None
    for s in signals:
        if s.get("signal_type") == "leadership_change" and s.get("value"):
            raw = s.get("last_observed_at") or s.get("first_observed_at")
            if not raw:
                return None
            try:
                if isinstance(raw, datetime):
                    return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
                return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            except ValueError:
                return None
    return None


def next_best_action(
    opportunity: Dict[str, Any],
    signals: Optional[List[Dict[str, Any]]] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Rule-based NBA from opportunity components, with expires_at."""
    score = opportunity["opportunity_score"]
    timing = opportunity.get("timing") or 0
    access = opportunity.get("access") or 0
    fit = opportunity.get("fit") or 0
    bucket = (opportunity.get("explanation") or {}).get("timing_bucket", "watch")
    missing = (opportunity.get("explanation") or {}).get("missing") or []
    now = now or datetime.now(timezone.utc)

    if fit < 50 or score < 45:
        action = "DEPRIORITIZE"
        reason = "Low thesis fit / opportunity score."
    elif len(missing) >= 3 or (opportunity.get("confidence") or 0) < 0.45:
        action = "RESEARCH_MORE"
        reason = "Material data gaps — research before outreach."
    elif bucket == "ready_now" and access >= 60 and score >= 75:
        action = "CONTACT_NOW"
        reason = (opportunity.get("explanation") or {}).get("why_now", ["High opportunity and access."])[0]
    elif score >= 65 and access < 60:
        action = "RELATIONSHIP_FIRST"
        reason = "Solid opportunity but weak access — warm intro / relationship first."
    elif bucket in ("warming_up", "watch") or score >= 55:
        action = "MONITOR"
        reason = "Watch for temporal movement before committing outreach."
    else:
        action = "DEPRIORITIZE"
        reason = "Not actionable under current evidence."

    assert action in NBA_ACTIONS
    trigger = _leadership_trigger_at(signals) if action == "CONTACT_NOW" else None
    expires = recommendation_expires_at(action, now=now, trigger_observed_at=trigger)
    return {
        "action": action,
        "priority": int(score),
        "reason": reason,
        "model_version": RECOMMENDATION_VERSION,
        "status": "open",
        "expires_at": expires,
    }
