from __future__ import annotations

import pytest
from datetime import datetime, timezone

from capmesh.health import HealthChecker, HealthStatus


class TestHealthChecker:
    def test_unknown_is_healthy(self):
        checker = HealthChecker()
        assert checker.is_healthy("ns", "svc", "1.0.0") is True

    def test_get_status_unknown_returns_none(self):
        checker = HealthChecker()
        assert checker.get_status("ns", "svc", "1.0.0") is None

    def test_update_sets_healthy(self):
        checker = HealthChecker()
        checker.update("ns", "svc", "1.0.0", healthy=True)
        assert checker.is_healthy("ns", "svc", "1.0.0") is True

    def test_update_sets_unhealthy(self):
        checker = HealthChecker()
        checker.update("ns", "svc", "1.0.0", healthy=False)
        assert checker.is_healthy("ns", "svc", "1.0.0") is False

    def test_update_with_error(self):
        checker = HealthChecker()
        checker.update("ns", "svc", "1.0.0", healthy=False, error="connection refused")
        status = checker.get_status("ns", "svc", "1.0.0")
        assert status is not None
        assert status.error == "connection refused"
        assert status.healthy is False

    def test_get_status_returns_health_status(self):
        checker = HealthChecker()
        checker.update("ns", "svc", "1.0.0", healthy=True)
        status = checker.get_status("ns", "svc", "1.0.0")
        assert isinstance(status, HealthStatus)
        assert status.healthy is True
        assert status.error is None
        assert isinstance(status.last_checked, datetime)
        assert status.last_checked.tzinfo is not None

    def test_key_format(self):
        checker = HealthChecker()
        assert checker._key("mynamespace", "myservice", "2.3.4") == "mynamespace/myservice:2.3.4"

    def test_different_providers_independent(self):
        checker = HealthChecker()
        checker.update("ns", "svc-a", "1.0.0", healthy=True)
        checker.update("ns", "svc-b", "1.0.0", healthy=False)
        assert checker.is_healthy("ns", "svc-a", "1.0.0") is True
        assert checker.is_healthy("ns", "svc-b", "1.0.0") is False

    def test_different_versions_independent(self):
        checker = HealthChecker()
        checker.update("ns", "svc", "1.0.0", healthy=True)
        checker.update("ns", "svc", "2.0.0", healthy=False)
        assert checker.is_healthy("ns", "svc", "1.0.0") is True
        assert checker.is_healthy("ns", "svc", "2.0.0") is False

    def test_update_overwrites(self):
        checker = HealthChecker()
        checker.update("ns", "svc", "1.0.0", healthy=True)
        checker.update("ns", "svc", "1.0.0", healthy=False, error="timeout")
        status = checker.get_status("ns", "svc", "1.0.0")
        assert status.healthy is False
        assert status.error == "timeout"

    @pytest.mark.asyncio
    async def test_refresh_stub(self):
        checker = HealthChecker()
        # Should not raise
        await checker.refresh("ns", "svc", "1.0.0")
