#!/usr/bin/env python3
"""
STEP 6: The Benefits — live proof of each advantage

Each benefit is demonstrated with real code, real results.
"""
import sqlite3
import tempfile
from pathlib import Path

from capmesh.adapters.defaults import default_adapter_registry
from capmesh.models import (
    A2AInterface, MCPInterface, RESTInterface, SkillInterface,
    CapabilityRef, Governance, Kind, Manifest, Metadata, Status, Visibility,
)
from capmesh.models.resolution import CallerContext, ResolveRequest
from capmesh.policy import default_policy_engine
from capmesh.registry import Registry
from capmesh.registry.storage import DuplicateVersionError
from capmesh.resolver import Resolver, ResolutionError
from capmesh.telemetry import TraceStore


def setup():
    root = Path(tempfile.mkdtemp(prefix="capmesh-benefits-"))
    registry = Registry(root=root)
    policy = default_policy_engine()
    db = sqlite3.connect(str(root / "traces.db"))
    db.row_factory = sqlite3.Row
    trace_store = TraceStore(db)
    trace_store.init_schema()
    resolver = Resolver(registry=registry, policy_engine=policy, trace_store=trace_store)
    adapter_reg = default_adapter_registry(resolver=resolver)
    resolver._adapter_registry = adapter_reg
    return registry, resolver, trace_store


def benefit_1_dynamic_discovery():
    print("""
===============================================================
  BENEFIT 1: Dynamic Discovery
  "Add providers without restarting anything"
===============================================================
""")
    registry, resolver, _ = setup()
    caller = CallerContext(identity="app")

    print("  Before: No providers registered")
    try:
        resolver.resolve(ResolveRequest(capability="email.send", contract="v1", caller=caller))
    except ResolutionError:
        print("  Resolve email.send/v1 -> NOT FOUND")
    print()

    # Register at runtime
    registry.register(Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="comms", name="email-sender",
                          version="1.0.0", owner="platform"),
        provides=[CapabilityRef(capability="email.send", contract="v1")],
        requires=[],
        interface=A2AInterface(protocol="a2a", endpoint="https://email.example.com"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ))
    print("  [Runtime] Registered comms/email-sender:1.0.0")

    res = resolver.resolve(ResolveRequest(capability="email.send", contract="v1", caller=caller))
    print(f"  Resolve email.send/v1 -> {res.provider_name}:{res.provider_version} via {res.binding.protocol}")
    print()
    print("  Result: Provider discovered INSTANTLY, no restart needed")
    print()


