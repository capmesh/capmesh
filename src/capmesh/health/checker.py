from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class HealthStatus:
    healthy: bool
    last_checked: datetime
    error: str | None = None


class HealthChecker:
    def __init__(self) -> None:
        self._cache: dict[str, HealthStatus] = {}

    def _key(self, namespace: str, name: str, version: str) -> str:
        return f"{namespace}/{name}:{version}"

    def update(self, namespace: str, name: str, version: str, healthy: bool, error: str | None = None) -> None:
        key = self._key(namespace, name, version)
        self._cache[key] = HealthStatus(healthy=healthy, last_checked=datetime.now(timezone.utc), error=error)

    def is_healthy(self, namespace: str, name: str, version: str) -> bool:
        key = self._key(namespace, name, version)
        status = self._cache.get(key)
        if status is None:
            return True  # V1: unknown = healthy
        return status.healthy

    def get_status(self, namespace: str, name: str, version: str) -> HealthStatus | None:
        return self._cache.get(self._key(namespace, name, version))

    async def refresh(self, namespace: str, name: str, version: str) -> None:
        """Stub for V1: background async refresh interface."""
        pass
