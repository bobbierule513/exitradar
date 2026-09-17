"""Signal extractors from Places payloads and web evidence."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def extract_from_places(store, company_id: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Create evidence + signals from a Google Places payload."""
    created = []
    rating = payload.get("rating")
    reviews = payload.get("user_ratings_total")
    snippet = (
        f"Places rating={rating}, reviews={reviews}, "
        f"status={payload.get('business_status')}, types={payload.get('types')}"
    )
    ev = store.add_evidence(
        company_id,
        source="google_places",
        type="places_stats",
        url=payload.get("url"),
        snippet=snippet,
        confidence=0.85,
        metadata={"rating": rating, "user_ratings_total": reviews},
    )
    created.append(ev)

    if reviews is not None:
        trend = "flat"
        if reviews > 100:
            trend = "active"
        elif reviews < 15:
            trend = "thin"
        store.upsert_signal(company_id, "review_trend", trend, 0.55)

    types = payload.get("types") or []
    if types:
        store.upsert_signal(company_id, "places_types", types[:8], 0.9)

    return created


def extract_from_web(store, company_id: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract website freshness, ownership hints, succession language."""
    if payload.get("blocked"):
        store.log_compliance(
            company_id=company_id,
            action="fetch_blocked",
            source="web",
            detail=payload.get("reason"),
            robots_allowed=payload.get("reason") != "robots_disallow",
            policy_allowed=True,
        )
        return []

    text = (payload.get("text_snippet") or "") + " " + (payload.get("title") or "")
    ev = store.add_evidence(
        company_id,
        source="web",
        type="website_snippet",
        url=payload.get("url"),
        snippet=text[:800],
        confidence=0.75,
        metadata={"title": payload.get("title")},
    )

    # Freshness heuristic: copyright year / "updated"
    freshness = "unknown"
    years = [int(y) for y in re.findall(r"20[0-2][0-9]", text)]
    if years:
        latest = max(years)
        freshness = "active" if latest >= 2024 else "stale"
    store.upsert_signal(company_id, "website_freshness", freshness, 0.65 if years else 0.35)

    # Founded year
    m = re.search(r"(?:since|founded|est\.?|established)\s+(19|20)\d{2}", text, re.I)
    if m:
        # re-find full year
        m2 = re.search(r"(?:since|founded|est\.?|established)\s+((?:19|20)\d{2})", text, re.I)
        if m2:
            year = int(m2.group(1))
            store.upsert_signal(company_id, "business_age_years", 2026 - year, 0.7)
            company = store.get_company(company_id)
            if company and not company.get("founded_year"):
                store.upsert_company({**company, "founded_year": year})

    lower = text.lower()
    if any(k in lower for k in ("family owned", "family-owned", "third generation", "no successor")):
        store.upsert_signal(company_id, "succession_indicator", "no_visible_successor", 0.6)
    if any(k in lower for k in ("owner", "principal", "founder", "president")):
        store.upsert_signal(company_id, "owner_identified", True, 0.55)

    if any(k in lower for k in ("we're hiring", "we are hiring", "careers", "join our team")):
        store.upsert_signal(company_id, "hiring_trend", "up", 0.5)
    elif "career" in lower and "404" in lower:
        store.upsert_signal(company_id, "hiring_trend", "none", 0.4)

    if any(k in lower for k in ("new general manager", "new gm", "leadership change", "formerly")):
        store.upsert_signal(company_id, "leadership_change", True, 0.5)

    # Contact email scrape (business only)
    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    emails = [e for e in emails if not e.endswith((".png", ".jpg"))]
    if emails:
        contacts = store.list_contacts(company_id)
        if not any(c.get("email") for c in contacts):
            store.add_contact(
                company_id,
                name=None,
                title=None,
                email=emails[0],
                phone=None,
                owner_estimate=False,
                confidence=0.5,
            )

    return [ev]


def seed_age_signal(store, company_id: str) -> None:
    """Ensure business_age signal when founded_year is known."""
    company = store.get_company(company_id)
    if company and company.get("founded_year"):
        age = 2026 - int(company["founded_year"])
        store.upsert_signal(company_id, "business_age_years", age, 0.9)
