"""Google Places discovery adapter."""

from __future__ import annotations

import logging
from typing import Iterator, List
from urllib.parse import urlparse

import httpx

from workers.discovery.adapters.base import RawRecord, SearchQuery, SourceCapabilities

logger = logging.getLogger(__name__)


class PlacesAdapter:
    """Search establishments via Google Places Text Search API."""

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities(search=True, fetch=True, rate_limit_per_minute=30)

    def search(self, query: SearchQuery) -> Iterator[RawRecord]:
        if not self.api_key:
            logger.info("Places API key missing — yielding demo Places-like records")
            yield from self._demo_search(query)
            return

        text = query.text
        if query.industry_keywords:
            text = f"{' '.join(query.industry_keywords[:3])} {query.location or ''}".strip() or text

        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {"query": text, "key": self.api_key}
        if query.latitude is not None and query.longitude is not None:
            params["location"] = f"{query.latitude},{query.longitude}"
            params["radius"] = str(query.radius_m)

        fetched = 0
        next_page = None
        with httpx.Client(timeout=30.0) as client:
            while fetched < query.max_results:
                p = dict(params)
                if next_page:
                    p = {"pagetoken": next_page, "key": self.api_key}
                resp = client.get(url, params=p)
                resp.raise_for_status()
                data = resp.json()
                if data.get("status") not in ("OK", "ZERO_RESULTS"):
                    logger.error("Places API status=%s error=%s", data.get("status"), data.get("error_message"))
                    break
                for item in data.get("results", []):
                    if fetched >= query.max_results:
                        break
                    place_id = item.get("place_id") or item.get("name")
                    yield RawRecord(source="google_places", external_id=place_id, payload=item)
                    fetched += 1
                next_page = data.get("next_page_token")
                if not next_page:
                    break

    def fetch(self, external_id: str) -> RawRecord:
        if not self.api_key:
            return RawRecord(source="google_places", external_id=external_id, payload={"place_id": external_id})
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": external_id,
            "fields": "name,formatted_address,formatted_phone_number,international_phone_number,website,url,geometry,types,rating,user_ratings_total,business_status",
            "key": self.api_key,
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            return RawRecord(source="google_places", external_id=external_id, payload=data.get("result") or {})

    def _demo_search(self, query: SearchQuery) -> Iterator[RawRecord]:
        """Deterministic fake Places results for offline demos."""
        loc = query.location or "Phoenix, AZ"
        samples = [
            ("Ch_demo_valley", "Valley Climate Control", "2140 Industrial Blvd, Phoenix, AZ", 33.45, -112.07),
            ("Ch_demo_gulf", "Gulf Coast Air Pros", "88 Bayshore Dr, Tampa, FL", 27.95, -82.46),
            ("Ch_demo_lone", "Lone Star Mechanical", "4500 Commerce St, Houston, TX", 29.76, -95.37),
            ("Ch_demo_bay", "Bay Area Comfort Systems", "1200 Harbor Rd, Oakland, CA", 37.80, -122.27),
            ("Ch_demo_desert", "Desert Peak Heating & Cooling", "33 Mesa Ave, Scottsdale, AZ", 33.49, -111.93),
        ]
        for i, (pid, name, addr, lat, lng) in enumerate(samples[: query.max_results]):
            yield RawRecord(
                source="google_places",
                external_id=pid,
                payload={
                    "place_id": pid,
                    "name": name,
                    "formatted_address": addr,
                    "geometry": {"location": {"lat": lat, "lng": lng}},
                    "types": ["hvac_contractor", "point_of_interest", "establishment"],
                    "rating": 4.3 + (i % 5) * 0.1,
                    "user_ratings_total": 40 + i * 17,
                    "business_status": "OPERATIONAL",
                    "demo_query": query.text,
                    "demo_location": loc,
                },
            )


def domain_from_website(website: str | None) -> str | None:
    """Normalize a website URL to a bare domain."""
    if not website:
        return None
    if not website.startswith("http"):
        website = "https://" + website
    host = urlparse(website).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host or None


def normalize_phone(phone: str | None) -> str | None:
    """Keep digits with leading + when possible."""
    if not phone:
        return None
    digits = "".join(c for c in phone if c.isdigit())
    if not digits:
        return None
    if phone.strip().startswith("+"):
        return "+" + digits
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    return digits
