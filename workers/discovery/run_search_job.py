"""Search job pipeline: discover → resolve → evidence → signals → score → recommend."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from apps.api.app.core.config import get_settings
from apps.api.app.core.store import get_store
from workers.discovery.adapters.maps import PlacesAdapter, domain_from_website, normalize_phone
from workers.discovery.adapters.web import WebAdapter
from workers.intelligence.engines import compute_opportunity, next_best_action
from workers.resolution.resolve import resolve_company
from workers.signals.extractors import extract_from_places, extract_from_web, seed_age_signal

logger = logging.getLogger(__name__)


def _parse_address_geo(payload: Dict[str, Any]) -> tuple[Optional[str], Dict[str, Any]]:
    address = payload.get("formatted_address") or payload.get("vicinity")
    loc = (payload.get("geometry") or {}).get("location") or {}
    geo: Dict[str, Any] = {}
    if loc:
        geo["lat"] = loc.get("lat")
        geo["lng"] = loc.get("lng")
    # Naive state parse from US address
    if address:
        parts = [p.strip() for p in address.split(",")]
        if len(parts) >= 2:
            geo["city"] = parts[-3] if len(parts) >= 3 else parts[0]
            state_zip = parts[-2] if len(parts) >= 2 else ""
            tokens = state_zip.split()
            if tokens:
                geo["state"] = tokens[0]
            geo["country"] = "US"
    return address, geo


def run_search_job(job_id: str, store: Optional[Any] = None) -> Dict[str, Any]:
    """Execute a full discovery + intelligence pass for a search job."""
    store = store or get_store()
    settings = get_settings()
    job = store.get_search_job(job_id)
    if not job:
        raise ValueError(f"Search job not found: {job_id}")

    thesis = store.get_thesis(job["thesis_id"])
    if not thesis:
        raise ValueError("Thesis not found for job")

    store.update_search_job(job_id, status="running", stats={"phase": "discovery"})
    criteria = thesis.get("criteria") or {}
    industries = criteria.get("industries") or ["business"]
    geos = criteria.get("geographies") or [{"country": "US", "states": ["CA"]}]
    location = job["query"].get("location")
    if not location:
        states = (geos[0].get("states") or ["CA"])
        location = f"{states[0]}, US"

    query_text = " ".join(industries[:2]) + f" companies in {location}"
    adapter = PlacesAdapter(api_key=settings.google_places_api_key)
    web = WebAdapter()

    from workers.discovery.adapters.base import SearchQuery

    sq = SearchQuery(
        text=query_text,
        location=location,
        max_results=int(job["query"].get("max_results") or 20),
        industry_keywords=list(industries),
    )

    discovered = 0
    company_ids = []
    for record in adapter.search(sq):
        store.insert_raw_lead(job_id, record.source, record.external_id, record.payload)
        discovered += 1

        # Enrich with details when API key present
        payload = record.payload
        if settings.google_places_api_key and record.external_id:
            try:
                detail = adapter.fetch(record.external_id)
                payload = {**payload, **(detail.payload or {})}
                store.insert_raw_lead(job_id, "google_places_details", record.external_id, detail.payload)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Places details failed: %s", exc)

        address, geo = _parse_address_geo(payload)
        website = payload.get("website")
        domain = domain_from_website(website)
        phone = normalize_phone(
            payload.get("international_phone_number") or payload.get("formatted_phone_number")
        )
        industry = industries[0] if industries else None
        types = payload.get("types") or []
        if not industry and types:
            industry = types[0].replace("_", " ")

        company = resolve_company(
            store,
            name=payload.get("name") or "Unknown",
            domain=domain,
            phone=phone,
            address=address,
            geo=geo or None,
            industry=industry,
            source=record.source,
            external_id=record.external_id,
            workspace_id=thesis["workspace_id"],
        )
        company_ids.append(company["id"])
        extract_from_places(store, company["id"], payload)

        if phone and not store.list_contacts(company["id"]):
            store.add_contact(
                company["id"],
                name=None,
                title=None,
                phone=phone,
                owner_estimate=False,
                confidence=0.4,
            )

        if website:
            store.log_compliance(
                company_id=company["id"],
                action="robots_check",
                source="web",
                detail=website,
                robots_allowed=web.robots_allowed(website),
                policy_allowed=True,
            )
            web_record, allowed = web.fetch_if_allowed(website)
            store.insert_raw_lead(job_id, "web", website, web_record.payload)
            if allowed and not web_record.payload.get("blocked"):
                extract_from_web(store, company["id"], web_record.payload)
            elif domain and domain.endswith(".example"):
                # Demo domains: synthesize website evidence
                synthetic = {
                    "url": f"https://{domain}/",
                    "title": company["canonical_name"],
                    "text_snippet": (
                        f"{company['canonical_name']} is a family-owned HVAC company "
                        f"serving {(geo or {}).get('city', 'the region')} since "
                        f"{company.get('founded_year') or 1995}. Contact us today."
                    ),
                    "blocked": False,
                }
                extract_from_web(store, company["id"], synthetic)

        seed_age_signal(store, company["id"])

    # Score all touched companies
    store.update_search_job(job_id, stats={"phase": "scoring", "discovered": discovered})
    peer_count = max(1, len(set(company_ids)))
    scored = 0
    for cid in set(company_ids):
        company = store.get_company(cid)
        if not company:
            continue
        signals = store.list_signals(cid)
        contacts = store.list_contacts(cid)
        opp = compute_opportunity(company, thesis, signals, contacts, peer_count=peer_count)
        seller = opp.pop("seller_breakdown")
        store.add_seller_score(seller)
        store.add_opportunity_score(opp)
        nba = next_best_action(opp, signals=signals)
        store.upsert_recommendation(cid, thesis["id"], **nba)
        store.upsert_pipeline(cid, thesis["id"], stage="identified")
        scored += 1

    stats = {"discovered": discovered, "scored": scored, "phase": "done"}
    store.update_search_job(job_id, status="completed", stats=stats)

    # Refresh / merge current week's Book of Work so discovery changes Monday's queue
    try:
        from workers.intelligence.book_of_work import iso_week_label
        from workers.intelligence.book_service import ensure_book_of_work

        existing = store.get_book_plan(thesis["id"], iso_week_label())
        if existing:
            ensure_book_of_work(store, thesis["id"], force=False, merge_only=True)
        else:
            ensure_book_of_work(store, thesis["id"], force=False, with_brief=False)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Book of Work refresh after search job failed: %s", exc)

    logger.info("Search job %s completed: %s", job_id, stats)
    return stats


def score_company(company_id: str, thesis_id: str, store: Optional[Any] = None) -> Dict[str, Any]:
    """Recompute opportunity score for one company/thesis."""
    store = store or get_store()
    company = store.get_company(company_id)
    thesis = store.get_thesis(thesis_id)
    if not company or not thesis:
        raise ValueError("Company or thesis not found")
    signals = store.list_signals(company_id)
    contacts = store.list_contacts(company_id)
    peers = len(store.list_companies(thesis.get("workspace_id")))
    opp = compute_opportunity(company, thesis, signals, contacts, peer_count=peers)
    seller = opp.pop("seller_breakdown")
    store.add_seller_score(seller)
    stored = store.add_opportunity_score(opp)
    nba = next_best_action(opp, signals=signals)
    store.upsert_recommendation(company_id, thesis_id, **nba)
    return stored
