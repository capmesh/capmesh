from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException

from capmesh.adapters.defaults import default_adapter_registry
from capmesh.models.manifest import Manifest
from capmesh.models.resolution import CallerContext, ResolveRequest
from capmesh.policy.engine import default_policy_engine
from capmesh.registry import DuplicateVersionError, Registry
from capmesh.resolver.resolver import ResolutionError, Resolver
from capmesh.server.schemas import RegisterResponse, SearchRequest
from capmesh.telemetry.traces import TraceStore


def create_app(root: Path | None = None) -> FastAPI:
    app = FastAPI(title="CapMesh Registry", version="0.1.0")

    root_path = root if root is not None else Path.home() / ".capmesh"
    root_path.mkdir(parents=True, exist_ok=True)

    registry = Registry(root=root_path)
    app.state.registry = registry

    db = sqlite3.connect(str(root_path / "traces.db"), check_same_thread=False)
    db.row_factory = sqlite3.Row
    trace_store = TraceStore(db)
    trace_store.init_schema()

    policy = default_policy_engine()
    resolver = Resolver(
        registry=registry,
        policy_engine=policy,
        trace_store=trace_store,
    )
    adapter_reg = default_adapter_registry(resolver=resolver)
    resolver._adapter_registry = adapter_reg

    app.state.trace_store = trace_store
    app.state.resolver = resolver

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
            {
                "namespace": p.namespace,
                "name": p.name,
                "version": p.version,
                "kind": p.kind.value,
            }
            for p in providers
        ]

    @app.post("/v1/search")
    async def search(request: SearchRequest):
        results = registry.search(request.query)
        return [
            {
                "namespace": r.namespace,
                "name": r.name,
                "version": r.version,
                "kind": r.kind.value,
            }
            for r in results
        ]

    @app.get("/v1/artifacts/{namespace}/{name}/{version}")
    async def get_artifact(namespace: str, name: str, version: str):
        manifest = registry.get(namespace, name, version)
        if manifest is None:
            raise HTTPException(status_code=404, detail="Artifact not found")
        return manifest.model_dump(mode="json")

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
                "provider": (
                    f"{resolution.provider_namespace}/{resolution.provider_name}"
                    f":{resolution.provider_version}"
                ),
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

    return app
