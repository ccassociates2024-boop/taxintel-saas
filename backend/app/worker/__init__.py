"""ARQ background worker.

Run with:
    python -m arq app.worker.WorkerSettings

Queues are added in later phases (billing, esign, digilocker, whatsapp).
This module defines the base WorkerSettings class that all queued tasks
will be registered into as integration phases land.
"""

from __future__ import annotations

import os
import logging

import structlog
from arq.connections import RedisSettings

log = structlog.get_logger(__name__)


async def startup(ctx: dict) -> None:
    from app.core.logging import configure_logging
    configure_logging(log_level=os.environ.get("LOG_LEVEL", "INFO"))
    log.info("worker.startup")


async def shutdown(ctx: dict) -> None:
    log.info("worker.shutdown")


class WorkerSettings:
    """ARQ worker configuration.

    Phase 0: skeleton with no registered functions.
    Functions are added per phase as integrations land.
    """

    functions: list = []

    on_startup = startup
    on_shutdown = shutdown

    # Redis connection — read from env at class definition time
    redis_settings = RedisSettings.from_dsn(
        os.environ.get("REDIS_URL", "redis://localhost:6379")
    )

    # Keep failed jobs for 24 hours for inspection
    keep_result_forever = False
    max_jobs = 10
    poll_delay = 0.5

    # Default job timeout: 5 minutes
    job_timeout = 300
