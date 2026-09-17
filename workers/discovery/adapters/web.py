"""Robots-aware website fetch adapter."""

from __future__ import annotations

import logging
import time
from typing import Iterator, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from workers.discovery.adapters.base import RawRecord, SearchQuery, SourceCapabilities

logger = logging.getLogger(__name__)

USER_AGENT = "ExitRadarBot/1.0 (+https://github.com/exitradar; respectful research crawler)"


class WebAdapter:
    """Fetch public pages only when robots.txt allows."""

    def __init__(self, redis_client=None) -> None:
        self.redis = redis_client
        self._robots_cache: dict[str, RobotFileParser] = {}

    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities(search=False, fetch=True, rate_limit_per_minute=10)

    def search(self, query: SearchQuery) -> Iterator[RawRecord]:
        return iter(())

    def robots_allowed(self, url: str) -> bool:
        """Check robots.txt for USER_AGENT."""
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base not in self._robots_cache:
            rp = RobotFileParser()
            robots_url = urljoin(base, "/robots.txt")
            try:
                rp.set_url(robots_url)
                rp.read()
            except Exception as exc:  # noqa: BLE001
                logger.info("robots.txt unavailable for %s (%s); denying by default", base, exc)
                # Fail closed for unknown robots — policy: allow only if fetch succeeds with allow-all
                # For demo domains (.example) allow
                if parsed.netloc.endswith(".example"):
                    class _Allow:
                        def can_fetch(self, *_a, **_k):
                            return True
                    self._robots_cache[base] = _Allow()  # type: ignore[assignment]
                else:
                    class _Deny:
                        def can_fetch(self, *_a, **_k):
                            return False
                    self._robots_cache[base] = _Deny()  # type: ignore[assignment]
                return self._robots_cache[base].can_fetch(USER_AGENT, url)
            self._robots_cache[base] = rp
        return bool(self._robots_cache[base].can_fetch(USER_AGENT, url))

    def _rate_limit(self, domain: str) -> None:
        if not self.redis:
            time.sleep(0.3)
            return
        key = f"ratelimit:web:{domain}"
        try:
            count = self.redis.incr(key)
            if count == 1:
                self.redis.expire(key, 60)
            if count > 10:
                time.sleep(2.0)
        except Exception:  # noqa: BLE001
            time.sleep(0.3)

    def fetch(self, external_id: str) -> RawRecord:
        """external_id is a URL."""
        url = external_id
        parsed = urlparse(url)
        domain = parsed.netloc
        allowed = self.robots_allowed(url)
        if not allowed:
            return RawRecord(
                source="web",
                external_id=url,
                payload={"url": url, "blocked": True, "reason": "robots_disallow"},
            )
        self._rate_limit(domain)
        try:
            with httpx.Client(
                timeout=20.0,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT},
            ) as client:
                resp = client.get(url)
                if resp.status_code in (401, 403):
                    return RawRecord(
                        source="web",
                        external_id=url,
                        payload={"url": url, "blocked": True, "status": resp.status_code, "reason": "access_control"},
                    )
                resp.raise_for_status()
                html = resp.text[:500_000]
                soup = BeautifulSoup(html, "lxml")
                title = (soup.title.string or "").strip() if soup.title else ""
                text = " ".join(soup.get_text(" ", strip=True).split())[:4000]
                about_hints = []
                for a in soup.find_all("a", href=True):
                    href = a["href"].lower()
                    if any(k in href for k in ("about", "our-story", "team", "contact")):
                        about_hints.append(urljoin(url, a["href"]))
                return RawRecord(
                    source="web",
                    external_id=url,
                    payload={
                        "url": str(resp.url),
                        "status": resp.status_code,
                        "title": title,
                        "text_snippet": text[:1500],
                        "about_links": about_hints[:5],
                        "blocked": False,
                    },
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Web fetch failed for %s: %s", url, exc)
            return RawRecord(
                source="web",
                external_id=url,
                payload={"url": url, "blocked": True, "reason": str(exc)},
            )

    def fetch_if_allowed(self, url: str) -> tuple[RawRecord, bool]:
        """Return (record, robots_allowed)."""
        allowed = self.robots_allowed(url)
        if not allowed:
            return (
                RawRecord(
                    source="web",
                    external_id=url,
                    payload={"url": url, "blocked": True, "reason": "robots_disallow"},
                ),
                False,
            )
        return self.fetch(url), True
