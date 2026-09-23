# CapMesh Phase 4: FastAPI Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI REST API server exposing all registry and resolution operations, with API key auth middleware, and a `capmesh server start` CLI command. Add a Dockerfile for containerized deployment.

**Architecture:** FastAPI app as a thin HTTP layer over the existing Registry, Resolver, and PolicyEngine. API key middleware validates `Authorization: Bearer <key>` headers. Request/response models are Pydantic schemas separate from internal models. The server shares the same SQLite storage as the CLI.

**Tech Stack:** Python 3.10+, FastAPI, Uvicorn, httpx (test client)

**Spec:** `docs/superpowers/specs/2026-09-23-capmesh-v1-design.md` (Section 8)

## Global Constraints

- Python >= 3.10, Pydantic >= 2.0
- Add `fastapi>=0.100`, `uvicorn>=0.20`, `httpx>=0.24` to dependencies
- API key via `Authorization: Bearer <key>` header
- All endpoints under `/v1/` prefix
- `GET /healthz` — no auth required
- Server shares `~/.capmesh/` storage with CLI (configurable via CAPMESH_ROOT)

---

### Task 1: Add Server Dependencies + FastAPI App Skeleton

**Files:**
- Modify: `pyproject.toml` (add server optional deps)
- Create: `src/capmesh/server/__init__.py`
- Create: `src/capmesh/server/app.py`
- Create: `tests/integration/test_server.py`

**Interfaces:**
- Consumes: `Registry` from Phase 1
- Produces:
  - `create_app(root: Path | None) -> FastAPI` — creates configured FastAPI app
  - `GET /healthz` returns `{"status": "ok"}`

- [ ] **Step 1: Add dependencies to pyproject.toml**

Add to `[project.optional-dependencies]`:
```toml
server = [
    "fastapi>=0.100",
    "uvicorn>=0.20",
    "httpx>=0.24",
]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "httpx>=0.24",
]
```

- [ ] **Step 2: Install server deps**

```bash
pip install -e ".[server,dev]"
```

- [ ] **Step 3: Write failing tests**

`tests/integration/test_server.py`:
```python
import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from capmesh.server.app import create_app
import asyncio


@pytest.fixture
def app(tmp_path: Path):
    return create_app(root=tmp_path)


@pytest.fixture
def client(app):
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def test_healthz(client):
    response = asyncio.get_event_loop().run_until_complete(client.get("/healthz"))
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
pytest tests/integration/test_server.py -v
```

- [ ] **Step 5: Implement app skeleton**

`src/capmesh/server/__init__.py`:
```python
```

`src/capmesh/server/app.py`:
```python
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from capmesh.registry import Registry


def create_app(root: Path | None = None) -> FastAPI:
    app = FastAPI(title="CapMesh Registry", version="0.1.0")

    registry = Registry(root=root)
    app.state.registry = registry

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    return app
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/integration/test_server.py -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/capmesh/server/ tests/integration/test_server.py
git commit -m "feat: add FastAPI app skeleton with healthz endpoint"
```

---

### Task 2: Registry API Endpoints

**Files:**
- Modify: `src/capmesh/server/app.py`
- Create: `src/capmesh/server/schemas.py`
- Modify: `tests/integration/test_server.py`

**Interfaces:**
- Consumes: `Registry`, `Manifest`, `ArtifactRecord` from Phase 1; `manifest_from_yaml` from Phase 1
- Produces:
  - `POST /v1/providers/register` — register a provider from manifest JSON
  - `GET /v1/providers/{namespace}/{name}` — get latest provider
  - `GET /v1/capabilities/{capability_id}/providers` — list providers
  - `POST /v1/search` — keyword search
  - `POST /v1/artifacts/publish` — publish a built artifact
  - `GET /v1/artifacts/{namespace}/{name}/{version}` — get specific artifact

- [ ] **Step 1: Write failing tests**

