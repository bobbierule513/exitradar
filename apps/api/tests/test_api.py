"""Basic API and intelligence unit tests."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from apps.api.app.core.demo_store import DemoStore
from apps.api.app.main import app
from workers.intelligence.engines import compute_opportunity, next_best_action
from workers.resolution.resolve import normalize_name, resolve_company


@pytest.fixture
def store() -> DemoStore:
    return DemoStore(demo_mode=True)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_workspaces_and_command_center(client: TestClient) -> None:
    r = client.get("/api/v1/workspaces")
    assert r.status_code == 200
    assert len(r.json()) >= 1
    ws = r.json()[0]["id"]
    cc = client.get(f"/api/v1/workspaces/{ws}/command-center")
    assert cc.status_code == 200
    assert "opportunity_count" in cc.json()


def test_list_opportunities(client: TestClient) -> None:
    theses = client.get(
        "/api/v1/theses?workspace_id=00000000-0000-4000-8000-000000000010"
    )
    assert theses.status_code == 200
    tid = theses.json()[0]["id"]
    opps = client.get(f"/api/v1/theses/{tid}/opportunities")
    assert opps.status_code == 200
    assert len(opps.json()) >= 1
    assert "opportunity_score" in opps.json()[0]


def test_seed_has_at_least_fifteen_companies_across_categories(client: TestClient) -> None:
    ws = "00000000-0000-4000-8000-000000000010"
    rows = client.get(f"/api/v1/companies?workspace_id={ws}").json()
    industries = {c.get("industry") for c in rows if c.get("industry")}
    assert len(rows) >= 15
    assert len(industries) >= 8
    assert "HVAC" in industries
    assert "Plumbing" in industries
    assert "Dental" in industries


def test_normalize_name() -> None:
    assert normalize_name("Valley Climate Control, LLC") == "valley climate control"


def test_resolve_dedup(store: DemoStore) -> None:
    a = resolve_company(
        store,
        name="Acme HVAC",
        domain="acmehvac.example",
        phone="+15551212",
        address="1 Main St",
        geo={"city": "Phoenix", "state": "AZ"},
        industry="HVAC",
        source="test",
        external_id="ext-1",
        workspace_id=None,
    )
    b = resolve_company(
        store,
        name="Acme HVAC Inc",
        domain="acmehvac.example",
        phone="+15551212",
        address="1 Main St",
        geo={"city": "Phoenix", "state": "AZ"},
        industry="HVAC",
        source="test",
        external_id="ext-2",
        workspace_id=None,
    )
    assert a["id"] == b["id"]


def test_opportunity_and_nba(store: DemoStore) -> None:
    thesis = store.list_theses("00000000-0000-4000-8000-000000000010")[0]
    company = store.list_companies()[0]
    signals = store.list_signals(company["id"])
    contacts = store.list_contacts(company["id"])
    opp = compute_opportunity(company, thesis, signals, contacts, peer_count=4)
    assert 0 <= opp["opportunity_score"] <= 100
    nba = next_best_action(opp)
    assert nba["action"] in {
        "CONTACT_NOW",
        "RELATIONSHIP_FIRST",
        "RESEARCH_MORE",
        "MONITOR",
        "DEPRIORITIZE",
    }


def test_search_job_inline(client: TestClient) -> None:
    theses = client.get(
        "/api/v1/theses?workspace_id=00000000-0000-4000-8000-000000000010"
    ).json()
    tid = theses[0]["id"]
    job = client.post(
        "/api/v1/search-jobs",
        json={"thesis_id": tid, "location": "Phoenix, AZ", "max_results": 3},
    )
    assert job.status_code == 201
    body = job.json()
    assert body["status"] == "completed"
    assert body.get("enqueue", {}).get("mode") == "sync"


def test_demo_enqueue_skips_redis() -> None:
    from workers.queue import enqueue

    result = enqueue("standard", lambda: "inline-ok")
    assert result == {"mode": "sync", "result": "inline-ok"}


class _ProtocolStore:
    """Store surface without DemoStore.companies / company_sources attributes."""

    def __init__(self) -> None:
        self._companies: Dict[str, Dict[str, Any]] = {}
        self._sources: List[Dict[str, Any]] = []

    def list_companies(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        rows = list(self._companies.values())
        if workspace_id:
            rows = [c for c in rows if c.get("workspace_id") == workspace_id]
        return rows

    def list_company_sources(self) -> List[Dict[str, Any]]:
        return list(self._sources)

    def get_company(self, company_id: str) -> Optional[Dict[str, Any]]:
        return self._companies.get(company_id)

    def upsert_company(self, data: dict) -> Dict[str, Any]:
        cid = data.get("id") or "co-1"
        row = {**data, "id": cid}
        self._companies[cid] = row
        return row

    def add_company_source(
        self, company_id: str, source: str, external_id: str, confidence: float = 0.8
    ) -> None:
        self._sources.append(
            {
                "company_id": company_id,
                "source": source,
                "external_id": external_id,
                "confidence": confidence,
            }
        )


def test_resolve_without_demo_store_attributes() -> None:
    store = _ProtocolStore()
    a = resolve_company(
        store,
        name="Acme HVAC",
        domain="acmehvac.example",
        phone="+15551212",
        address="1 Main St",
        geo={"city": "Phoenix", "state": "AZ"},
        industry="HVAC",
        source="test",
        external_id="ext-1",
        workspace_id="ws-1",
    )
    b = resolve_company(
        store,
        name="Acme HVAC Inc",
        domain="acmehvac.example",
        phone="+15551212",
        address="1 Main St",
        geo={"city": "Phoenix", "state": "AZ"},
        industry="HVAC",
        source="test",
        external_id="ext-2",
        workspace_id="ws-1",
    )
    assert a["id"] == b["id"]
    assert not hasattr(store, "companies")
    assert not hasattr(store, "company_sources")


def test_create_thesis_from_natural_language(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Semantic search should persist a structured thesis from a plain-English query."""
    from workers.llm import client as llm_client

    monkeypatch.setattr(llm_client, "parse_thesis_nl", llm_client._heuristic_thesis_parse)
    r = client.post(
        "/api/v1/theses",
        json={
            "workspace_id": "00000000-0000-4000-8000-000000000010",
            "name": "Semantic search",
            "natural_language": "US-based HVAC service businesses in CA, owner-operated",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert "HVAC" in (body.get("criteria") or {}).get("industries", [])
    assert "CA" in ((body.get("criteria") or {}).get("geographies") or [{}])[0].get(
        "states", []
    )


def test_resolve_groq_retired_model(monkeypatch: pytest.MonkeyPatch) -> None:
    from apps.api.app.core.config import get_settings
    from workers.llm.client import GROQ_DEFAULT_MODEL, LLMClient

    monkeypatch.setenv("LLM_MODEL", "llama-3.3-70b-versatile")
    get_settings.cache_clear()
    try:
        resolved = LLMClient()._resolve_groq_model()
        assert resolved == GROQ_DEFAULT_MODEL
    finally:
        get_settings.cache_clear()
