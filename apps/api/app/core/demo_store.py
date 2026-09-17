"""In-memory demo store used when Supabase is not configured.

Mirrors the ERD so the full product loop works locally for demos and tests.
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from apps.api.app.core.seed_data import (
    DEMO_THESIS,
    DEMO_THESIS_ID,
    DEMO_USER_ID,
    DEMO_WORKSPACE_ID,
    apply_hvac_seed,
)
from apps.api.app.core.store import StoreOpsMixin

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid() -> str:
    return str(uuid4())


class DemoStore(StoreOpsMixin):
    """Thread-safe in-memory persistence for ExitRadar entities."""

    def __init__(self, demo_mode: bool = True) -> None:
        self.demo_mode = demo_mode
        self._lock = threading.RLock()
        self.users: Dict[str, Dict[str, Any]] = {}
        self.workspaces: Dict[str, Dict[str, Any]] = {}
        self.workspace_members: List[Dict[str, Any]] = []
        self.acquisition_theses: Dict[str, Dict[str, Any]] = {}
        self.search_jobs: Dict[str, Dict[str, Any]] = {}
        self.raw_leads: Dict[str, Dict[str, Any]] = {}
        self.companies: Dict[str, Dict[str, Any]] = {}
        self.company_sources: List[Dict[str, Any]] = []
        self.contacts: Dict[str, Dict[str, Any]] = {}
        self.evidence_items: Dict[str, Dict[str, Any]] = {}
        self.signals: Dict[str, Dict[str, Any]] = {}
        self.signal_events: List[Dict[str, Any]] = []
        self.signal_evidence: List[Dict[str, Any]] = []
        self.seller_readiness_scores: List[Dict[str, Any]] = []
        self.opportunity_scores: List[Dict[str, Any]] = []
        self.score_evidence: List[Dict[str, Any]] = []
        self.recommendations: Dict[str, Dict[str, Any]] = {}
        self.outreach_drafts: Dict[str, Dict[str, Any]] = {}
        self.deal_pipeline: Dict[str, Dict[str, Any]] = {}
        self.activities: List[Dict[str, Any]] = []
        self.exports: Dict[str, Dict[str, Any]] = {}
        self.compliance_log: List[Dict[str, Any]] = []
        self.company_relationships: List[Dict[str, Any]] = []
        self.transactions: List[Dict[str, Any]] = []
        self.book_of_work_plans: Dict[str, Dict[str, Any]] = {}
        self.book_of_work_slots: Dict[str, Dict[str, Any]] = {}
        self._seed()

    def _seed(self) -> None:
        """Bootstrap a demo user, workspace, and HVAC thesis."""
        user_id = DEMO_USER_ID
        ws_id = DEMO_WORKSPACE_ID
        thesis_id = DEMO_THESIS_ID
        self.users[user_id] = {
            "id": user_id,
            "email": "demo@exitradar.local",
            "created_at": _now(),
        }
        self.workspaces[ws_id] = {
            "id": ws_id,
            "owner_id": user_id,
            "name": "Caprae Demo Workspace",
            "plan": "pro",
            "settings": {
                "cadence": {
                    "max_outreach_per_week": 5,
                    "max_research_slots": 4,
                }
            },
            "created_at": _now(),
        }
        self.workspace_members.append(
            {"workspace_id": ws_id, "user_id": user_id, "role": "owner"}
        )
        self.acquisition_theses[thesis_id] = {
            "id": thesis_id,
            "workspace_id": ws_id,
            "name": DEMO_THESIS["name"],
            "criteria": DEMO_THESIS["criteria"],
            "strategy": DEMO_THESIS["strategy"],
            "created_at": _now(),
            "updated_at": _now(),
        }
        apply_hvac_seed(self, ws_id, thesis_id)

    def list_workspaces(self, user_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            member_ws = {m["workspace_id"] for m in self.workspace_members if m["user_id"] == user_id}
            return [copy.deepcopy(self.workspaces[w]) for w in member_ws if w in self.workspaces]

    def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            ws = self.workspaces.get(workspace_id)
            return copy.deepcopy(ws) if ws else None

    def get_workspace_member(self, workspace_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for m in self.workspace_members:
                if m["workspace_id"] == workspace_id and m["user_id"] == user_id:
                    return copy.deepcopy(m)
            return None

    def ensure_membership(self, workspace_id: str, user_id: str, role: str = "member") -> None:
        with self._lock:
            if self.get_workspace_member(workspace_id, user_id):
                return
            self.workspace_members.append(
                {"workspace_id": workspace_id, "user_id": user_id, "role": role}
            )

    def list_theses(self, workspace_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                copy.deepcopy(t)
                for t in self.acquisition_theses.values()
                if t["workspace_id"] == workspace_id
            ]

    def get_thesis(self, thesis_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            t = self.acquisition_theses.get(thesis_id)
            return copy.deepcopy(t) if t else None

    def create_thesis(self, workspace_id: str, name: str, criteria: dict, strategy: dict) -> Dict[str, Any]:
        with self._lock:
            tid = _uid()
            row = {
                "id": tid,
                "workspace_id": workspace_id,
                "name": name,
                "criteria": criteria,
                "strategy": strategy,
                "created_at": _now(),
                "updated_at": _now(),
            }
            self.acquisition_theses[tid] = row
            return copy.deepcopy(row)

    def update_thesis(self, thesis_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
        with self._lock:
            t = self.acquisition_theses.get(thesis_id)
            if not t:
                return None
            t.update({k: v for k, v in fields.items() if v is not None})
            t["updated_at"] = _now()
            return copy.deepcopy(t)

    def create_search_job(self, thesis_id: str, query: dict) -> Dict[str, Any]:
        with self._lock:
            jid = _uid()
            row = {
                "id": jid,
                "thesis_id": thesis_id,
                "status": "queued",
                "query": query,
                "stats": {},
                "created_at": _now(),
                "updated_at": _now(),
            }
            self.search_jobs[jid] = row
            return copy.deepcopy(row)

    def get_search_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            j = self.search_jobs.get(job_id)
            return copy.deepcopy(j) if j else None

    def update_search_job(self, job_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
        with self._lock:
            j = self.search_jobs.get(job_id)
            if not j:
                return None
            j.update(fields)
            j["updated_at"] = _now()
            return copy.deepcopy(j)

    def insert_raw_lead(self, search_job_id: str, source: str, external_id: str, payload: dict) -> Dict[str, Any]:
        with self._lock:
            content = json.dumps(payload, sort_keys=True, default=str)
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            # Dedup by hash within job
            for existing in self.raw_leads.values():
                if (
                    existing["search_job_id"] == search_job_id
                    and existing["source"] == source
                    and existing.get("external_id") == external_id
                ):
                    return copy.deepcopy(existing)
            rid = _uid()
            row = {
                "id": rid,
                "search_job_id": search_job_id,
                "source": source,
                "external_id": external_id,
                "payload": payload,
                "content_hash": content_hash,
                "created_at": _now(),
            }
            self.raw_leads[rid] = row
            return copy.deepcopy(row)

    def upsert_company(self, data: dict) -> Dict[str, Any]:
        with self._lock:
            domain = (data.get("domain") or "").lower().strip()
            if domain:
                for c in self.companies.values():
                    if (c.get("domain") or "").lower() == domain:
                        c.update({k: v for k, v in data.items() if v is not None and k != "id"})
                        c["updated_at"] = _now()
                        return copy.deepcopy(c)
            phone = data.get("phone_norm")
            if phone:
                for c in self.companies.values():
                    if c.get("phone_norm") == phone:
                        c.update({k: v for k, v in data.items() if v is not None and k != "id"})
                        c["updated_at"] = _now()
                        return copy.deepcopy(c)
            cid = data.get("id") or _uid()
            row = {**data, "id": cid, "created_at": _now(), "updated_at": _now()}
            self.companies[cid] = row
            return copy.deepcopy(row)

    def add_company_source(self, company_id: str, source: str, external_id: str, confidence: float = 0.8) -> None:
        with self._lock:
            for s in self.company_sources:
                if s["company_id"] == company_id and s["source"] == source and s["external_id"] == external_id:
                    return
            self.company_sources.append(
                {
                    "id": _uid(),
                    "company_id": company_id,
                    "source": source,
                    "external_id": external_id,
                    "confidence": confidence,
                    "raw_ref": None,
                }
            )

    def list_company_sources(self) -> List[Dict[str, Any]]:
        """All source identity links (resolution pass 1)."""
        with self._lock:
            return [copy.deepcopy(s) for s in self.company_sources]

    def list_companies(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            rows = list(self.companies.values())
            if workspace_id:
                rows = [c for c in rows if c.get("workspace_id") == workspace_id]
            return [copy.deepcopy(c) for c in rows]

    def get_company(self, company_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            c = self.companies.get(company_id)
            return copy.deepcopy(c) if c else None

    def list_evidence(self, company_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [copy.deepcopy(e) for e in self.evidence_items.values() if e["company_id"] == company_id]

    def add_evidence(self, company_id: str, **fields: Any) -> Dict[str, Any]:
        with self._lock:
            eid = _uid()
            row = {
                "id": eid,
                "company_id": company_id,
                "source": fields.get("source", "web"),
                "type": fields.get("type", "snippet"),
                "url": fields.get("url"),
                "snippet": fields.get("snippet"),
                "snapshot_path": fields.get("snapshot_path"),
                "observed_at": fields.get("observed_at", _now()),
                "confidence": fields.get("confidence", 0.7),
                "metadata": fields.get("metadata", {}),
            }
            self.evidence_items[eid] = row
            return copy.deepcopy(row)

    def list_signals(self, company_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [copy.deepcopy(s) for s in self.signals.values() if s["company_id"] == company_id]

    def upsert_signal(
        self,
        company_id: str,
        signal_type: str,
        value: Any,
        confidence: float,
        observed_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            stamp = observed_at or _now()
            existing = None
            for s in self.signals.values():
                if s["company_id"] == company_id and s["signal_type"] == signal_type:
                    existing = s
                    break
            if existing:
                prev = existing.get("value")
                if prev != value:
                    self.signal_events.append(
                        {
                            "id": _uid(),
                            "company_id": company_id,
                            "signal_id": existing["id"],
                            "signal_type": signal_type,
                            "previous_value": prev,
                            "current_value": value,
                            "delta": None,
                            "observed_at": stamp,
                        }
                    )
                existing["value"] = value
                existing["confidence"] = confidence
                existing["last_observed_at"] = stamp
                return copy.deepcopy(existing)
            sid = _uid()
            row = {
                "id": sid,
                "company_id": company_id,
                "signal_type": signal_type,
                "value": value,
                "confidence": confidence,
                "first_observed_at": stamp,
                "last_observed_at": stamp,
            }
            self.signals[sid] = row
            return copy.deepcopy(row)

    def list_signal_events(self, company_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [copy.deepcopy(e) for e in self.signal_events if e["company_id"] == company_id]

    def latest_seller_score(self, company_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            rows = [s for s in self.seller_readiness_scores if s["company_id"] == company_id]
            if not rows:
                return None
            rows.sort(key=lambda r: r["computed_at"], reverse=True)
            return copy.deepcopy(rows[0])

    def add_seller_score(self, row: dict) -> Dict[str, Any]:
        with self._lock:
            row = {**row, "id": row.get("id") or _uid(), "computed_at": row.get("computed_at", _now())}
            self.seller_readiness_scores.append(row)
            return copy.deepcopy(row)

    def list_opportunities(self, thesis_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            # Latest score per company for thesis
            by_company: Dict[str, Dict[str, Any]] = {}
            for s in self.opportunity_scores:
                if s["thesis_id"] != thesis_id:
                    continue
                prev = by_company.get(s["company_id"])
                if not prev or s["computed_at"] > prev["computed_at"]:
                    by_company[s["company_id"]] = s
            scores = sorted(by_company.values(), key=lambda x: x["opportunity_score"], reverse=True)
            result = []
            for s in scores:
                company = self.companies.get(s["company_id"], {})
                rec = next(
                    (
                        r
                        for r in self.recommendations.values()
                        if r["company_id"] == s["company_id"]
                        and r["thesis_id"] == thesis_id
                        and r["status"] == "open"
                    ),
                    None,
                )
                result.append(
                    {
                        **copy.deepcopy(s),
                        "company": copy.deepcopy(company),
                        "recommendation": copy.deepcopy(rec) if rec else None,
                    }
                )
            return result

    def get_opportunity(self, company_id: str, thesis_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            rows = [
                s
                for s in self.opportunity_scores
                if s["company_id"] == company_id and s["thesis_id"] == thesis_id
            ]
            if not rows:
                return None
            rows.sort(key=lambda r: r["computed_at"], reverse=True)
            return copy.deepcopy(rows[0])

    def add_opportunity_score(self, row: dict) -> Dict[str, Any]:
        with self._lock:
            row = {**row, "id": row.get("id") or _uid(), "computed_at": row.get("computed_at", _now())}
            self.opportunity_scores.append(row)
            return copy.deepcopy(row)

    def list_recommendations(self, thesis_id: Optional[str] = None, status: str = "open") -> List[Dict[str, Any]]:
        with self._lock:
            rows = list(self.recommendations.values())
            if thesis_id:
                rows = [r for r in rows if r["thesis_id"] == thesis_id]
            if status:
                rows = [r for r in rows if r["status"] == status]
            rows.sort(key=lambda r: r.get("priority", 0), reverse=True)
            return [copy.deepcopy(r) for r in rows]

    def upsert_recommendation(self, company_id: str, thesis_id: str, **fields: Any) -> Dict[str, Any]:
        with self._lock:
            for r in self.recommendations.values():
                if r["company_id"] == company_id and r["thesis_id"] == thesis_id and r["status"] == "open":
                    r.update(fields)
                    return copy.deepcopy(r)
            rid = _uid()
            row = {
                "id": rid,
                "company_id": company_id,
                "thesis_id": thesis_id,
                "action": fields.get("action", "MONITOR"),
                "priority": fields.get("priority", 50),
                "reason": fields.get("reason", ""),
                "status": "open",
                "model_version": fields.get("model_version", "nba-v1"),
                "expires_at": fields.get("expires_at"),
                "created_at": _now(),
            }
            self.recommendations[rid] = row
            return copy.deepcopy(row)

    def get_recommendation(self, company_id: str, thesis_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        with self._lock:
            rows = [
                r
                for r in self.recommendations.values()
                if r["company_id"] == company_id and r["status"] == "open"
            ]
            if thesis_id:
                rows = [r for r in rows if r["thesis_id"] == thesis_id]
            if not rows:
                return None
            rows.sort(key=lambda r: r.get("priority", 0), reverse=True)
            return copy.deepcopy(rows[0])

    def list_contacts(self, company_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [copy.deepcopy(c) for c in self.contacts.values() if c["company_id"] == company_id]

    def add_contact(self, company_id: str, **fields: Any) -> Dict[str, Any]:
        with self._lock:
            cid = _uid()
            row = {
                "id": cid,
                "company_id": company_id,
                "name": fields.get("name"),
                "title": fields.get("title"),
                "email": fields.get("email"),
                "phone": fields.get("phone"),
                "linkedin": fields.get("linkedin"),
                "owner_estimate": fields.get("owner_estimate", False),
                "confidence": fields.get("confidence", 0.5),
            }
            self.contacts[cid] = row
            return copy.deepcopy(row)

    def create_outreach(self, company_id: str, contact_id: Optional[str], **fields: Any) -> Dict[str, Any]:
        with self._lock:
            oid = _uid()
            row = {
                "id": oid,
                "company_id": company_id,
                "contact_id": contact_id,
                "channel": fields.get("channel", "email"),
                "subject": fields.get("subject"),
                "body": fields.get("body"),
                "prompt_version": fields.get("prompt_version", "outreach-v1"),
                "evidence_refs": fields.get("evidence_refs", []),
                "created_at": _now(),
            }
            self.outreach_drafts[oid] = row
            return copy.deepcopy(row)

    def list_outreach(self, company_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                copy.deepcopy(o)
                for o in self.outreach_drafts.values()
                if o["company_id"] == company_id
            ]

    def upsert_pipeline(self, company_id: str, thesis_id: str, **fields: Any) -> Dict[str, Any]:
        with self._lock:
            for p in self.deal_pipeline.values():
                if p["company_id"] == company_id and p["thesis_id"] == thesis_id:
                    p.update({k: v for k, v in fields.items() if v is not None})
                    p["updated_at"] = _now()
                    return copy.deepcopy(p)
            pid = _uid()
            row = {
                "id": pid,
                "company_id": company_id,
                "thesis_id": thesis_id,
                "stage": fields.get("stage", "identified"),
                "probability": fields.get("probability", 0.1),
                "notes": fields.get("notes", ""),
                "updated_at": _now(),
            }
            self.deal_pipeline[pid] = row
            return copy.deepcopy(row)

    def get_pipeline(self, company_id: str, thesis_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for p in self.deal_pipeline.values():
                if p["company_id"] == company_id and p["thesis_id"] == thesis_id:
                    return copy.deepcopy(p)
            return None

    def add_activity(self, **fields: Any) -> Dict[str, Any]:
        with self._lock:
            row = {
                "id": _uid(),
                "company_id": fields.get("company_id"),
                "recommendation_id": fields.get("recommendation_id"),
                "activity_type": fields.get("activity_type"),
                "outcome": fields.get("outcome"),
                "metadata": fields.get("metadata", {}),
                "occurred_at": fields.get("occurred_at", _now()),
            }
            self.activities.append(row)
            return copy.deepcopy(row)

    def list_activities(self, company_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            rows = [a for a in self.activities if a.get("company_id") == company_id]
            rows.sort(key=lambda a: a.get("occurred_at", ""), reverse=True)
            return [copy.deepcopy(a) for a in rows]

    def create_export(self, workspace_id: str, filters: dict, rows: List[dict]) -> Dict[str, Any]:
        with self._lock:
            eid = _uid()
            row = {
                "id": eid,
                "workspace_id": workspace_id,
                "file_path": f"exports/{eid}.json",
                "filters": filters,
                "row_count": len(rows),
                "rows": rows,
                "created_at": _now(),
            }
            self.exports[eid] = row
            return copy.deepcopy({k: v for k, v in row.items() if k != "rows"})

    def get_export(self, export_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            e = self.exports.get(export_id)
            return copy.deepcopy(e) if e else None

    def log_compliance(self, **fields: Any) -> None:
        with self._lock:
            self.compliance_log.append(
                {
                    "id": _uid(),
                    "company_id": fields.get("company_id"),
                    "action": fields.get("action"),
                    "source": fields.get("source"),
                    "detail": fields.get("detail"),
                    "robots_allowed": fields.get("robots_allowed"),
                    "policy_allowed": fields.get("policy_allowed", True),
                    "created_at": _now(),
                }
            )

    def update_workspace_settings(self, workspace_id: str, settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Merge workspace settings (e.g. cadence) and return workspace."""
        with self._lock:
            ws = self.workspaces.get(workspace_id)
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
            ws["settings"] = current
            return copy.deepcopy(ws)

    def add_company_relationship(
        self,
        company_id: str,
        related_company_id: str,
        relationship_type: str,
        confidence: float = 0.5,
    ) -> Dict[str, Any]:
        """Upsert a company relationship edge."""
        with self._lock:
            for r in self.company_relationships:
                if (
                    r["company_id"] == company_id
                    and r["related_company_id"] == related_company_id
                    and r["relationship_type"] == relationship_type
                ):
                    r["confidence"] = confidence
                    return copy.deepcopy(r)
                if (
                    r["company_id"] == related_company_id
                    and r["related_company_id"] == company_id
                    and r["relationship_type"] == relationship_type
                ):
                    r["confidence"] = confidence
                    return copy.deepcopy(r)
            row = {
                "id": _uid(),
                "company_id": company_id,
                "related_company_id": related_company_id,
                "relationship_type": relationship_type,
                "confidence": confidence,
            }
            self.company_relationships.append(row)
            return copy.deepcopy(row)

    def update_recommendation(self, recommendation_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
        """Patch a recommendation by id."""
        with self._lock:
            r = self.recommendations.get(recommendation_id)
            if not r:
                return None
            r.update({k: v for k, v in fields.items() if v is not None})
            return copy.deepcopy(r)

    def get_book_plan(self, thesis_id: str, iso_week: str) -> Optional[Dict[str, Any]]:
        """Latest active plan for thesis/week with slots."""
        with self._lock:
            plans = [
                p
                for p in self.book_of_work_plans.values()
                if p["thesis_id"] == thesis_id
                and p["iso_week"] == iso_week
                and p.get("status") == "active"
            ]
            if not plans:
                return None
            plans.sort(key=lambda p: p.get("generated_at", ""), reverse=True)
            plan = copy.deepcopy(plans[0])
            slots = [
                copy.deepcopy(s)
                for s in self.book_of_work_slots.values()
                if s["plan_id"] == plan["id"]
            ]
            slots.sort(key=lambda s: (s.get("kind", ""), s.get("rank") or 0))
            plan["slots"] = slots
            return plan

    def get_book_plan_by_id(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Fetch plan by id with slots."""
        with self._lock:
            plan = self.book_of_work_plans.get(plan_id)
            if not plan:
                return None
            out = copy.deepcopy(plan)
            slots = [
                copy.deepcopy(s)
                for s in self.book_of_work_slots.values()
                if s["plan_id"] == plan_id
            ]
            slots.sort(key=lambda s: (s.get("kind", ""), s.get("rank") or 0))
            out["slots"] = slots
            return out

    def get_book_slot(self, slot_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single book-of-work slot."""
        with self._lock:
            s = self.book_of_work_slots.get(slot_id)
            return copy.deepcopy(s) if s else None

    def update_book_slot(self, slot_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
        """Patch a book-of-work slot."""
        with self._lock:
            s = self.book_of_work_slots.get(slot_id)
            if not s:
                return None
            s.update({k: v for k, v in fields.items() if v is not None})
            return copy.deepcopy(s)

    def supersede_book_plans(self, thesis_id: str, iso_week: str) -> None:
        """Mark prior active plans for week as superseded."""
        with self._lock:
            for p in self.book_of_work_plans.values():
                if p["thesis_id"] == thesis_id and p["iso_week"] == iso_week and p.get("status") == "active":
                    p["status"] = "superseded"

    def save_book_plan(
        self,
        thesis_id: str,
        workspace_id: str,
        draft: Dict[str, Any],
        brief: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Persist a generated week plan and its slots."""
        with self._lock:
            plan_id = _uid()
            plan = {
                "id": plan_id,
                "thesis_id": thesis_id,
                "workspace_id": workspace_id,
                "iso_week": draft["iso_week"],
                "model_version": draft.get("model_version", "bow-v1"),
                "cadence": draft.get("cadence") or {},
                "stats": draft.get("stats") or {},
                "brief": brief,
                "status": "active",
                "generated_at": draft.get("generated_at", _now()),
            }
            self.book_of_work_plans[plan_id] = plan
            saved_slots = []
            for raw in draft.get("slots") or []:
                sid = raw.get("id") or _uid()
                slot = {
                    "id": sid,
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
                    "status": raw.get("status") or "open",
                }
                self.book_of_work_slots[sid] = slot
                saved_slots.append(copy.deepcopy(slot))
            out = copy.deepcopy(plan)
            out["slots"] = saved_slots
            return out

    def merge_companies_into_book_plan(
        self,
        plan_id: str,
        new_slots: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Append hold/research slots for companies not already on the plan."""
        with self._lock:
            plan = self.book_of_work_plans.get(plan_id)
            if not plan:
                raise ValueError("Plan not found")
            existing = {
                s["company_id"]
                for s in self.book_of_work_slots.values()
                if s["plan_id"] == plan_id
            }
            for raw in new_slots:
                if raw["company_id"] in existing:
                    continue
                if raw.get("kind") not in ("hold", "research", "stale"):
                    raw = {**raw, "kind": "hold", "reason": raw.get("reason") or "Merged after discovery."}
                sid = _uid()
                slot = {
                    "id": sid,
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
                }
                self.book_of_work_slots[sid] = slot
                existing.add(raw["company_id"])
            return self.get_book_plan_by_id(plan_id)  # type: ignore[return-value]

    def list_relationships(self, company_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                copy.deepcopy(r)
                for r in self.company_relationships
                if r.get("company_id") == company_id or r.get("related_company_id") == company_id
            ]


def get_demo_store():
    """Backward-compatible alias for get_store()."""
    from apps.api.app.core.store import get_store

    return get_store()
