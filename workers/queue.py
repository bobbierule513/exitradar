"""Queue helpers — enqueue jobs or run inline in demo mode."""

from __future__ import annotations

import logging
from typing import Any, Callable

from apps.api.app.core.config import get_settings

logger = logging.getLogger(__name__)


def enqueue(queue_name: str, func: Callable, *args: Any, **kwargs: Any) -> Any:
    """Enqueue to RQ when Redis is up; otherwise run synchronously.

    DEMO_MODE uses an in-process DemoStore singleton. RQ workers are a
    separate process with their own empty store, so jobs must run inline.
    """
    settings = get_settings()
    if settings.demo_mode:
        logger.info("DEMO_MODE=true; running %s inline", func.__name__)
        result = func(*args, **kwargs)
        return {"mode": "sync", "result": result}

    try:
        from redis import Redis
        from rq import Queue

        conn = Redis.from_url(settings.redis_url)
        conn.ping()
        q = Queue(queue_name, connection=conn)
        job = q.enqueue(func, *args, **kwargs)
        logger.info("Enqueued %s to %s job_id=%s", func.__name__, queue_name, job.id)
        return {"mode": "async", "job_id": job.id}
    except Exception as exc:  # noqa: BLE001
        logger.info("Redis unavailable (%s); running %s inline", exc, func.__name__)
        result = func(*args, **kwargs)
        return {"mode": "sync", "result": result}
