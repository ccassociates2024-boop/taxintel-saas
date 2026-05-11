"""Unit tests for backend/app/worker/__init__.py."""

from __future__ import annotations

import pytest


class TestWorkerSettings:
    def test_worker_settings_importable(self):
        from app.worker import WorkerSettings

        assert WorkerSettings is not None

    def test_redis_settings_present(self):
        from app.worker import WorkerSettings

        assert hasattr(WorkerSettings, "redis_settings")

    def test_functions_list_exists(self):
        from app.worker import WorkerSettings

        assert isinstance(WorkerSettings.functions, list)

    def test_on_startup_callable(self):
        from app.worker import WorkerSettings

        assert callable(WorkerSettings.on_startup)

    def test_on_shutdown_callable(self):
        from app.worker import WorkerSettings

        assert callable(WorkerSettings.on_shutdown)

    def test_job_timeout_positive(self):
        from app.worker import WorkerSettings

        assert WorkerSettings.job_timeout > 0

    @pytest.mark.asyncio
    async def test_startup_does_not_raise(self):
        from app.worker import startup

        await startup({})

    @pytest.mark.asyncio
    async def test_shutdown_does_not_raise(self):
        from app.worker import shutdown

        await shutdown({})
