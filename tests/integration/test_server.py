import asyncio
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from capmesh.server.app import create_app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_MANIFEST = {
    "metadata": {
        "api_version": "capmesh.io/v1alpha1",
        "kind": "agent",
        "namespace": "security",
        "name": "reviewer",
        "version": "1.0.0",
        "owner": "test-team",
    },
    "provides": [{"capability": "security.code.review", "contract": "v1"}],
    "requires": [],
    "interface": {"protocol": "a2a", "endpoint": "https://agent.example"},
    "governance": {"visibility": "public", "status": "approved"},
}


@pytest.fixture
def app(tmp_path: Path):
    return create_app(root=tmp_path)


@pytest.fixture
def client(app):
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Task 1 — Health check
# ---------------------------------------------------------------------------


def test_healthz(client):
    response = _run(client.get("/healthz"))
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Task 2 — Registry endpoints
# ---------------------------------------------------------------------------


def test_register_provider(client):
    response = _run(client.post("/v1/providers/register", json=_MANIFEST))
    assert response.status_code == 200
    data = response.json()
    assert "digest" in data


def test_register_provider_duplicate_same_digest_is_idempotent(client):
    _run(client.post("/v1/providers/register", json=_MANIFEST))
    # Posting the same manifest again returns 200 (idempotent — same digest)
    response = _run(client.post("/v1/providers/register", json=_MANIFEST))
    assert response.status_code == 200
    assert "digest" in response.json()


def test_register_provider_duplicate_different_digest_returns_409(client):
    _run(client.post("/v1/providers/register", json=_MANIFEST))
    # Change the owner to produce a different digest for the same version
    modified = {**_MANIFEST, "metadata": {**_MANIFEST["metadata"], "owner": "other-team"}}
    response = _run(client.post("/v1/providers/register", json=modified))
    assert response.status_code == 409


def test_get_provider(client):
    _run(client.post("/v1/providers/register", json=_MANIFEST))
    response = _run(client.get("/v1/providers/security/reviewer"))
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"]["name"] == "reviewer"


def test_get_provider_not_found(client):
    response = _run(client.get("/v1/providers/nonexistent/nobody"))
    assert response.status_code == 404


def test_get_capabilities_providers(client):
    _run(client.post("/v1/providers/register", json=_MANIFEST))
    response = _run(client.get("/v1/capabilities/security.code.review/providers"))
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_search(client):
    _run(client.post("/v1/providers/register", json=_MANIFEST))
    response = _run(client.post("/v1/search", json={"query": "security"}))
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_publish_artifact_alias(client):
    response = _run(client.post("/v1/artifacts/publish", json=_MANIFEST))
    assert response.status_code == 200
    assert "digest" in response.json()


def test_get_artifact(client):
    _run(client.post("/v1/providers/register", json=_MANIFEST))
    response = _run(client.get("/v1/artifacts/security/reviewer/1.0.0"))
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"]["version"] == "1.0.0"


def test_get_artifact_not_found(client):
    response = _run(client.get("/v1/artifacts/security/nobody/9.9.9"))
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Task 3 — Resolution endpoints
# ---------------------------------------------------------------------------


def test_resolve(client):
    _run(client.post("/v1/providers/register", json=_MANIFEST))
    response = _run(
        client.post(
            "/v1/resolve",
            json={
                "capability": "security.code.review",
                "contract": "v1",
                "caller": {"identity": "test-user"},
            },
        )
    )
    assert response.status_code == 200
    data = response.json()
    assert "provider" in data
    assert "trace_id" in data


def test_resolve_not_found(client):
    response = _run(
        client.post(
            "/v1/resolve",
            json={
                "capability": "nonexistent",
                "contract": "v1",
                "caller": {"identity": "test"},
            },
        )
    )
    assert response.status_code == 404


def test_get_resolution_trace(client):
    _run(client.post("/v1/providers/register", json=_MANIFEST))
    resolve_resp = _run(
        client.post(
            "/v1/resolve",
            json={
                "capability": "security.code.review",
                "contract": "v1",
                "caller": {"identity": "test"},
            },
        )
    )
    trace_id = resolve_resp.json()["trace_id"]

    response = _run(client.get(f"/v1/resolutions/{trace_id}"))
    assert response.status_code == 200
    data = response.json()
    assert data["trace_id"] == trace_id


def test_get_resolution_trace_not_found(client):
    response = _run(client.get("/v1/resolutions/nonexistent-trace-id"))
    assert response.status_code == 404