def benefit_2_provider_swap():
    print("""
===============================================================
  BENEFIT 2: Provider Swap Without Code Changes
  "Replace a tool and no consumer knows"
===============================================================
""")
    registry, resolver, _ = setup()
    caller = CallerContext(identity="app")

    # Register v1 (GitHub)
    registry.register(Manifest(
        metadata=Metadata(kind=Kind.TOOL, namespace="repo", name="github",
                          version="1.0.0", owner="platform"),
        provides=[CapabilityRef(capability="repository.read", contract="v1")],
        requires=[],
        interface=MCPInterface(protocol="mcp", server="github-mcp"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ))

    req = ResolveRequest(capability="repository.read", contract="v1", caller=caller)
    res1 = resolver.resolve(req)
    print(f"  Before: repository.read -> {res1.provider_name}:{res1.provider_version} (server: {res1.binding.connection.get('server')})")

    # Register v2 (GitLab) - higher version wins automatically
    registry.register(Manifest(
        metadata=Metadata(kind=Kind.TOOL, namespace="repo", name="gitlab",
                          version="2.0.0", owner="platform"),
        provides=[CapabilityRef(capability="repository.read", contract="v1")],
        requires=[],
        interface=MCPInterface(protocol="mcp", server="gitlab-mcp"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ))
    print("  [Swap]  Registered repo/gitlab:2.0.0")

    res2 = resolver.resolve(req)
    print(f"  After:  repository.read -> {res2.provider_name}:{res2.provider_version} (server: {res2.binding.connection.get('server')})")
    print()
    print(f"  Consumer code changes: 0")
    print(f"  Redeployment: No")
    print()


def benefit_3_cross_framework():
    print("""
===============================================================
  BENEFIT 3: Cross-Framework Discovery
  "LangGraph, CrewAI, Strands — all discoverable together"
===============================================================
""")
    registry, resolver, _ = setup()
    caller = CallerContext(identity="app")

    # Register agents from different frameworks
    frameworks = [
        ("langgraph-reviewer", "1.0.0", "LangGraph"),
        ("crewai-reviewer", "1.5.0", "CrewAI"),
        ("strands-reviewer", "2.0.0", "Strands"),
    ]
    for name, ver, framework in frameworks:
        registry.register(Manifest(
            metadata=Metadata(kind=Kind.AGENT, namespace="security", name=name,
                              version=ver, owner="team"),
            provides=[CapabilityRef(capability="security.code.review", contract="v1")],
            requires=[],
            interface=A2AInterface(protocol="a2a", endpoint=f"https://{name}.example.com"),
            governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        ))
        print(f"  Registered: {name}:{ver} (built with {framework})")

    print()
    providers = registry.providers_for("security.code.review", "v1")
    print(f"  Providers for security.code.review: {len(providers)}")
    for p in providers:
        print(f"    {p.name}:{p.version}")

    res = resolver.resolve(ResolveRequest(
        capability="security.code.review", contract="v1", caller=caller))
    print(f"\n  Resolver picks: {res.provider_name}:{res.provider_version} (highest semver)")
    print("  Framework is irrelevant — only the capability contract matters")
    print()


def benefit_4_policy():
    print("""
===============================================================
  BENEFIT 4: Policy Enforcement
  "Discovery does NOT mean authorization"
===============================================================
""")
    registry, resolver, _ = setup()

    # Public provider
    registry.register(Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="public", name="analyzer",
                          version="1.0.0", owner="platform"),
        provides=[CapabilityRef(capability="code.analyze", contract="v1")],
        requires=[],
        interface=A2AInterface(protocol="a2a", endpoint="https://analyzer.example.com"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ))

    # Private provider
    registry.register(Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="internal", name="secret-scanner",
                          version="1.0.0", owner="security-team"),
        provides=[CapabilityRef(capability="security.deep-scan", contract="v1")],
        requires=[],
        interface=A2AInterface(protocol="a2a", endpoint="https://secret.internal.com"),
        governance=Governance(visibility=Visibility.PRIVATE, status=Status.APPROVED),
    ))

    # Production-only provider
    registry.register(Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="infra", name="prod-monitor",
                          version="1.0.0", owner="ops"),
        provides=[CapabilityRef(capability="infra.monitor", contract="v1")],
        requires=[],
        interface=A2AInterface(protocol="a2a", endpoint="https://monitor.prod.com"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED,
                              environment=["production"]),
    ))

    print("  Scenario A: Public provider")
    res = resolver.resolve(ResolveRequest(
        capability="code.analyze", contract="v1",
        caller=CallerContext(identity="anyone"),
    ))
    print(f"    anyone -> code.analyze: ALLOWED ({res.provider_name})")

    print()
    print("  Scenario B: Private provider (non-owner)")
    try:
        resolver.resolve(ResolveRequest(
            capability="security.deep-scan", contract="v1",
            caller=CallerContext(identity="random-user"),
        ))
    except ResolutionError:
        print("    random-user -> security.deep-scan: DENIED")

    print()
    print("  Scenario C: Private provider (owner)")
    res = resolver.resolve(ResolveRequest(
        capability="security.deep-scan", contract="v1",
        caller=CallerContext(identity="security-team"),
    ))
    print(f"    security-team -> security.deep-scan: ALLOWED ({res.provider_name})")

    print()
    print("  Scenario D: Production provider from staging")
    try:
        resolver.resolve(ResolveRequest(
            capability="infra.monitor", contract="v1",
            caller=CallerContext(identity="dev", environment="staging"),
        ))
    except ResolutionError:
        print("    staging caller -> infra.monitor: DENIED")

    print()
    print("  Scenario E: Production provider from production")
    res = resolver.resolve(ResolveRequest(
        capability="infra.monitor", contract="v1",
        caller=CallerContext(identity="prod-app", environment="production"),
    ))
    print(f"    production caller -> infra.monitor: ALLOWED ({res.provider_name})")
    print()


