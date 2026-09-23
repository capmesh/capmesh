#!/usr/bin/env python3
"""CapMesh — Full Live Action Demo"""
import sqlite3
import tempfile
from pathlib import Path

from capmesh.adapters.defaults import default_adapter_registry
from capmesh.models import (
    A2AInterface, CapabilityRef, Governance, Kind, Manifest, Metadata,
    Status, Visibility,
)
from capmesh.models.resolution import CallerContext, ResolveRequest
from capmesh.models.serialization import manifest_from_yaml
from capmesh.policy import default_policy_engine
from capmesh.registry import Registry
from capmesh.registry.storage import DuplicateVersionError
from capmesh.resolver import Resolver, ResolutionError
from capmesh.telemetry import TraceStore


def main():
    root = Path(tempfile.mkdtemp(prefix="capmesh-action-"))

    print("=" * 70)
    print("  CAPMESH — LIVE ACTION DEMO")
    print("  Service discovery for the agentic world")
    print("=" * 70)

    # Setup
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

    # [1] REGISTER
    print()
    print("[1] REGISTER - Load 5 providers from example manifests")
    print("-" * 70)

    example_files = [
        ("security-agent/manifest.yaml", "A2A"),
        ("github-tool/manifest.yaml", "MCP"),
        ("security-review-skill/manifest.yaml", "Skill"),
        ("performance-agent/manifest.yaml", "A2A"),
        ("rest-analyzer/manifest.yaml", "REST"),
    ]
    for path, protocol in example_files:
        m = manifest_from_yaml((examples_dir / path).read_text())
        digest = registry.register(m)
        caps = ", ".join(c.capability for c in m.provides)
        print(f"  + {m.metadata.namespace}/{m.metadata.name}:{m.metadata.version}")
        print(f"    Protocol: {protocol} | Provides: {caps}")
        print(f"    Digest: sha256:{digest[:16]}...")
        print()

    # [2] SEARCH
    print("[2] SEARCH - Find all security-related providers")
    print("-" * 70)
    results = registry.search("security")
    for r in results:
        print(f"  {r.namespace}/{r.name}:{r.version} ({r.kind.value})")
    print()

    # [3] RESOLVE
    print("[3] RESOLVE - Ask for security.code.review capability")
    print("-" * 70)
    req = ResolveRequest(
        capability="security.code.review",
        contract="v1",
        caller=CallerContext(identity="my-orchestrator", environment="production"),
    )
    res = resolver.resolve(req)
    print(f"  Capability:  security.code.review/v1")
    print(f"  Selected:    {res.provider_namespace}/{res.provider_name}:{res.provider_version}")
    print(f"  Protocol:    {res.binding.protocol}")
    print(f"  Endpoint:    {res.binding.connection.get('endpoint', 'N/A')}")
    print(f"  Trace ID:    {res.trace.trace_id}")
    print(f"  Resolved in: {res.trace.resolution_ms:.1f} ms")
    print()

    # [4] TRACE
    print("[4] TRACE - Full audit trail of the resolution decision")
    print("-" * 70)
    trace = trace_store.get_trace(res.trace.trace_id)
    print(f"  Requested: {trace.requested_capability}/{trace.requested_contract}")
    print(f"  Caller:    {trace.caller.identity} (env: {trace.caller.environment})")
    print(f"  Candidates evaluated: {len(trace.candidates)}")
    for c in trace.candidates:
        icon = "PASS" if c.passed else "FAIL"
        reason = f" ({c.rejection_reason})" if c.rejection_reason else ""
        print(f"    [{icon}] {c.provider}:{c.version}{reason}")
    print(f"  Winner:    {trace.selected_provider}")
    print(f"  Outcome:   {trace.outcome}")
    print()

    # [5] ALL PROTOCOLS
    print("[5] RESOLVE ALL PROTOCOLS - One resolver, four protocols")
    print("-" * 70)
    capabilities = [
        ("security.code.review", "v1"),
        ("repository.read", "v1"),
        ("performance.analyze", "v1"),
        ("code.analyze", "v1"),
    ]
    for cap, contract in capabilities:
        r = resolver.resolve(ResolveRequest(
            capability=cap, contract=contract,
            caller=CallerContext(identity="orchestrator"),
        ))
        conn = r.binding.connection
        detail = conn.get("endpoint") or conn.get("server") or "N/A"
        print(f"  {cap:30s} -> {r.binding.protocol:5s} | {r.provider_namespace}/{r.provider_name}:{r.provider_version} | {detail}")
    print()

    # [6] DYNAMIC DISCOVERY
    print("[6] DYNAMIC DISCOVERY - Add a new provider WITHOUT restart")
    print("-" * 70)
    print("  Before: Resolving ai.summarize/v1...")
    try:
        resolver.resolve(ResolveRequest(
            capability="ai.summarize", contract="v1",
            caller=CallerContext(identity="test"),
        ))
        print("  Found!")
    except ResolutionError:
        print("  No provider found (expected)")

    new_agent = Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="ai", name="summarizer", version="1.0.0", owner="ai-team"),
        provides=[CapabilityRef(capability="ai.summarize", contract="v1")],
        requires=[],
        interface=A2AInterface(protocol="a2a", endpoint="https://summarizer.example.com"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )
    registry.register(new_agent)
    print("  Registered: ai/summarizer:1.0.0")
    print("  After:  Resolving ai.summarize/v1...")
    r = resolver.resolve(ResolveRequest(
        capability="ai.summarize", contract="v1",
        caller=CallerContext(identity="test"),
    ))
    print(f"  Found: {r.provider_namespace}/{r.provider_name}:{r.provider_version} via {r.binding.protocol}")
    print("  No restart, no config change, no redeployment!")
    print()

    # [7] PROVIDER SWAP
    print("[7] PROVIDER SWAP - Higher version auto-selected")
    print("-" * 70)
    print(f"  Current best for security.code.review: {res.provider_name}:{res.provider_version}")
    new_reviewer = Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="security", name="reviewer-next", version="3.0.0", owner="security-engineering"),
        provides=[CapabilityRef(capability="security.code.review", contract="v1")],
        requires=[],
        interface=A2AInterface(protocol="a2a", endpoint="https://reviewer-v3.example.com"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )
    registry.register(new_reviewer)
    print("  Registered: security/reviewer-next:3.0.0")
    res2 = resolver.resolve(req)
    print(f"  New best:   {res2.provider_name}:{res2.provider_version}")
    print(f"  Endpoint:   {res2.binding.connection['endpoint']}")
    print("  Consumer code: ZERO changes!")
    print()

    # [8] SKILL DUAL BINDING
    print("[8] SKILL DUAL BINDING - Skill + resolved tool dependencies")
    print("-" * 70)
    skill_req = ResolveRequest(
        capability="security.code.review", contract="v1",
        caller=CallerContext(identity="orchestrator"),
        version_constraint=">=1.0,<2.0",
    )
    skill_res = resolver.resolve(skill_req)
    print(f"  Resolved:     {skill_res.provider_namespace}/{skill_res.provider_name}:{skill_res.provider_version}")
    print(f"  Protocol:     {skill_res.binding.protocol}")
    print(f"  Instructions: {skill_res.binding.connection.get('instructions', 'N/A')}")
    tool_bindings = skill_res.binding.connection.get("tool_bindings", [])
    print(f"  Tool bindings resolved: {len(tool_bindings)}")
    for tb in tool_bindings:
        if "error" not in tb:
            print(f"    {tb['capability']}/{tb['contract']} -> {tb['protocol']} ({tb['provider']})")
        else:
            print(f"    {tb['capability']}/{tb['contract']} -> {tb['error']}")
    print()

    # [9] POLICY ENFORCEMENT
    print("[9] POLICY ENFORCEMENT - Private provider denied")
    print("-" * 70)
    private_agent = Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="internal", name="secret-scanner", version="1.0.0", owner="security-team"),
        provides=[CapabilityRef(capability="internal.scan", contract="v1")],
        requires=[],
        interface=A2AInterface(protocol="a2a", endpoint="https://internal.example.com"),
        governance=Governance(visibility=Visibility.PRIVATE, status=Status.APPROVED),
    )
    registry.register(private_agent)
    print("  Registered: internal/secret-scanner:1.0.0 (PRIVATE)")
    try:
        resolver.resolve(ResolveRequest(
            capability="internal.scan", contract="v1",
            caller=CallerContext(identity="random-user"),
        ))
        print("  As random-user: ALLOWED (unexpected)")
    except ResolutionError:
        print("  As random-user: DENIED (policy: visibility)")

    r = resolver.resolve(ResolveRequest(
        capability="internal.scan", contract="v1",
        caller=CallerContext(identity="security-team"),
    ))
    print(f"  As owner (security-team): ALLOWED -> {r.provider_name}:{r.provider_version}")
    print()

    # [10] IMMUTABILITY
    print("[10] IMMUTABILITY - Same version, different content = REJECTED")
    print("-" * 70)
    try:
        tampered = Manifest(
            metadata=Metadata(kind=Kind.AGENT, namespace="security", name="security-reviewer", version="2.4.0", owner="attacker"),
            provides=[CapabilityRef(capability="security.code.review", contract="v1")],
            requires=[],
            interface=A2AInterface(protocol="a2a", endpoint="https://evil.example.com"),
            governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        )
        registry.register(tampered)
        print("  Result: Accepted (BAD!)")
    except DuplicateVersionError as e:
        print(f"  Tried:  security/security-reviewer:2.4.0 with different content")
        print(f"  Result: REJECTED - {e}")
    print()

    # Summary
    all_traces = trace_store.list_traces(limit=100)
    all_artifacts = registry.list()
    print("=" * 70)
    print(f"  SUMMARY: {len(all_artifacts)} providers registered, {len(all_traces)} resolutions traced")
    print(f"  All resolutions fully auditable. Zero consumer code changes.")
    print("=" * 70)


if __name__ == "__main__":
    main()
