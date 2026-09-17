"""RQ worker entrypoint."""

from __future__ import annotations

import logging
import sys

from redis import Redis
from rq import Queue, Worker

from apps.api.app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("workers.runner")


def main() -> None:
    """Start RQ workers listening on partitioned queues."""
    settings = get_settings()
    redis_conn = Redis.from_url(settings.redis_url)
    redis_conn.ping()
    queues = [
        Queue("critical", connection=redis_conn),
        Queue("interactive", connection=redis_conn),
        Queue("standard", connection=redis_conn),
        Queue("llm", connection=redis_conn),
        Queue("slow", connection=redis_conn),
    ]
    logger.info("Starting RQ worker on %s", settings.redis_url)
    worker = Worker(queues, connection=redis_conn)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        logger.error("Worker failed to start: %s", exc)
        sys.exit(1)
