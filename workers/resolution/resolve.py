"""Entity resolution: exact → composite → fuzzy."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


def normalize_name(name: str) -> str:
    """Normalize company name for matching."""
    n = name.lower().strip()
    n = re.sub(r"[,.]", " ", n)
    n = re.sub(
        r"\b(llc|inc|ltd|corp|co|company|services|service)\b\.?",
        " ",
        n,
    )
    n = re.sub(r"\s+", " ", n).strip()
    return n


def _companies(store: Any, workspace_id: Optional[str]) -> List[Dict[str, Any]]:
    """Load candidates via the store protocol (never DemoStore attributes)."""
    return store.list_companies(workspace_id)


def exact_match(
    store: Any,
    domain: Optional[str],
    phone: Optional[str],
    source: str,
    external_id: str,
    workspace_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Pass 1 — exact domain, phone, or known source id."""
    for src in store.list_company_sources():
        if src["source"] == source and src["external_id"] == external_id:
            company = store.get_company(src["company_id"])
            if company and (not workspace_id or company.get("workspace_id") == workspace_id):
                return company
    if domain:
        needle = domain.lower()
        for c in _companies(store, workspace_id):
            if (c.get("domain") or "").lower() == needle:
                return store.get_company(c["id"])
    if phone:
        for c in _companies(store, workspace_id):
            if c.get("phone_norm") == phone:
                return store.get_company(c["id"])
    return None


def composite_match(
    store: Any,
    name: str,
    city: Optional[str],
    phone: Optional[str],
    domain: Optional[str],
    workspace_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Pass 2 — deterministic composite keys."""
    nn = normalize_name(name)
    for c in _companies(store, workspace_id):
        cn = normalize_name(c.get("canonical_name") or "")
        c_city = ((c.get("geo") or {}).get("city") or "").lower()
        if nn == cn and city and c_city == city.lower():
            return store.get_company(c["id"])
        if nn == cn and phone and c.get("phone_norm") == phone:
            return store.get_company(c["id"])
        if nn == cn and domain and (c.get("domain") or "").lower() == domain.lower():
            return store.get_company(c["id"])
    return None


def fuzzy_match(
    store: Any,
    name: str,
    city: Optional[str] = None,
    threshold: int = 92,
    workspace_id: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], float]:
    """Pass 3 — high-threshold fuzzy; low confidence must not merge."""
    nn = normalize_name(name)
    best = None
    best_score = 0.0
    for c in _companies(store, workspace_id):
        cn = normalize_name(c.get("canonical_name") or "")
        score = float(fuzz.token_sort_ratio(nn, cn))
        if city:
            c_city = ((c.get("geo") or {}).get("city") or "").lower()
            if c_city and c_city != city.lower():
                score *= 0.85
        if score > best_score:
            best_score = score
            best = c
    if best and best_score >= threshold:
        return store.get_company(best["id"]), best_score / 100.0
    return None, best_score / 100.0


def resolve_company(
    store,
    *,
    name: str,
    domain: Optional[str],
    phone: Optional[str],
    address: Optional[str],
    geo: Optional[dict],
    industry: Optional[str],
    source: str,
    external_id: str,
    workspace_id: Optional[str],
    extra: Optional[dict] = None,
) -> Dict[str, Any]:
    """Resolve or create a canonical company; never silently merge low-confidence."""
    city = (geo or {}).get("city")
    matched = exact_match(store, domain, phone, source, external_id, workspace_id)
    confidence = 1.0
    if not matched:
        matched = composite_match(store, name, city, phone, domain, workspace_id)
        confidence = 0.9
    if not matched:
        matched, confidence = fuzzy_match(store, name, city, workspace_id=workspace_id)
        if matched and confidence < 0.92:
            logger.info("Fuzzy match below threshold for %s (%.2f); creating new entity", name, confidence)
            matched = None

    payload = {
        "canonical_name": name,
        "domain": domain,
        "phone_norm": phone,
        "address": address,
        "geo": geo,
        "industry": industry,
        "workspace_id": workspace_id,
    }
    if extra:
        for k in ("revenue_est", "founded_year"):
            if extra.get(k) is not None:
                payload[k] = extra[k]

    if matched:
        company = store.upsert_company({**matched, **{k: v for k, v in payload.items() if v is not None}})
    else:
        company = store.upsert_company(payload)

    store.add_company_source(company["id"], source, external_id, confidence=confidence)
    return company
