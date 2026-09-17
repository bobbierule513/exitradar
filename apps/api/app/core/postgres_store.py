"""Supabase/Postgres persistence implementing the DemoStore method surface."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from postgrest.exceptions import APIError

from apps.api.app.core.database import get_supabase
from apps.api.app.core.store import StoreOpsMixin

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid() -> str:
    return str(uuid4())


def _normalize(value: Any) -> Any:
    """Coerce PostgREST / Postgres values into JSON-friendly Python types."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    return value


def _row(data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not data:
        return None
    return {k: _normalize(v) for k, v in data.items()}


def _rows(data: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    return [_row(r) or {} for r in (data or [])]


class PostgresStore(StoreOpsMixin):
    """Service-role Supabase client used when DEMO_MODE=false."""

    demo_mode = False

    def __init__(self) -> None:
        client = get_supabase()
        if client is None:
            raise RuntimeError(
                "DEMO_MODE=false requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY"
            )
        self._sb = client

    def _table(self, name: str):
        return self._sb.table(name)

    def _one(self, table: str, **eq: Any) -> Optional[Dict[str, Any]]:
        q = self._table(table).select("*")
        for key, value in eq.items():
            q = q.eq(key, value)
        resp = q.limit(1).execute()
        rows = resp.data or []
        return _row(rows[0]) if rows else None

    def _many(self, table: str, **eq: Any) -> List[Dict[str, Any]]:
        q = self._table(table).select("*")
        for key, value in eq.items():
            q = q.eq(key, value)
        resp = q.execute()
        return _rows(resp.data)

    def _insert(self, table: str, row: Dict[str, Any]) -> Dict[str, Any]:
        resp = self._table(table).insert(row).execute()
        data = resp.data or [row]
        return _row(data[0]) or row

    def _update(self, table: str, match: Dict[str, Any], fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        q = self._table(table).update(fields)
        for key, value in match.items():
            q = q.eq(key, value)
        resp = q.execute()
        rows = resp.data or []
        return _row(rows[0]) if rows else None

    def list_workspaces(self, user_id: str) -> List[Dict[str, Any]]:
        members = self._many("workspace_members", user_id=user_id)
        ids = [m["workspace_id"] for m in members]
        if not ids:
            return []
        resp = self._table("workspaces").select("*").in_("id", ids).execute()
        return _rows(resp.data)

    def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        return self._one("workspaces", id=workspace_id)

    def get_workspace_member(self, workspace_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        return self._one("workspace_members", workspace_id=workspace_id, user_id=user_id)

    def ensure_membership(self, workspace_id: str, user_id: str, role: str = "member") -> None:
        if self.get_workspace_member(workspace_id, user_id):
            return
        try:
            self._insert(
                "workspace_members",
                {"workspace_id": workspace_id, "user_id": user_id, "role": role},
            )
        except APIError as exc:
            logger.info("Membership insert skipped: %s", exc)

    def list_theses(self, workspace_id: str) -> List[Dict[str, Any]]:
        resp = (
            self._table("acquisition_theses")
            .select("*")
            .eq("workspace_id", workspace_id)
            .order("created_at")
            .execute()
        )
        return _rows(resp.data)

    def get_thesis(self, thesis_id: str) -> Optional[Dict[str, Any]]:
        return self._one("acquisition_theses", id=thesis_id)

    def create_thesis(self, workspace_id: str, name: str, criteria: dict, strategy: dict) -> Dict[str, Any]:
        return self._insert(
            "acquisition_theses",
            {
                "id": _uid(),
                "workspace_id": workspace_id,
                "name": name,
                "criteria": criteria or {},
                "strategy": strategy or {},
            },
        )

    def upsert_thesis(
        self,
        thesis_id: str,
        workspace_id: str,
        name: str,
        criteria: dict,
        strategy: dict,
    ) -> Dict[str, Any]:
        existing = self.get_thesis(thesis_id)
        if existing:
            return existing
        return self._insert(
            "acquisition_theses",
            {
                "id": thesis_id,
                "workspace_id": workspace_id,
                "name": name,
                "criteria": criteria or {},
                "strategy": strategy or {},
            },
        )

    def update_thesis(self, thesis_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
        patch = {k: v for k, v in fields.items() if v is not None}
        patch["updated_at"] = _now()
        return self._update("acquisition_theses", {"id": thesis_id}, patch)

    def create_search_job(self, thesis_id: str, query: dict) -> Dict[str, Any]:
        return self._insert(
            "search_jobs",
            {
                "id": _uid(),
                "thesis_id": thesis_id,
                "status": "queued",
                "query": query or {},
                "stats": {},
            },
        )

    def get_search_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._one("search_jobs", id=job_id)

    def update_search_job(self, job_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
        patch = dict(fields)
        patch["updated_at"] = _now()
        return self._update("search_jobs", {"id": job_id}, patch)

    def insert_raw_lead(self, search_job_id: str, source: str, external_id: str, payload: dict) -> Dict[str, Any]:
        existing = self._one(
            "raw_leads",
            search_job_id=search_job_id,
            source=source,
            external_id=external_id,
        )
        if existing:
            return existing
        content = json.dumps(payload, sort_keys=True, default=str)
        return self._insert(
            "raw_leads",
            {
                "id": _uid(),
                "search_job_id": search_job_id,
                "source": source,
                "external_id": external_id,
                "payload": payload,
                "content_hash": hashlib.sha256(content.encode()).hexdigest(),
            },
        )

    def upsert_company(self, data: dict) -> Dict[str, Any]:
        domain = (data.get("domain") or "").lower().strip()
        existing = None
        if domain:
            resp = self._table("companies").select("*").ilike("domain", domain).limit(1).execute()
            rows = resp.data or []
            existing = _row(rows[0]) if rows else None
        if existing is None and data.get("phone_norm"):
            existing = self._one("companies", phone_norm=data["phone_norm"])
        payload = {k: v for k, v in data.items() if v is not None and k != "id"}
        payload["updated_at"] = _now()
        if existing:
            updated = self._update("companies", {"id": existing["id"]}, payload)
            return updated or existing
        payload["id"] = data.get("id") or _uid()
        payload["created_at"] = _now()
        return self._insert("companies", payload)

    def add_company_source(
        self, company_id: str, source: str, external_id: str, confidence: float = 0.8
    ) -> None:
        existing = self._one("company_sources", source=source, external_id=external_id)
        if existing:
            return
        try:
            self._insert(
                "company_sources",
                {
                    "id": _uid(),
                    "company_id": company_id,
                    "source": source,
                    "external_id": external_id,
                    "confidence": confidence,
                },
            )
        except APIError as exc:
            logger.info("company_source insert skipped: %s", exc)

    def list_company_sources(self) -> List[Dict[str, Any]]:
        """All source identity links (resolution pass 1)."""
        resp = self._table("company_sources").select("*").execute()
        return _rows(resp.data)

    def list_companies(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        q = self._table("companies").select("*")
        if workspace_id:
            q = q.eq("workspace_id", workspace_id)
        resp = q.order("canonical_name").execute()
        return _rows(resp.data)

    def get_company(self, company_id: str) -> Optional[Dict[str, Any]]:
        return self._one("companies", id=company_id)

    def list_evidence(self, company_id: str) -> List[Dict[str, Any]]:
        resp = (
            self._table("evidence_items")
            .select("*")
            .eq("company_id", company_id)
            .order("observed_at", desc=True)
            .execute()
        )
        return _rows(resp.data)

    def add_evidence(self, company_id: str, **fields: Any) -> Dict[str, Any]:
        return self._insert(
            "evidence_items",
            {
                "id": _uid(),
                "company_id": company_id,
                "source": fields.get("source", "web"),
                "type": fields.get("type", "snippet"),
                "url": fields.get("url"),
                "snippet": fields.get("snippet"),
                "snapshot_path": fields.get("snapshot_path"),
                "observed_at": fields.get("observed_at", _now()),
                "confidence": fields.get("confidence", 0.7),
                "metadata": fields.get("metadata") or {},
            },
        )

    def list_signals(self, company_id: str) -> List[Dict[str, Any]]:
        return self._many("signals", company_id=company_id)

    def upsert_signal(
        self,
        company_id: str,
        signal_type: str,
        value: Any,
        confidence: float,
        observed_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        existing = self._one("signals", company_id=company_id, signal_type=signal_type)
        stamp = observed_at or _now()
        if existing:
            if existing.get("value") != value:
                self._insert(
                    "signal_events",
                    {
                        "id": _uid(),
                        "company_id": company_id,
                        "signal_id": existing["id"],
                        "signal_type": signal_type,
                        "previous_value": existing.get("value"),
                        "current_value": value,
                        "delta": None,
                        "observed_at": stamp,
                    },
                )
            updated = self._update(
                "signals",
                {"id": existing["id"]},
                {"value": value, "confidence": confidence, "last_observed_at": stamp},
            )
            return updated or existing
        return self._insert(
            "signals",
            {
                "id": _uid(),
                "company_id": company_id,
                "signal_type": signal_type,
                "value": value,
                "confidence": confidence,
                "first_observed_at": stamp,
                "last_observed_at": stamp,
            },
        )

    def list_signal_events(self, company_id: str) -> List[Dict[str, Any]]:
        resp = (
            self._table("signal_events")
            .select("*")
            .eq("company_id", company_id)
            .order("observed_at", desc=True)
            .execute()
        )
        return _rows(resp.data)

    def latest_seller_score(self, company_id: str) -> Optional[Dict[str, Any]]:
        resp = (
            self._table("seller_readiness_scores")
            .select("*")
            .eq("company_id", company_id)
            .order("computed_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return _row(rows[0]) if rows else None

    def add_seller_score(self, row: dict) -> Dict[str, Any]:
        payload = {
            **row,
            "id": row.get("id") or _uid(),
            "computed_at": row.get("computed_at", _now()),
        }
        return self._insert("seller_readiness_scores", payload)

    def list_opportunities(self, thesis_id: str) -> List[Dict[str, Any]]:
        resp = (
            self._table("opportunity_scores")
            .select("*")
            .eq("thesis_id", thesis_id)
            .order("computed_at", desc=True)
            .execute()
        )
        by_company: Dict[str, Dict[str, Any]] = {}
        for s in _rows(resp.data):
            prev = by_company.get(s["company_id"])
            if not prev or str(s.get("computed_at") or "") > str(prev.get("computed_at") or ""):
                by_company[s["company_id"]] = s
        scores = sorted(
            by_company.values(),
            key=lambda x: float(x.get("opportunity_score") or 0),
            reverse=True,
        )
        recs = self.list_recommendations(thesis_id, status="open")
        rec_by_company = {r["company_id"]: r for r in recs}
        result = []
        for s in scores:
            company = self.get_company(s["company_id"]) or {}
            result.append(
                {
                    **s,
                    "company": company,
                    "recommendation": rec_by_company.get(s["company_id"]),
                }
            )
        return result

    def get_opportunity(self, company_id: str, thesis_id: str) -> Optional[Dict[str, Any]]:
        resp = (
            self._table("opportunity_scores")
            .select("*")
            .eq("company_id", company_id)
            .eq("thesis_id", thesis_id)
            .order("computed_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return _row(rows[0]) if rows else None

    def add_opportunity_score(self, row: dict) -> Dict[str, Any]:
        payload = {
            **row,
            "id": row.get("id") or _uid(),
            "computed_at": row.get("computed_at", _now()),
        }
        return self._insert("opportunity_scores", payload)

    def list_recommendations(
        self, thesis_id: Optional[str] = None, status: str = "open"
    ) -> List[Dict[str, Any]]:
        q = self._table("recommendations").select("*")
        if thesis_id:
            q = q.eq("thesis_id", thesis_id)
        if status:
            q = q.eq("status", status)
        resp = q.order("priority", desc=True).execute()
        return _rows(resp.data)

    def upsert_recommendation(self, company_id: str, thesis_id: str, **fields: Any) -> Dict[str, Any]:
        q = (
            self._table("recommendations")
            .select("*")
            .eq("company_id", company_id)
            .eq("thesis_id", thesis_id)
            .eq("status", "open")
            .limit(1)
        )
        rows = q.execute().data or []
        if rows:
            existing = _row(rows[0]) or {}
            updated = self._update("recommendations", {"id": existing["id"]}, fields)
            return updated or existing
        return self._insert(
            "recommendations",
            {
                "id": _uid(),
                "company_id": company_id,
                "thesis_id": thesis_id,
                "action": fields.get("action", "MONITOR"),
                "priority": fields.get("priority", 50),
                "reason": fields.get("reason", ""),
                "status": "open",
                "model_version": fields.get("model_version", "nba-v1"),
                "expires_at": fields.get("expires_at"),
            },
        )

    def get_recommendation(
        self, company_id: str, thesis_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        q = (
            self._table("recommendations")
            .select("*")
            .eq("company_id", company_id)
            .eq("status", "open")
        )
        if thesis_id:
            q = q.eq("thesis_id", thesis_id)
        resp = q.order("priority", desc=True).limit(1).execute()
        rows = resp.data or []
        return _row(rows[0]) if rows else None

    def list_contacts(self, company_id: str) -> List[Dict[str, Any]]:
        return self._many("contacts", company_id=company_id)

    def add_contact(self, company_id: str, **fields: Any) -> Dict[str, Any]:
        return self._insert(
            "contacts",
            {
                "id": _uid(),
                "company_id": company_id,
                "name": fields.get("name"),
                "title": fields.get("title"),
                "email": fields.get("email"),
                "phone": fields.get("phone"),
                "linkedin": fields.get("linkedin"),
                "owner_estimate": fields.get("owner_estimate", False),
                "confidence": fields.get("confidence", 0.5),
            },
        )

    def create_outreach(self, company_id: str, contact_id: Optional[str], **fields: Any) -> Dict[str, Any]:
        return self._insert(
            "outreach_drafts",
            {
                "id": _uid(),
                "company_id": company_id,
                "contact_id": contact_id,
                "channel": fields.get("channel", "email"),
                "subject": fields.get("subject"),
                "body": fields.get("body"),
                "prompt_version": fields.get("prompt_version", "outreach-v1"),
                "evidence_refs": fields.get("evidence_refs") or [],
            },
        )

    def list_outreach(self, company_id: str) -> List[Dict[str, Any]]:
        resp = (
            self._table("outreach_drafts")
            .select("*")
            .eq("company_id", company_id)
            .order("created_at", desc=True)
            .execute()
        )
        return _rows(resp.data)

    def upsert_pipeline(self, company_id: str, thesis_id: str, **fields: Any) -> Dict[str, Any]:
        existing = self._one("deal_pipeline", company_id=company_id, thesis_id=thesis_id)
        patch = {k: v for k, v in fields.items() if v is not None}
        patch["updated_at"] = _now()
        if existing:
            updated = self._update("deal_pipeline", {"id": existing["id"]}, patch)
            return updated or existing
        return self._insert(
            "deal_pipeline",
            {
                "id": _uid(),
                "company_id": company_id,
                "thesis_id": thesis_id,
                "stage": fields.get("stage", "identified"),
                "probability": fields.get("probability", 0.1),
                "notes": fields.get("notes", ""),
            },
        )

    def get_pipeline(self, company_id: str, thesis_id: str) -> Optional[Dict[str, Any]]:
        return self._one("deal_pipeline", company_id=company_id, thesis_id=thesis_id)

    def add_activity(self, **fields: Any) -> Dict[str, Any]:
        return self._insert(
            "activities",
            {
                "id": _uid(),
                "company_id": fields.get("company_id"),
                "recommendation_id": fields.get("recommendation_id"),
                "activity_type": fields.get("activity_type"),
                "outcome": fields.get("outcome"),
                "metadata": fields.get("metadata") or {},
                "occurred_at": fields.get("occurred_at", _now()),
            },
        )

    def list_activities(self, company_id: str) -> List[Dict[str, Any]]:
        resp = (
            self._table("activities")
            .select("*")
            .eq("company_id", company_id)
            .order("occurred_at", desc=True)
            .execute()
        )
        return _rows(resp.data)

    def create_export(self, workspace_id: str, filters: dict, rows: List[dict]) -> Dict[str, Any]:
        eid = _uid()
        row = self._insert(
            "exports",
            {
                "id": eid,
                "workspace_id": workspace_id,
                "file_path": f"exports/{eid}.json",
                "filters": filters,
                "row_count": len(rows),
                "payload": rows,
            },
        )
        return {k: v for k, v in row.items() if k != "payload"}

    def get_export(self, export_id: str) -> Optional[Dict[str, Any]]:
        row = self._one("exports", id=export_id)
        if not row:
            return None
        row["rows"] = row.pop("payload", None) or []
        return row

    def log_compliance(self, **fields: Any) -> None:
        self._insert(
            "compliance_log",
            {
                "id": _uid(),
                "company_id": fields.get("company_id"),
                "action": fields.get("action"),
                "source": fields.get("source"),
                "detail": fields.get("detail"),
                "robots_allowed": fields.get("robots_allowed"),
                "policy_allowed": fields.get("policy_allowed", True),
            },
        )

    def update_workspace_settings(
        self, workspace_id: str, settings: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        ws = self.get_workspace(workspace_id)
        if not ws:
            return None
        current = dict(ws.get("settings") or {})
        for key, value in settings.items():
            if isinstance(value, dict) and isinstance(current.get(key), dict):
                merged = dict(current[key])
                merged.update(value)
                current[key] = merged
            else:
                current[key] = value
        return self._update("workspaces", {"id": workspace_id}, {"settings": current})

    def add_company_relationship(
        self,
        company_id: str,
        related_company_id: str,
        relationship_type: str,
        confidence: float = 0.5,
    ) -> Dict[str, Any]:
        for a, b in ((company_id, related_company_id), (related_company_id, company_id)):
            existing = self._one(
                "company_relationships",
                company_id=a,
                related_company_id=b,
                relationship_type=relationship_type,
            )
            if existing:
                updated = self._update(
                    "company_relationships", {"id": existing["id"]}, {"confidence": confidence}
                )
                return updated or existing
        return self._insert(
            "company_relationships",
            {
                "id": _uid(),
                "company_id": company_id,
                "related_company_id": related_company_id,
                "relationship_type": relationship_type,
                "confidence": confidence,
            },
        )

    def update_recommendation(self, recommendation_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
        patch = {k: v for k, v in fields.items() if v is not None}
        return self._update("recommendations", {"id": recommendation_id}, patch)

    def get_book_plan(self, thesis_id: str, iso_week: str) -> Optional[Dict[str, Any]]:
        resp = (
            self._table("book_of_work_plans")
            .select("*")
            .eq("thesis_id", thesis_id)
            .eq("iso_week", iso_week)
            .eq("status", "active")
            .order("generated_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return None
        plan = _row(rows[0]) or {}
        plan["slots"] = self._slots_for_plan(plan["id"])
        return plan

    def get_book_plan_by_id(self, plan_id: str) -> Optional[Dict[str, Any]]:
        plan = self._one("book_of_work_plans", id=plan_id)
        if not plan:
            return None
        plan["slots"] = self._slots_for_plan(plan_id)
        return plan

    def _slots_for_plan(self, plan_id: str) -> List[Dict[str, Any]]:
        resp = self._table("book_of_work_slots").select("*").eq("plan_id", plan_id).execute()
        slots = _rows(resp.data)
        slots.sort(key=lambda s: (s.get("kind", ""), s.get("rank") or 0))
        return slots

    def get_book_slot(self, slot_id: str) -> Optional[Dict[str, Any]]:
        return self._one("book_of_work_slots", id=slot_id)

    def update_book_slot(self, slot_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
        patch = {k: v for k, v in fields.items() if v is not None}
        return self._update("book_of_work_slots", {"id": slot_id}, patch)

    def supersede_book_plans(self, thesis_id: str, iso_week: str) -> None:
        self._table("book_of_work_plans").update({"status": "superseded"}).eq(
            "thesis_id", thesis_id
        ).eq("iso_week", iso_week).eq("status", "active").execute()

    def save_book_plan(
        self,
        thesis_id: str,
        workspace_id: str,
        draft: Dict[str, Any],
        brief: Optional[str] = None,
    ) -> Dict[str, Any]:
        plan = self._insert(
            "book_of_work_plans",
            {
                "id": _uid(),
                "thesis_id": thesis_id,
                "workspace_id": workspace_id,
                "iso_week": draft["iso_week"],
                "model_version": draft.get("model_version", "bow-v1"),
                "cadence": draft.get("cadence") or {},
                "stats": draft.get("stats") or {},
                "brief": brief,
                "status": "active",
                "generated_at": draft.get("generated_at", _now()),
            },
        )
        saved_slots = []
        for raw in draft.get("slots") or []:
            slot = self._insert(
                "book_of_work_slots",
                {
                    "id": raw.get("id") or _uid(),
                    "plan_id": plan["id"],
                    "kind": raw["kind"],
                    "rank": raw.get("rank") or 0,
                    "company_id": raw["company_id"],
                    "recommendation_id": raw.get("recommendation_id"),
                    "cluster_id": raw.get("cluster_id"),
                    "window_closes_at": raw.get("window_closes_at"),
                    "reason": raw.get("reason"),
                    "expected_lift": raw.get("expected_lift"),
                    "research_field": raw.get("research_field"),
                    "lift_per_hour": raw.get("lift_per_hour"),
                    "chosen_sibling_id": raw.get("chosen_sibling_id"),
                    "action": raw.get("action"),
                    "opportunity_score": raw.get("opportunity_score"),
                    "status": raw.get("status") or "open",
                },
            )
            saved_slots.append(slot)
        out = dict(plan)
        out["slots"] = saved_slots
        return out

    def merge_companies_into_book_plan(
        self,
        plan_id: str,
        new_slots: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        plan = self.get_book_plan_by_id(plan_id)
        if not plan:
            raise ValueError("Plan not found")
        existing = {s["company_id"] for s in plan.get("slots") or []}
        for raw in new_slots:
            if raw["company_id"] in existing:
                continue
            if raw.get("kind") not in ("hold", "research", "stale"):
                raw = {
                    **raw,
                    "kind": "hold",
                    "reason": raw.get("reason") or "Merged after discovery.",
                }
            self._insert(
                "book_of_work_slots",
                {
                    "id": _uid(),
                    "plan_id": plan_id,
                    "kind": raw["kind"],
                    "rank": raw.get("rank") or 0,
                    "company_id": raw["company_id"],
                    "recommendation_id": raw.get("recommendation_id"),
                    "cluster_id": raw.get("cluster_id"),
                    "window_closes_at": raw.get("window_closes_at"),
                    "reason": raw.get("reason"),
                    "expected_lift": raw.get("expected_lift"),
                    "research_field": raw.get("research_field"),
                    "lift_per_hour": raw.get("lift_per_hour"),
                    "chosen_sibling_id": raw.get("chosen_sibling_id"),
                    "action": raw.get("action"),
                    "opportunity_score": raw.get("opportunity_score"),
                    "status": "open",
                },
            )
            existing.add(raw["company_id"])
        refreshed = self.get_book_plan_by_id(plan_id)
        if not refreshed:
            raise ValueError("Plan not found")
        return refreshed

    def list_relationships(self, company_id: str) -> List[Dict[str, Any]]:
        a = self._many("company_relationships", company_id=company_id)
        b = self._many("company_relationships", related_company_id=company_id)
        seen = {r["id"] for r in a}
        out = list(a)
        for r in b:
            if r["id"] not in seen:
                out.append(r)
        return out

    def upsert_user(self, user_id: str, email: str) -> Dict[str, Any]:
        existing = self._one("users", id=user_id)
        if existing:
            return existing
        try:
            return self._insert("users", {"id": user_id, "email": email})
        except APIError:
            by_email = self._one("users", email=email)
            return by_email or {"id": user_id, "email": email}

    def upsert_workspace(
        self,
        workspace_id: str,
        owner_id: str,
        name: str,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        existing = self.get_workspace(workspace_id)
        if existing:
            return existing
        return self._insert(
            "workspaces",
            {
                "id": workspace_id,
                "owner_id": owner_id,
                "name": name,
                "plan": "pro",
                "settings": settings or {},
            },
        )