Append to `tests/integration/test_server.py`:
```python
def test_register_provider(client):
    manifest = {
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
    response = asyncio.get_event_loop().run_until_complete(
        client.post("/v1/providers/register", json=manifest)
    )
    assert response.status_code == 200
    data = response.json()
    assert "digest" in data


def test_get_provider(client):
    manifest = {
        "metadata": {
            "api_version": "capmesh.io/v1alpha1",
            "kind": "agent", "namespace": "security",
            "name": "reviewer", "version": "1.0.0", "owner": "test",
        },
        "provides": [{"capability": "security.code.review", "contract": "v1"}],
        "requires": [],
        "interface": {"protocol": "a2a", "endpoint": "https://agent.example"},
        "governance": {"visibility": "public", "status": "approved"},
    }
    asyncio.get_event_loop().run_until_complete(
        client.post("/v1/providers/register", json=manifest)
    )
    response = asyncio.get_event_loop().run_until_complete(
        client.get("/v1/providers/security/reviewer")
    )
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"]["name"] == "reviewer"


def test_get_capabilities_providers(client):
    manifest = {
        "metadata": {
            "api_version": "capmesh.io/v1alpha1",
            "kind": "agent", "namespace": "security",
            "name": "reviewer", "version": "1.0.0", "owner": "test",
        },
        "provides": [{"capability": "security.code.review", "contract": "v1"}],
        "requires": [],
        "interface": {"protocol": "a2a", "endpoint": "https://agent.example"},
        "governance": {"visibility": "public", "status": "approved"},
    }
    asyncio.get_event_loop().run_until_complete(
        client.post("/v1/providers/register", json=manifest)
    )
    response = asyncio.get_event_loop().run_until_complete(
        client.get("/v1/capabilities/security.code.review/providers")
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_search(client):
    manifest = {
        "metadata": {
            "api_version": "capmesh.io/v1alpha1",
            "kind": "agent", "namespace": "security",
            "name": "reviewer", "version": "1.0.0", "owner": "test",
        },
        "provides": [{"capability": "security.code.review", "contract": "v1"}],
        "requires": [],
        "interface": {"protocol": "a2a", "endpoint": "https://agent.example"},
        "governance": {"visibility": "public", "status": "approved"},
    }
    asyncio.get_event_loop().run_until_complete(
        client.post("/v1/providers/register", json=manifest)
    )
    response = asyncio.get_event_loop().run_until_complete(
        client.post("/v1/search", json={"query": "security"})
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_get_artifact(client):
    manifest = {
        "metadata": {
            "api_version": "capmesh.io/v1alpha1",
            "kind": "agent", "namespace": "security",
            "name": "reviewer", "version": "1.0.0", "owner": "test",
        },
        "provides": [{"capability": "security.code.review", "contract": "v1"}],
        "requires": [],
        "interface": {"protocol": "a2a", "endpoint": "https://agent.example"},
        "governance": {"visibility": "public", "status": "approved"},
    }
    asyncio.get_event_loop().run_until_complete(
        client.post("/v1/providers/register", json=manifest)
    )
    response = asyncio.get_event_loop().run_until_complete(
        client.get("/v1/artifacts/security/reviewer/1.0.0")
    )
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"]["version"] == "1.0.0"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/integration/test_server.py -v
```

- [ ] **Step 3: Implement server endpoints**

`src/capmesh/server/schemas.py`:
```python
from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str


class RegisterResponse(BaseModel):
    digest: str
    message: str
```

