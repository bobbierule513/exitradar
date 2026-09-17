"""Book of Work policy and API workflow tests."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from apps.api.app.core.demo_store import DemoStore
from apps.api.app.core.scoring import BOOK_OF_WORK_VERSION
from apps.api.app.main import app
from workers.intelligence.book_of_work import (
    are_substitutes,
    build_substitute_clusters,
    build_week_plan,
    estimate_research_lift,
    is_expired,
    promote_on_skip,
    resolve_cadence,
)
from workers.intelligence.book_service import complete_slot, ensure_book_of_work, skip_slot
from workers.llm.client import LLMClient


@pytest.fixture
def store() -> DemoStore:
    return DemoStore(demo_mode=True)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _company(name: str, city: str, state: str, lat: float, lng: float, **extra: Any) -> Dict[str, Any]:
    return {
        "id": extra.pop("id", name.lower().replace(" ", "-")),
        "canonical_name": name,
        "industry": "HVAC",
        "revenue_est": extra.pop("revenue_est", 4_000_000),
        "geo": {"city": city, "state": state, "lat": lat, "lng": lng, "country": "US"},
        **extra,
    }


def test_phoenix_scottsdale_are_substitutes() -> None:
    a = _company("Valley", "Phoenix", "AZ", 33.4484, -112.0740)
    b = _company("Apex", "Phoenix", "AZ", 33.4510, -112.0650, id="apex")
    c = _company("Gulf", "Tampa", "FL", 27.9506, -82.4572, id="gulf")
    assert are_substitutes(a, b)
    assert not are_substitutes(a, c)


def test_two_phoenix_contact_now_one_outreach_one_hold() -> None:
    now = datetime.now(timezone.utc)
    valley = _company("Valley Climate", "Phoenix", "AZ", 33.4484, -112.0740, id="valley")
    apex = _company("Apex Air", "Phoenix", "AZ", 33.451, -112.065, id="apex")
    opps = [
        {
            "company_id": "valley",
            "company": valley,
            "opportunity_score": 90,
            "explanation": {"missing": [], "timing_bucket": "ready_now"},
            "recommendation": {
                "id": "r1",
                "action": "CONTACT_NOW",
                "expires_at": (now + timedelta(days=6)).isoformat(),
                "reason": "Closing window",
                "status": "open",
            },
        },
        {
            "company_id": "apex",
            "company": apex,
            "opportunity_score": 85,
            "explanation": {"missing": [], "timing_bucket": "ready_now"},
            "recommendation": {
                "id": "r2",
                "action": "CONTACT_NOW",
                "expires_at": (now + timedelta(days=28)).isoformat(),
                "reason": "Longer window",
                "status": "open",
            },
        },
    ]
    thesis = {"id": "t1", "criteria": {}, "strategy": {}}
    plan = build_week_plan(opps, thesis, {"max_outreach_per_week": 5, "max_research_slots": 4}, now=now)
    outreach = [s for s in plan["slots"] if s["kind"] == "outreach"]
    hold = [s for s in plan["slots"] if s["kind"] == "hold"]
    assert len(outreach) == 1
    assert outreach[0]["company_id"] == "valley"
    assert len(hold) == 1
    assert hold[0]["company_id"] == "apex"
    assert "Substitute" in (hold[0]["reason"] or "")
    assert plan["substitute_edges"]


def test_tampa_and_phoenix_both_outreach() -> None:
    now = datetime.now(timezone.utc)
    valley = _company("Valley", "Phoenix", "AZ", 33.4484, -112.0740, id="valley")
    gulf = _company("Gulf", "Tampa", "FL", 27.95, -82.45, id="gulf")
    opps = [
        {
            "company_id": "valley",
            "company": valley,
            "opportunity_score": 90,
            "explanation": {"missing": []},
            "recommendation": {
                "id": "r1",
                "action": "CONTACT_NOW",
                "expires_at": (now + timedelta(days=10)).isoformat(),
                "reason": "x",
                "status": "open",
            },
        },
        {
            "company_id": "gulf",
            "company": gulf,
            "opportunity_score": 88,
            "explanation": {"missing": []},
            "recommendation": {
                "id": "r2",
                "action": "CONTACT_NOW",
                "expires_at": (now + timedelta(days=12)).isoformat(),
                "reason": "y",
                "status": "open",
            },
        },
    ]
    plan = build_week_plan(
        opps, {"id": "t", "criteria": {}}, {"max_outreach_per_week": 5, "max_research_slots": 2}, now=now
    )
    outreach_ids = {s["company_id"] for s in plan["slots"] if s["kind"] == "outreach"}
    assert outreach_ids == {"valley", "gulf"}


def test_expired_not_in_outreach() -> None:
    now = datetime.now(timezone.utc)
    c = _company("Stale Co", "Seattle", "WA", 47.6, -122.3, id="stale")
    opps = [
        {
            "company_id": "stale",
            "company": c,
            "opportunity_score": 80,
            "explanation": {"missing": []},
            "recommendation": {
                "id": "r1",
                "action": "CONTACT_NOW",
                "expires_at": (now - timedelta(days=5)).isoformat(),
                "reason": "expired",
                "status": "open",
            },
        }
    ]
    plan = build_week_plan(
        opps, {"id": "t", "criteria": {}}, {"max_outreach_per_week": 5, "max_research_slots": 2}, now=now
    )
    assert not any(s["kind"] == "outreach" for s in plan["slots"])
    assert any(s["kind"] == "stale" for s in plan["slots"])


def test_capacity_one_limits_outreach() -> None:
    now = datetime.now(timezone.utc)
    a = _company("A", "Phoenix", "AZ", 33.45, -112.07, id="a")
    b = _company("B", "Tampa", "FL", 27.95, -82.45, id="b")
    opps = []
    for cid, company, days in (("a", a, 5), ("b", b, 8)):
        opps.append(
            {
                "company_id": cid,
                "company": company,
                "opportunity_score": 90,
                "explanation": {"missing": []},
                "recommendation": {
                    "id": f"r-{cid}",
                    "action": "CONTACT_NOW",
                    "expires_at": (now + timedelta(days=days)).isoformat(),
                    "reason": "x",
                    "status": "open",
                },
            }
        )
    plan = build_week_plan(
        opps, {"id": "t", "criteria": {}}, {"max_outreach_per_week": 1, "max_research_slots": 0}, now=now
    )
    assert sum(1 for s in plan["slots"] if s["kind"] == "outreach") == 1
    assert sum(1 for s in plan["slots"] if s["kind"] == "hold") >= 1


def test_research_lift_prefers_contacts(store: DemoStore) -> None:
    thesis = store.list_theses("00000000-0000-4000-8000-000000000010")[0]
    bay = next(c for c in store.list_companies() if c["canonical_name"] == "Bay Area Comfort Systems")
    opp = store.get_opportunity(bay["id"], thesis["id"])
    assert opp is not None
    opp_full = {**opp, "company": bay, "recommendation": store.get_recommendation(bay["id"], thesis["id"])}
    tasks = estimate_research_lift(
        opp_full, bay, thesis, store.list_signals(bay["id"]), store.list_contacts(bay["id"])
    )
    assert tasks
    assert tasks[0]["field"] in ("contacts", "founded_year")
    assert tasks[0]["lift_per_hour"] > 0


def test_seed_plan_valley_over_apex(store: DemoStore) -> None:
    thesis = store.list_theses("00000000-0000-4000-8000-000000000010")[0]
    plan = ensure_book_of_work(store, thesis["id"], force=True)
    assert plan["model_version"] == BOOK_OF_WORK_VERSION
    outreach = [s for s in plan["slots"] if s["kind"] == "outreach" and s["status"] == "open"]
    names = [s["company"]["canonical_name"] for s in outreach]
    assert "Valley Climate Control" in names
    hold_names = [
        s["company"]["canonical_name"]
        for s in plan["slots"]
        if s["kind"] == "hold"
    ]
    assert "Apex Air Phoenix" in hold_names
    # Relationships persisted
    valley = next(c for c in store.list_companies() if "Valley" in c["canonical_name"])
    rels = store.list_relationships(valley["id"])
    assert any(r["relationship_type"] == "substitute" for r in rels)


def test_skip_promotes_substitute(store: DemoStore) -> None:
    thesis = store.list_theses("00000000-0000-4000-8000-000000000010")[0]
    plan = ensure_book_of_work(store, thesis["id"], force=True)
    valley_slot = next(
        s
        for s in plan["slots"]
        if s["kind"] == "outreach" and s["company"]["canonical_name"] == "Valley Climate Control"
    )
    updated = skip_slot(store, valley_slot["id"])
    apex = next(
        (
            s
            for s in updated["slots"]
            if s["company"]["canonical_name"] == "Apex Air Phoenix" and s["kind"] == "outreach"
        ),
        None,
    )
    assert apex is not None
    assert apex["status"] == "open"
    skipped = next(s for s in updated["slots"] if s["id"] == valley_slot["id"])
    assert skipped["status"] == "skipped"


def test_complete_writes_activity_and_pipeline(store: DemoStore) -> None:
    thesis = store.list_theses("00000000-0000-4000-8000-000000000010")[0]
    plan = ensure_book_of_work(store, thesis["id"], force=True)
    slot = next(s for s in plan["slots"] if s["kind"] == "outreach" and s["status"] == "open")
    complete_slot(store, slot["id"], outcome="called")
    activities = store.list_activities(slot["company_id"])
    assert any(a["activity_type"] == "book_of_work_complete" for a in activities)
    pipe = store.get_pipeline(slot["company_id"], thesis["id"])
    assert pipe and pipe["stage"] == "outreach"


def test_idempotent_get_book(store: DemoStore) -> None:
    thesis = store.list_theses("00000000-0000-4000-8000-000000000010")[0]
    a = ensure_book_of_work(store, thesis["id"], force=True)
    b = ensure_book_of_work(store, thesis["id"], force=False)
    assert a["id"] == b["id"]
    assert len(a["slots"]) == len(b["slots"])


def test_command_center_includes_book(client: TestClient) -> None:
    ws = client.get("/api/v1/workspaces").json()[0]["id"]
    cc = client.get(f"/api/v1/workspaces/{ws}/command-center")
    assert cc.status_code == 200
    body = cc.json()
    assert "book_of_work" in body
    assert body["book_of_work"]["slots"]
    assert "book_metrics" in body


def test_cadence_patch_and_regen(client: TestClient) -> None:
    ws = "00000000-0000-4000-8000-000000000010"
    tid = "00000000-0000-4000-8000-000000000020"
    r = client.patch(f"/api/v1/workspaces/{ws}/cadence", json={"max_outreach_per_week": 1})
    assert r.status_code == 200
    assert r.json()["max_outreach_per_week"] == 1
    gen = client.post(f"/api/v1/theses/{tid}/book-of-work", json={"force": True})
    assert gen.status_code == 201
    outreach = [s for s in gen.json()["slots"] if s["kind"] == "outreach"]
    assert len(outreach) == 1


def test_is_expired_helper() -> None:
    now = datetime.now(timezone.utc)
    assert is_expired({"expires_at": (now - timedelta(days=1)).isoformat()}, now)
    assert not is_expired({"expires_at": (now + timedelta(days=1)).isoformat()}, now)


def test_promote_on_skip_helper() -> None:
    slots = [
        {"id": "o1", "kind": "outreach", "cluster_id": "c1", "status": "open", "action": "CONTACT_NOW"},
        {
            "id": "h1",
            "kind": "hold",
            "cluster_id": "c1",
            "status": "open",
            "action": "CONTACT_NOW",
            "opportunity_score": 80,
        },
    ]
    assert promote_on_skip(slots, "o1")["id"] == "h1"


def test_groq_available_and_explicit_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    get_settings.cache_clear()
    client = LLMClient()
    assert client.available is True

    called = {"groq": False, "openai": False}

    def fake_groq(self, system: str, user: str, temperature: float = 0.2) -> str:
        called["groq"] = True
        return '{"ok": true}'

    def fake_openai(self, system: str, user: str, temperature: float = 0.2) -> str:
        called["openai"] = True
        return '{"ok": true}'

    monkeypatch.setattr(LLMClient, "_groq", fake_groq)
    monkeypatch.setattr(LLMClient, "_openai", fake_openai)
    client.complete("sys", "user")
    assert called["groq"] is True
    assert called["openai"] is False

    get_settings.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    get_settings.cache_clear()
    client2 = LLMClient()
    called["groq"] = False
    called["openai"] = False
    client2.complete("sys", "user")
    assert called["openai"] is True
    assert called["groq"] is False
    get_settings.cache_clear()


def test_resolve_cadence_overrides() -> None:
    c = resolve_cadence({"cadence": {"max_outreach_per_week": 2}}, {"cadence": {"max_research_slots": 1}})
    assert c["max_outreach_per_week"] == 2
    assert c["max_research_slots"] == 1
