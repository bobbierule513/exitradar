"""Repository factory: DemoStore for local demos, PostgresStore for production."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Protocol, runtime_checkable

from apps.api.app.core.config import get_settings

logger = logging.getLogger(__name__)


@runtime_checkable
class Store(Protocol):
    """Persistence surface used by API routes and workers."""

    demo_mode: bool


class StoreOpsMixin:
    """Methods that only call other store accessors (shared by memory + Postgres)."""

    demo_mode: bool = False

    def get_cadence(self, workspace_id: str, thesis_id: Optional[str] = None) -> Dict[str, int]:
        """Resolved cadence for workspace (+ optional thesis strategy override)."""
        from workers.intelligence.book_of_work import resolve_cadence

        ws = self.get_workspace(workspace_id) or {}  # type: ignore[attr-defined]
        strategy = None
        if thesis_id:
            thesis = self.get_thesis(thesis_id)  # type: ignore[attr-defined]
            strategy = (thesis or {}).get("strategy")
        return resolve_cadence(ws.get("settings"), strategy)

    def company_book_slot(
        self, company_id: str, thesis_id: str, iso_week: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Current-week slot for a company if any."""
        from workers.intelligence.book_of_work import iso_week_label

        week = iso_week or iso_week_label()
        plan = self.get_book_plan(thesis_id, week)  # type: ignore[attr-defined]
        if not plan:
            return None
        for s in plan.get("slots") or []:
            if s.get("company_id") == company_id:
                return s
        return None

    def command_center(self, workspace_id: str, thesis_id: Optional[str] = None) -> Dict[str, Any]:
        """Acquisition command center aggregates including Book of Work."""
        from workers.intelligence.book_of_work import iso_week_label
        from workers.intelligence.book_service import ensure_book_of_work

        theses = self.list_theses(workspace_id)  # type: ignore[attr-defined]
        tid = thesis_id or (theses[0]["id"] if theses else None)
        opps = self.list_opportunities(tid) if tid else []  # type: ignore[attr-defined]
        ready = [o for o in opps if (o.get("recommendation") or {}).get("action") == "CONTACT_NOW"]
        warming = [
            o
            for o in opps
            if (o.get("recommendation") or {}).get("action") in ("RELATIONSHIP_FIRST", "MONITOR")
        ]

        book = None
        if tid:
            book = ensure_book_of_work(self, tid, force=False, with_brief=False)

        slots = (book or {}).get("slots") or []
        outreach_open = [s for s in slots if s.get("kind") == "outreach" and s.get("status") == "open"]
        research_open = [s for s in slots if s.get("kind") == "research" and s.get("status") == "open"]
        stale = [s for s in slots if s.get("kind") == "stale"]
        closing_soon = 0
        now = datetime.now(timezone.utc)
        for s in outreach_open:
            exp = s.get("window_closes_at")
            if not exp:
                continue
            try:
                dt = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if 0 <= (dt - now).total_seconds() / 86400 <= 7:
                    closing_soon += 1
            except ValueError:
                pass

        return {
            "opportunity_count": len(opps),
            "newly_actionable": len(ready),
            "warming_targets": len(warming),
            "top_opportunities": opps[:5],
            "open_recommendations": self.list_recommendations(tid)[:10] if tid else [],  # type: ignore[attr-defined]
            "thesis_id": tid,
            "book_of_work": book,
            "book_metrics": {
                "outreach_remaining": len(outreach_open),
                "research_remaining": len(research_open),
                "stale_count": len(stale),
                "windows_closing_7d": closing_soon,
                "iso_week": (book or {}).get("iso_week") or iso_week_label(),
            },
        }


_store: Any = None


def reset_store() -> None:
    """Clear the process-wide store singleton (tests)."""
    global _store
    _store = None


def get_store() -> Any:
    """Return DemoStore when DEMO_MODE=true, otherwise PostgresStore.

    Production (DEMO_MODE=false) requires Supabase service-role credentials.
    """
    global _store
    if _store is not None:
        return _store

    settings = get_settings()
    if settings.demo_mode:
        from apps.api.app.core.demo_store import DemoStore

        logger.info("Using in-memory DemoStore (DEMO_MODE=true)")
        _store = DemoStore(demo_mode=True)
        return _store

    from apps.api.app.core.postgres_store import PostgresStore

    logger.info("Using PostgresStore (DEMO_MODE=false)")
    _store = PostgresStore()
    return _store


def get_demo_store() -> Any:
    """Backward-compatible FastAPI dependency alias for get_store()."""
    return get_store()
