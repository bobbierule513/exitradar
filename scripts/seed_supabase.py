#!/usr/bin/env python3
"""Seed Supabase with the demo workspace, thesis, and multi-category companies.

Usage (from repo root, with .env configured):

    PYTHONPATH=. python scripts/seed_supabase.py

Requires DEMO_MODE=false credentials: SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY.
Idempotent on the fixed demo UUIDs / company domains.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.app.core.postgres_store import PostgresStore
from apps.api.app.core.seed_data import (
    DEMO_THESIS,
    DEMO_THESIS_ID,
    DEMO_USER_ID,
    DEMO_WORKSPACE_ID,
    apply_hvac_seed,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("seed_supabase")


def main() -> int:
    """Insert demo user, workspace, thesis, and HVAC companies."""
    store = PostgresStore()
    store.upsert_user(DEMO_USER_ID, "demo@exitradar.local")
    store.upsert_workspace(
        DEMO_WORKSPACE_ID,
        DEMO_USER_ID,
        "Caprae Demo Workspace",
        settings={"cadence": {"max_outreach_per_week": 5, "max_research_slots": 4}},
    )
    store.ensure_membership(DEMO_WORKSPACE_ID, DEMO_USER_ID, "owner")
    store.upsert_thesis(
        DEMO_THESIS_ID,
        DEMO_WORKSPACE_ID,
        DEMO_THESIS["name"],
        DEMO_THESIS["criteria"],
        DEMO_THESIS["strategy"],
    )
    apply_hvac_seed(store, DEMO_WORKSPACE_ID, DEMO_THESIS_ID)
    companies = store.list_companies(DEMO_WORKSPACE_ID)
    logger.info(
        "Seeded workspace %s with %s companies and thesis %s",
        DEMO_WORKSPACE_ID,
        len(companies),
        DEMO_THESIS_ID,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