Update `src/capmesh/server/app.py`:
```python
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request

from capmesh.models.manifest import Manifest
from capmesh.registry import Registry, DuplicateVersionError
from capmesh.server.schemas import SearchRequest, RegisterResponse


def create_app(root: Path | None = None) -> FastAPI:
    app = FastAPI(title="CapMesh Registry", version="0.1.0")

    registry = Registry(root=root)
    app.state.registry = registry

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.post("/v1/providers/register")
    async def register_provider(manifest_data: dict):
        try:
            manifest = Manifest.model_validate(manifest_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid manifest: {e}")
        try:
            digest = registry.register(manifest)
        except DuplicateVersionError as e:
            raise HTTPException(status_code=409, detail=str(e))
        return RegisterResponse(digest=digest, message="registered")

    @app.post("/v1/artifacts/publish")
    async def publish_artifact(manifest_data: dict):
        return await register_provider(manifest_data)

    @app.get("/v1/providers/{namespace}/{name}")
    async def get_provider(namespace: str, name: str):
        # Get latest version
        artifacts = registry.list(namespace=namespace)
        matches = [a for a in artifacts if a.name == name]
        if not matches:
            raise HTTPException(status_code=404, detail="Provider not found")
        latest = max(matches, key=lambda a: a.version)
        manifest = registry.get(namespace, name, latest.version)
        if manifest is None:
            raise HTTPException(status_code=404, detail="Provider not found")
        return manifest.model_dump(mode="json")

    @app.get("/v1/capabilities/{capability_id}/providers")
    async def get_capability_providers(capability_id: str, contract: str = "v1"):
        providers = registry.providers_for(capability_id, contract)
        return [
            {"namespace": p.namespace, "name": p.name, "version": p.version, "kind": p.kind.value}
            for p in providers
        ]

    @app.post("/v1/search")
    async def search(request: SearchRequest):
        results = registry.search(request.query)
        return [
            {"namespace": r.namespace, "name": r.name, "version": r.version, "kind": r.kind.value}
            for r in results
        ]

    @app.get("/v1/artifacts/{namespace}/{name}/{version}")
    async def get_artifact(namespace: str, name: str, version: str):
        manifest = registry.get(namespace, name, version)
        if manifest is None:
            raise HTTPException(status_code=404, detail="Artifact not found")
        return manifest.model_dump(mode="json")

    return app
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/integration/test_server.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/capmesh/server/ tests/integration/test_server.py
git commit -m "feat: add registry API endpoints for providers, capabilities, search, and artifacts"
```

---

### Task 3: Resolution API Endpoint + Trace Query

**Files:**
- Modify: `src/capmesh/server/app.py`
- Modify: `tests/integration/test_server.py`

**Interfaces:**
- Consumes: `Resolver` from Phase 2; `TraceStore` from Phase 2; `ResolveRequest`, `CallerContext` from Phase 2
- Produces:
  - `POST /v1/resolve` — resolve capability to provider
  - `GET /v1/resolutions/{trace_id}` — query resolution trace

- [ ] **Step 1: Write failing tests**

Append to `tests/integration/test_server.py`:
```python
def test_resolve(client):
    # Register a provider first
    manifest = {
        "metadata": {
            "api_version": "capmesh.io/v1alpha1",
            "kind": "agent", "namespace": "security",
            "name": "reviewer", "version": "1.0.0", "owner": "test",
        },
        "provides": [{"capability": "security.code.review", "contract": "v1"}],
        "requires": [],
        "interface": {"protocol": "a2a", "endpoint": "https://agent.example"},
        "governance": {"visibility": "public", "status": "approved"},
    }
    asyncio.get_event_loop().run_until_complete(
        client.post("/v1/providers/register", json=manifest)
    )
    response = asyncio.get_event_loop().run_until_complete(
        client.post("/v1/resolve", json={
            "capability": "security.code.review",
            "contract": "v1",
            "caller": {"identity": "test-user"},
        })
    )
    assert response.status_code == 200
    data = response.json()
    assert "provider" in data
    assert "trace_id" in data


def test_resolve_not_found(client):
    response = asyncio.get_event_loop().run_until_complete(
        client.post("/v1/resolve", json={
            "capability": "nonexistent",
            "contract": "v1",
            "caller": {"identity": "test"},
        })
    )
    assert response.status_code == 404


def test_get_resolution_trace(client):
    manifest = {
        "metadata": {
            "api_version": "capmesh.io/v1alpha1",
            "kind": "agent", "namespace": "security",
            "name": "reviewer", "version": "1.0.0", "owner": "test",
        },
        "provides": [{"capability": "security.code.review", "contract": "v1"}],
        "requires": [],
        "interface": {"protocol": "a2a", "endpoint": "https://agent.example"},
        "governance": {"visibility": "public", "status": "approved"},
    }
    asyncio.get_event_loop().run_until_complete(
        client.post("/v1/providers/register", json=manifest)
    )
    resolve_resp = asyncio.get_event_loop().run_until_complete(
        client.post("/v1/resolve", json={
            "capability": "security.code.review",
            "contract": "v1",
            "caller": {"identity": "test"},
        })
    )
    trace_id = resolve_resp.json()["trace_id"]

    response = asyncio.get_event_loop().run_until_complete(
        client.get(f"/v1/resolutions/{trace_id}")
    )
    assert response.status_code == 200
    data = response.json()
    assert data["trace_id"] == trace_id
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/integration/test_server.py -v
```

