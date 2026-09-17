"""Workspace scoping and store selection."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from apps.api.app.core.demo_store import DemoStore
from apps.api.app.core.seed_data import DEMO_WORKSPACE_ID
from apps.api.app.core.store import get_store, reset_store
from apps.api.app.main import app

client = TestClient(app)


def test_get_store_is_demo_when_demo_mode() -> None:
    reset_store()
    store = get_store()
    assert isinstance(store, DemoStore)
    assert store.demo_mode is True


def test_list_companies_requires_workspace() -> None:
    r = client.get("/api/v1/companies")
    assert r.status_code == 422


def test_list_companies_scoped_to_workspace() -> None:
    r = client.get(f"/api/v1/companies?workspace_id={DEMO_WORKSPACE_ID}")
    assert r.status_code == 200
    rows = r.json()
    assert rows
    assert all(c.get("workspace_id") == DEMO_WORKSPACE_ID for c in rows)


def test_company_wrong_workspace_is_not_found() -> None:
    rows = client.get(f"/api/v1/companies?workspace_id={DEMO_WORKSPACE_ID}").json()
    company_id = rows[0]["id"]
    other = "00000000-0000-4000-8000-000000000099"
    r = client.get(f"/api/v1/companies/{company_id}?workspace_id={other}")
    assert r.status_code == 404


def test_company_matching_workspace_ok() -> None:
    rows = client.get(f"/api/v1/companies?workspace_id={DEMO_WORKSPACE_ID}").json()
    company_id = rows[0]["id"]
    r = client.get(f"/api/v1/companies/{company_id}?workspace_id={DEMO_WORKSPACE_ID}")
    assert r.status_code == 200
    assert r.json()["id"] == company_id