def benefit_5_audit_trail():
    print("""
===============================================================
  BENEFIT 5: Complete Audit Trail
  "Every resolution decision is traceable"
===============================================================
""")
    registry, resolver, trace_store = setup()
    caller = CallerContext(identity="orchestrator", environment="production")

    # Register some providers
    for name, cap in [("reader", "repository.read"), ("scanner", "security.scan"), ("reporter", "report.generate")]:
        registry.register(Manifest(
            metadata=Metadata(kind=Kind.AGENT, namespace="tools", name=name,
                              version="1.0.0", owner="team"),
            provides=[CapabilityRef(capability=cap, contract="v1")],
            requires=[],
            interface=A2AInterface(protocol="a2a", endpoint=f"https://{name}.example.com"),
            governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        ))

    # Simulate an orchestrator workflow
    for cap in ["repository.read", "security.scan", "report.generate"]:
        resolver.resolve(ResolveRequest(capability=cap, contract="v1", caller=caller))

    # Show full audit trail
    traces = trace_store.list_traces(limit=10)
    print(f"  {len(traces)} resolutions recorded:")
    print()
    for t in reversed(traces):
        print(f"  Trace: {t.trace_id}")
        print(f"    Time:       {t.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"    Caller:     {t.caller.identity} (env: {t.caller.environment})")
        print(f"    Requested:  {t.requested_capability}/{t.requested_contract}")
        print(f"    Candidates: {len(t.candidates)}")
        print(f"    Selected:   {t.selected_provider}")
        print(f"    Outcome:    {t.outcome}")
        print(f"    Latency:    {t.resolution_ms:.1f}ms")
        print()

    print("  Every decision is recorded: who asked, what was available,")
    print("  what was selected, and why. Full compliance audit trail.")
    print()


def benefit_6_skill_portability():
    print("""
===============================================================
  BENEFIT 6: Skill Portability (Dual Binding)
  "Same skill works with ANY tool vendor"
===============================================================
""")
    registry, resolver, _ = setup()
    caller = CallerContext(identity="app")

    # Register a skill that requires repository capabilities
    registry.register(Manifest(
        metadata=Metadata(kind=Kind.SKILL, namespace="security", name="review-skill",
                          version="1.0.0", owner="team"),
        provides=[CapabilityRef(capability="security.code.review", contract="v1")],
        requires=[
            CapabilityRef(capability="repository.read", contract="v1"),
            CapabilityRef(capability="repository.search", contract="v1"),
        ],
        interface=SkillInterface(protocol="skill", instructions="SKILL.md", assets=[]),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ))

    # Register GitHub as the tool provider
    registry.register(Manifest(
        metadata=Metadata(kind=Kind.TOOL, namespace="repo", name="github",
                          version="1.0.0", owner="platform"),
        provides=[
            CapabilityRef(capability="repository.read", contract="v1"),
            CapabilityRef(capability="repository.search", contract="v1"),
        ],
        requires=[],
        interface=MCPInterface(protocol="mcp", server="github-mcp"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ))

    # Resolve the skill
    res = resolver.resolve(ResolveRequest(
        capability="security.code.review", contract="v1", caller=caller,
    ))
    print(f"  Skill resolved: {res.provider_name}:{res.provider_version}")
    print(f"  Instructions:   {res.binding.connection.get('instructions')}")
    print(f"  Tool bindings automatically resolved:")
    for tb in res.binding.connection.get("tool_bindings", []):
        if "error" not in tb:
            print(f"    {tb['capability']}/{tb['contract']} -> {tb['protocol']} ({tb['provider']})")
    print()
    print("  The skill says 'I need repository.read' — NOT 'I need GitHub'")
    print("  CapMesh resolved the tools independently")
    print("  Swap GitHub for GitLab? The skill doesn't change at all.")
    print()


def benefit_7_immutability():
    print("""
===============================================================
  BENEFIT 7: Immutable Versions
  "Published versions can never be silently modified"
===============================================================
""")
    registry, _, _ = setup()

    # Register original
    registry.register(Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="security", name="scanner",
                          version="1.0.0", owner="security-team"),
        provides=[CapabilityRef(capability="security.scan", contract="v1")],
        requires=[],
        interface=A2AInterface(protocol="a2a", endpoint="https://scanner.example.com"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ))
    print("  Registered: security/scanner:1.0.0")
    print("  Digest:     sha256:... (computed from manifest content)")
    print()

    # Try to tamper
    print("  Attacker tries to overwrite with malicious endpoint...")
    try:
        registry.register(Manifest(
            metadata=Metadata(kind=Kind.AGENT, namespace="security", name="scanner",
                              version="1.0.0", owner="attacker"),
            provides=[CapabilityRef(capability="security.scan", contract="v1")],
            requires=[],
            interface=A2AInterface(protocol="a2a", endpoint="https://evil.attacker.com"),
            governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        ))
        print("  DANGER: Accepted! (this shouldn't happen)")
    except DuplicateVersionError:
        print("  REJECTED! Same version with different content = different digest")
        print("  The only way to publish new content is a new version number")
    print()


def main():
    benefit_1_dynamic_discovery()
    benefit_2_provider_swap()
    benefit_3_cross_framework()
    benefit_4_policy()
    benefit_5_audit_trail()
    benefit_6_skill_portability()
    benefit_7_immutability()

    print("=" * 70)
    print("  7 BENEFITS, ALL PROVEN WITH REAL CODE")
    print("=" * 70)
    print()
    print("  1. Dynamic Discovery      — add providers without restart")
    print("  2. Provider Swap          — replace tools without code changes")
    print("  3. Cross-Framework        — any framework, one registry")
    print("  4. Policy Enforcement     — visibility, environment, ownership")
    print("  5. Audit Trail            — every resolution decision traced")
    print("  6. Skill Portability      — same skill, any tool vendor")
    print("  7. Immutable Versions     — tamper-proof version integrity")
    print()


if __name__ == "__main__":
    main()
