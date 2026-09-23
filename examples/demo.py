#!/usr/bin/env python3
"""CapMesh Proof-of-Value Demo

Demonstrates:
1. Register providers from example manifests
2. Resolve capabilities to providers
3. Show resolution traces
4. Dynamically add a new provider without restart
5. Swap a compatible provider
"""
import sqlite3
import sys
from pathlib import Path

from capmesh.adapters.defaults import default_adapter_registry
from capmesh.models.resolution import CallerContext, ResolveRequest
from capmesh.models.serialization import manifest_from_yaml
from capmesh.policy import default_policy_engine
from capmesh.registry import Registry
from capmesh.resolver import Resolver, ResolutionError
from capmesh.telemetry import TraceStore


def main():
    # Setup: temp registry
    import tempfile
    root = Path(tempfile.mkdtemp(prefix="capmesh-demo-"))
    print(f"Registry root: {root}\n")

    registry = Registry(root=root)
    policy = default_policy_engine()
    db = sqlite3.connect(str(root / "traces.db"))
    db.row_factory = sqlite3.Row
    trace_store = TraceStore(db)
    trace_store.init_schema()

    resolver = Resolver(registry=registry, policy_engine=policy, trace_store=trace_store)
    adapter_reg = default_adapter_registry(resolver=resolver)
    resolver._adapter_registry = adapter_reg

    examples_dir = Path(__file__).parent

    # Step 1: Register providers
    print("=" * 60)
    print("STEP 1: Register providers")
    print("=" * 60)

    manifests_to_register = [
        "security-agent/manifest.yaml",
        "github-tool/manifest.yaml",
        "security-review-skill/manifest.yaml",
    ]

    for manifest_path in manifests_to_register:
        full_path = examples_dir / manifest_path
        yaml_str = full_path.read_text()
        manifest = manifest_from_yaml(yaml_str)
        digest = registry.register(manifest)
        print(f"  Registered: {manifest.metadata.namespace}/{manifest.metadata.name}:{manifest.metadata.version}")
        print(f"    Digest: sha256:{digest[:16]}...")
        print(f"    Provides: {', '.join(c.capability for c in manifest.provides)}")

    # Step 2: Resolve security.code.review
    print(f"\n{'=' * 60}")
    print("STEP 2: Resolve security.code.review/v1")
    print("=" * 60)

    request = ResolveRequest(
        capability="security.code.review",
        contract="v1",
        caller=CallerContext(identity="demo-orchestrator", environment="production"),
    )
    resolution = resolver.resolve(request)
    print(f"  Provider:  {resolution.provider_namespace}/{resolution.provider_name}:{resolution.provider_version}")
    print(f"  Protocol:  {resolution.binding.protocol}")
    print(f"  Trace ID:  {resolution.trace.trace_id}")
    print(f"  Resolution: {resolution.trace.resolution_ms:.1f} ms")

    # Step 3: Show trace
    print(f"\n{'=' * 60}")
    print("STEP 3: Resolution Trace")
    print("=" * 60)

    trace = trace_store.get_trace(resolution.trace.trace_id)
    print(f"  Requested: {trace.requested_capability}/{trace.requested_contract}")
    print(f"  Candidates: {len(trace.candidates)}")
    for c in trace.candidates:
        status = "PASS" if c.passed else f"FAIL ({c.rejection_reason})"
        print(f"    {c.provider}:{c.version} -> {status}")
    print(f"  Selected: {trace.selected_provider}")
    print(f"  Outcome: {trace.outcome}")

    # Step 4: Dynamic discovery — add performance agent WITHOUT restart
    print(f"\n{'=' * 60}")
    print("STEP 4: Dynamic Discovery — add new provider at runtime")
    print("=" * 60)

    perf_yaml = (examples_dir / "performance-agent/manifest.yaml").read_text()
    perf_manifest = manifest_from_yaml(perf_yaml)
    registry.register(perf_manifest)
    print(f"  Registered: {perf_manifest.metadata.namespace}/{perf_manifest.metadata.name}:{perf_manifest.metadata.version}")

    # Resolve performance.analyze — works immediately
    perf_request = ResolveRequest(
        capability="performance.analyze",
        contract="v1",
        caller=CallerContext(identity="demo-orchestrator"),
    )
    perf_resolution = resolver.resolve(perf_request)
    print(f"  Resolved:  {perf_resolution.provider_namespace}/{perf_resolution.provider_name}:{perf_resolution.provider_version}")
    print(f"  Protocol:  {perf_resolution.binding.protocol}")
    print("  No restart needed!")

    # Step 5: Provider swap — register a higher-version security reviewer
    print(f"\n{'=' * 60}")
    print("STEP 5: Provider Swap — higher version replaces selection")
    print("=" * 60)

    from capmesh.models import (
        A2AInterface, CapabilityRef, Governance, Kind, Manifest, Metadata,
        Status, Visibility,
    )
    new_reviewer = Manifest(
        metadata=Metadata(
            kind=Kind.AGENT, namespace="security", name="security-reviewer-v3",
            version="3.0.0", owner="security-engineering",
        ),
        provides=[CapabilityRef(capability="security.code.review", contract="v1")],
        requires=[],
        interface=A2AInterface(protocol="a2a", endpoint="https://security-v3.example.com"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED, environment=["production", "staging"]),
    )
    registry.register(new_reviewer)
    print(f"  Registered: security/security-reviewer-v3:3.0.0")

    resolution2 = resolver.resolve(request)
    print(f"  Re-resolved: {resolution2.provider_namespace}/{resolution2.provider_name}:{resolution2.provider_version}")
    print(f"  Previous:    {resolution.provider_namespace}/{resolution.provider_name}:{resolution.provider_version}")
    print(f"  No consumer code changes needed!")

    # Step 6: Resolve repository.read (MCP tool)
    print(f"\n{'=' * 60}")
    print("STEP 6: Resolve repository.read/v1 (MCP tool)")
    print("=" * 60)

    repo_request = ResolveRequest(
        capability="repository.read",
        contract="v1",
        caller=CallerContext(identity="demo-orchestrator"),
    )
    repo_resolution = resolver.resolve(repo_request)
    print(f"  Provider:  {repo_resolution.provider_namespace}/{repo_resolution.provider_name}:{repo_resolution.provider_version}")
    print(f"  Protocol:  {repo_resolution.binding.protocol}")
    print(f"  Server:    {repo_resolution.binding.connection.get('server', 'N/A')}")

    print(f"\n{'=' * 60}")
    print("DEMO COMPLETE")
    print("=" * 60)
    print(f"\nAll resolutions auditable. {len(trace_store.list_traces())} traces stored.")


if __name__ == "__main__":
    main()