- [ ] **Step 3: Add resolve and trace endpoints to app.py**

Add imports and endpoints to `create_app()` in `src/capmesh/server/app.py`:
```python
import sqlite3
from capmesh.models.resolution import CallerContext, ResolveRequest
from capmesh.policy import default_policy_engine
from capmesh.resolver import Resolver, ResolutionError
from capmesh.adapters.defaults import default_adapter_registry
from capmesh.telemetry import TraceStore

# Inside create_app, after registry creation:
root_path = root if root else Path.home() / ".capmesh"
db = sqlite3.connect(str(root_path / "traces.db"))
db.row_factory = sqlite3.Row
trace_store = TraceStore(db)
trace_store.init_schema()

policy = default_policy_engine()
resolver = Resolver(registry=registry, policy_engine=policy, trace_store=trace_store)
adapter_reg = default_adapter_registry(resolver=resolver)
resolver._adapter_registry = adapter_reg

@app.post("/v1/resolve")
async def resolve_capability(request_data: dict):
    try:
        caller = CallerContext.model_validate(request_data.get("caller", {}))
        req = ResolveRequest(
            capability=request_data["capability"],
            contract=request_data.get("contract", "v1"),
            caller=caller,
            version_constraint=request_data.get("version_constraint"),
        )
        resolution = resolver.resolve(req)
        return {
            "provider": f"{resolution.provider_namespace}/{resolution.provider_name}:{resolution.provider_version}",
            "protocol": resolution.binding.protocol,
            "binding": resolution.binding.connection,
            "trace_id": resolution.trace.trace_id,
        }
    except ResolutionError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/v1/resolutions/{trace_id}")
async def get_resolution_trace(trace_id: str):
    trace = trace_store.get_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace.model_dump(mode="json")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/integration/test_server.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/capmesh/server/ tests/integration/test_server.py
git commit -m "feat: add resolve and trace query API endpoints"
```

---

### Task 4: Server CLI Command + Dockerfile

**Files:**
- Create: `src/capmesh/cli/server_commands.py`
- Modify: `src/capmesh/cli/__init__.py`
- Create: `Dockerfile`

**Interfaces:**
- Consumes: `create_app` from Task 1
- Produces:
  - `capmesh server start` CLI command (runs uvicorn)
  - `Dockerfile` for containerized deployment

- [ ] **Step 1: Implement server CLI command**

`src/capmesh/cli/server_commands.py`:
```python
from __future__ import annotations

import os
from pathlib import Path

import typer

server_app = typer.Typer(help="Registry server commands.", no_args_is_help=True)


@server_app.command()
def start(
    host: str = typer.Option("0.0.0.0", help="Bind host"),
    port: int = typer.Option(8080, help="Bind port"),
) -> None:
    """Start the CapMesh registry server."""
    import uvicorn
    from capmesh.server.app import create_app

    root = os.environ.get("CAPMESH_ROOT")
    app = create_app(root=Path(root) if root else None)
    uvicorn.run(app, host=host, port=port)
```

- [ ] **Step 2: Register server command in CLI**

Add to `src/capmesh/cli/__init__.py`:
```python
from capmesh.cli.server_commands import server_app
app.add_typer(server_app, name="server")
```

- [ ] **Step 3: Create Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/

RUN pip install --no-cache-dir ".[server]"

ENV CAPMESH_ROOT=/data

EXPOSE 8080

VOLUME ["/data"]

CMD ["capmesh", "server", "start", "--host", "0.0.0.0", "--port", "8080"]
```

- [ ] **Step 4: Verify CLI help works**

```bash
capmesh server --help
capmesh server start --help
```

- [ ] **Step 5: Commit**

```bash
git add src/capmesh/cli/server_commands.py src/capmesh/cli/__init__.py Dockerfile
git commit -m "feat: add server start CLI command and Dockerfile"
```

---

### Task 5: Full Phase 4 Test Verification

**Files:**
- No new files

- [ ] **Step 1: Run full test suite with coverage**

```bash
pytest tests/ -v --cov=capmesh --cov-report=term-missing
```

Expected: all pass, coverage >= 80%

- [ ] **Step 2: Commit if any fixes needed**

```bash
git add -A
git commit -m "chore: verify Phase 4 test suite"
```
