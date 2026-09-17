"""Database and Supabase client helpers."""

from __future__ import annotations

import logging
from typing import Any, Optional

from apps.api.app.core.config import get_settings

logger = logging.getLogger(__name__)

_supabase = None
_engine = None


def get_supabase():
    """Return a service-role Supabase client (backend / workers only)."""
    global _supabase
    if _supabase is not None:
        return _supabase

    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        logger.warning("Supabase not configured; database operations will use demo store")
        return None

    from supabase import create_client

    _supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _supabase


def get_sqlalchemy_engine():
    """Return a SQLAlchemy engine when DATABASE_URL is set."""
    global _engine
    if _engine is not None:
        return _engine

    settings = get_settings()
    if not settings.database_url:
        return None

    from sqlalchemy import create_engine

    _engine = create_engine(settings.database_url, pool_pre_ping=True)
    return _engine


def table(name: str) -> Any:
    """Convenience accessor for Supabase table queries."""
    client = get_supabase()
    if client is None:
        raise RuntimeError("Supabase client not configured")
    return client.table(name)
