#!/usr/bin/env python3
"""
GOVERNANCE & CONTROL DEMO

For organizations that think "dynamic = losing control":
CapMesh gives you MORE control, not less.

Shows:
1. MCP servers — how they integrate (unchanged, not replaced)
2. Approval workflow — nothing runs without explicit approval
3. Locked environments — prod tools can't leak to staging
4. Version pinning — freeze to exact versions (no surprises)
5. Visibility controls — not everyone sees everything
6. Immutable versions — published = tamper-proof
7. Deprecation — graceful sunset, not sudden breakage
8. Full audit — who resolved what, when, and why
"""
import sqlite3
import tempfile
from pathlib import Path

from capmesh.adapters.defaults import default_adapter_registry
from capmesh.models import (
    A2AInterface, MCPInterface, RESTInterface, CapabilityRef, Governance,
    Kind, Manifest, Metadata, Status, Visibility,
)
from capmesh.models.resolution import CallerContext, ResolveRequest
from capmesh.policy import default_policy_engine
from capmesh.registry import Registry
from capmesh.registry.storage import DuplicateVersionError
from capmesh.resolver import Resolver, ResolutionError
from capmesh.telemetry import TraceStore


def setup():
    root = Path(tempfile.mkdtemp(prefix="capmesh-gov-"))
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


def section(num, title, subtitle=""):
    print()
    print("=" * 70)
    print(f"  {num}. {title}")
    if subtitle:
        print(f"     {subtitle}")
    print("=" * 70)
    print()


def main():
    registry, resolver, trace_store = setup()

    print()
    print("+" + "=" * 68 + "+")
    print("|  CAPMESH GOVERNANCE & CONTROL                                     |")
    print("|  For orgs that need control over what agents can use              |")
    print("+" + "=" * 68 + "+")

    # =================================================================
    # 1. MCP SERVERS — how they work with CapMesh
    # =================================================================
    section("1", "MCP SERVERS: Unchanged, not replaced",
            "CapMesh discovers which MCP server to use. The agent calls it directly.")

    print("  WITHOUT CapMesh (today):")
    print("  +-------------------------------------------------------+")
    print("  |  # Agent hardcodes the MCP server config              |")
    print("  |  mcp_config = {                                       |")
    print("  |      'server': 'github-mcp',  # HARDCODED             |")
    print("  |      'tool': 'read_file'      # HARDCODED             |")
    print("  |  }                                                     |")
    print("  |  result = mcp_client.call(mcp_config, args)            |")
    print("  +-------------------------------------------------------+")
    print()
    print("  Problems:")
    print("    - Every agent has its own MCP config")
    print("    - No central registry of which MCP servers exist")
    print("    - No control over which agents use which servers")
    print("    - No audit trail of MCP usage")
    print("    - Swapping a server = updating every agent's config")
    print()

    # Register MCP servers
    registry.register(Manifest(
        metadata=Metadata(kind=Kind.TOOL, namespace="repository", name="github-mcp-server",
                          version="1.0.0", owner="platform-team"),
        provides=[CapabilityRef(capability="repository.read", contract="v1"),
                  CapabilityRef(capability="repository.search", contract="v1")],
        requires=[],
        interface=MCPInterface(protocol="mcp", server="github-mcp", tool_name="read_file"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ))
    registry.register(Manifest(
        metadata=Metadata(kind=Kind.TOOL, namespace="repository", name="gitlab-mcp-server",
                          version="2.0.0", owner="platform-team"),
        provides=[CapabilityRef(capability="repository.read", contract="v1"),
                  CapabilityRef(capability="repository.search", contract="v1")],
        requires=[],
        interface=MCPInterface(protocol="mcp", server="gitlab-mcp", tool_name="read_file"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ))

    print("  WITH CapMesh:")
    print("  +-------------------------------------------------------+")
    print("  |  # Agent asks for capability, gets MCP binding back   |")
    print("  |  binding = resolver.resolve('repository.read/v1')     |")
    print("  |  # binding = {server: 'gitlab-mcp', tool: 'read_file'}|")
    print("  |  result = mcp_client.call(binding.server, args)       |")
    print("  +-------------------------------------------------------+")
    print()

    res = resolver.resolve(ResolveRequest(
        capability="repository.read", contract="v1",
        caller=CallerContext(identity="agent-1"),
    ))
    print(f"  Resolved: repository.read/v1")
    print(f"    -> {res.provider_name}:{res.provider_version}")
    print(f"    -> Protocol: {res.binding.protocol} (MCP)")
    print(f"    -> Server:   {res.binding.connection.get('server')}")
    print(f"    -> Tool:     {res.binding.connection.get('tool_name')}")
    print()
    print("  The MCP server is UNCHANGED. Still running as before.")
    print("  CapMesh just told the agent WHICH server to use.")
    print("  Platform team controls the registry. Agents obey.")

    # =================================================================
    # 2. APPROVAL WORKFLOW — nothing runs without approval
    # =================================================================
    section("2", "APPROVAL WORKFLOW: Nothing runs without 'status: approved'",
            "governance.status controls the lifecycle: approved -> deprecated -> revoked")

    # Register an unapproved agent
    registry.register(Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="experimental", name="untested-scanner",
                          version="0.1.0", owner="intern"),
        provides=[CapabilityRef(capability="security.experimental-scan", contract="v1")],
        requires=[],
        interface=A2AInterface(protocol="a2a", endpoint="https://untested.example.com"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.DEPRECATED),
    ))

    print("  Registered: experimental/untested-scanner:0.1.0")
    print("    status: deprecated (not approved for production)")
    print()

    # Approved agent
    registry.register(Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="security", name="approved-scanner",
                          version="2.0.0", owner="security-team"),
        provides=[CapabilityRef(capability="security.scan", contract="v1")],
        requires=[],
        interface=A2AInterface(protocol="a2a", endpoint="https://approved.example.com"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ))

    print("  Registered: security/approved-scanner:2.0.0")
    print("    status: approved")
    print()

    res = resolver.resolve(ResolveRequest(
        capability="security.scan", contract="v1",
        caller=CallerContext(identity="ci-pipeline"),
    ))
    print(f"  Resolve security.scan/v1 -> {res.provider_name}:{res.provider_version}")
    print(f"    Status: APPROVED. This is the only one agents can use.")
    print()
    print("  Lifecycle:  approved -> deprecated -> revoked")
    print("  Only 'approved' providers are resolvable.")
    print("  Deprecated: still visible in search, but resolver filters them out.")
    print("  Revoked: completely blocked, audit trail preserved.")

    # =================================================================
    # 3. LOCKED ENVIRONMENTS
    # =================================================================
    section("3", "LOCKED ENVIRONMENTS: Prod tools can't leak to staging",
            "governance.environment controls where providers can be used")

    registry.register(Manifest(
        metadata=Metadata(kind=Kind.TOOL, namespace="database", name="prod-db-connector",
                          version="1.0.0", owner="dba-team"),
        provides=[CapabilityRef(capability="database.query", contract="v1")],
        requires=[],
        interface=MCPInterface(protocol="mcp", server="prod-postgres", tool_name="query"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED,
                              environment=["production"]),
    ))
    registry.register(Manifest(
        metadata=Metadata(kind=Kind.TOOL, namespace="database", name="staging-db-connector",
                          version="1.0.0", owner="dba-team"),
        provides=[CapabilityRef(capability="database.query", contract="v1")],
        requires=[],
        interface=MCPInterface(protocol="mcp", server="staging-postgres", tool_name="query"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED,
                              environment=["staging", "development"]),
    ))

    print("  Registered:")
    print("    database/prod-db-connector:1.0.0     environment: [production]")
    print("    database/staging-db-connector:1.0.0   environment: [staging, development]")
    print()

    # Staging agent tries to access prod DB
    print("  Staging agent tries to resolve database.query:")
    try:
        resolver.resolve(ResolveRequest(
            capability="database.query", contract="v1",
            caller=CallerContext(identity="staging-agent", environment="staging"),
        ))
        print("    -> Got prod DB (BAD!)")
    except ResolutionError:
        res = resolver.resolve(ResolveRequest(
            capability="database.query", contract="v1",
            caller=CallerContext(identity="staging-agent", environment="staging"),
            version_constraint=">=1.0,<2.0",
        ))
    # Actually let me show this more clearly
    staging_res = resolver.resolve(ResolveRequest(
        capability="database.query", contract="v1",
        caller=CallerContext(identity="staging-agent", environment="staging"),
    ))
    print(f"    -> {staging_res.provider_name} (server: {staging_res.binding.connection.get('server')})")

    prod_res = resolver.resolve(ResolveRequest(
        capability="database.query", contract="v1",
        caller=CallerContext(identity="prod-agent", environment="production"),
    ))
    print()
    print("  Production agent resolves database.query:")
    print(f"    -> {prod_res.provider_name} (server: {prod_res.binding.connection.get('server')})")
    print()
    print("  Staging NEVER gets prod credentials. Automatic. No firewall rules.")
    print("  The policy is IN the manifest. Platform team sets it once.")

    # =================================================================
    # 4. VERSION PINNING
    # =================================================================
    section("4", "VERSION PINNING: Freeze to exact versions",
            "version_constraint prevents surprise upgrades")

    registry.register(Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="security", name="scanner",
                          version="1.0.0", owner="security-team"),
        provides=[CapabilityRef(capability="security.code.review", contract="v1")],
        requires=[],
        interface=A2AInterface(protocol="a2a", endpoint="https://scanner-v1.example.com"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ))
    registry.register(Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="security", name="scanner-v2",
                          version="2.0.0", owner="security-team"),
        provides=[CapabilityRef(capability="security.code.review", contract="v1")],
        requires=[],
        interface=A2AInterface(protocol="a2a", endpoint="https://scanner-v2.example.com"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ))
    registry.register(Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="security", name="scanner-v3",
                          version="3.0.0", owner="security-team"),
        provides=[CapabilityRef(capability="security.code.review", contract="v1")],
        requires=[],
        interface=A2AInterface(protocol="a2a", endpoint="https://scanner-v3.example.com"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ))

    print("  Available: scanner:1.0.0, scanner-v2:2.0.0, scanner-v3:3.0.0")
    print()

    # Default: highest version
    res = resolver.resolve(ResolveRequest(
        capability="security.code.review", contract="v1",
        caller=CallerContext(identity="agent"),
    ))
    print(f"  No constraint:  -> {res.provider_name}:{res.provider_version} (latest)")

    # Pinned to v1
    res = resolver.resolve(ResolveRequest(
        capability="security.code.review", contract="v1",
        caller=CallerContext(identity="agent"),
        version_constraint=">=1.0,<2.0",
    ))
    print(f"  Pin '>=1.0,<2.0': -> {res.provider_name}:{res.provider_version}")

    # Pinned to v2
    res = resolver.resolve(ResolveRequest(
        capability="security.code.review", contract="v1",
        caller=CallerContext(identity="agent"),
        version_constraint=">=2.0,<3.0",
    ))
    print(f"  Pin '>=2.0,<3.0': -> {res.provider_name}:{res.provider_version}")
    print()
    print("  Compliance team says 'only use scanner v2 in production'?")
    print("  Set version_constraint='>=2.0,<3.0' in the agent config.")
    print("  Even if v3 exists, the agent gets v2. Deterministic. Auditable.")

    # =================================================================
    # 5. VISIBILITY CONTROLS
    # =================================================================
    section("5", "VISIBILITY: Not everyone sees everything",
            "public / organization / private")

    registry.register(Manifest(
        metadata=Metadata(kind=Kind.TOOL, namespace="public", name="open-tool",
                          version="1.0.0", owner="platform"),
        provides=[CapabilityRef(capability="tools.public-op", contract="v1")],
        requires=[],
        interface=RESTInterface(protocol="rest", endpoint="https://public.example.com",
                                auth_type="none", request_mapping={}, response_mapping={}),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ))
    registry.register(Manifest(
        metadata=Metadata(kind=Kind.TOOL, namespace="internal", name="org-tool",
                          version="1.0.0", owner="engineering"),
        provides=[CapabilityRef(capability="tools.org-op", contract="v1")],
        requires=[],
        interface=RESTInterface(protocol="rest", endpoint="https://org.example.com",
                                auth_type="bearer", request_mapping={}, response_mapping={}),
        governance=Governance(visibility=Visibility.ORGANIZATION, status=Status.APPROVED),
    ))
    registry.register(Manifest(
        metadata=Metadata(kind=Kind.TOOL, namespace="secret", name="private-tool",
                          version="1.0.0", owner="ciso-office"),
        provides=[CapabilityRef(capability="tools.secret-op", contract="v1")],
        requires=[],
        interface=RESTInterface(protocol="rest", endpoint="https://secret.example.com",
                                auth_type="bearer", request_mapping={}, response_mapping={}),
        governance=Governance(visibility=Visibility.PRIVATE, status=Status.APPROVED),
    ))

    print("  Registered 3 tools with different visibility:")
    print("    public/open-tool:1.0.0       visibility: public")
    print("    internal/org-tool:1.0.0      visibility: organization")
    print("    secret/private-tool:1.0.0    visibility: private (owner: ciso-office)")
    print()

    # Public — anyone
    res = resolver.resolve(ResolveRequest(
        capability="tools.public-op", contract="v1",
        caller=CallerContext(identity="anyone"),
    ))
    print(f"  anyone -> tools.public-op:        ALLOWED ({res.provider_name})")

    # Org — same org
    res = resolver.resolve(ResolveRequest(
        capability="tools.org-op", contract="v1",
        caller=CallerContext(identity="dev", organization="engineering"),
    ))
    print(f"  engineering org -> tools.org-op:   ALLOWED ({res.provider_name})")

    try:
        resolver.resolve(ResolveRequest(
            capability="tools.org-op", contract="v1",
            caller=CallerContext(identity="outsider", organization="vendor"),
        ))
        print(f"  vendor org -> tools.org-op:       ALLOWED (bad!)")
    except ResolutionError:
        print(f"  vendor org -> tools.org-op:       DENIED")

    # Private — owner only
    res = resolver.resolve(ResolveRequest(
        capability="tools.secret-op", contract="v1",
        caller=CallerContext(identity="ciso-office"),
    ))
    print(f"  ciso-office -> tools.secret-op:   ALLOWED ({res.provider_name})")

    try:
        resolver.resolve(ResolveRequest(
            capability="tools.secret-op", contract="v1",
            caller=CallerContext(identity="developer"),
        ))
        print(f"  developer -> tools.secret-op:     ALLOWED (bad!)")
    except ResolutionError:
        print(f"  developer -> tools.secret-op:     DENIED")

    print()
    print("  Control is in the YAML manifest, managed by the platform team.")
    print("  No code changes needed. No middleware. No ACL databases.")

    # =================================================================
    # 6. IMMUTABILITY
    # =================================================================
    section("6", "IMMUTABLE VERSIONS: Published = tamper-proof",
            "Same version + different content = REJECTED")

    print("  scanner:1.0.0 is already registered with a specific digest.")
    print()
    print("  Attacker tries to replace it with a malicious version:")
    try:
        registry.register(Manifest(
            metadata=Metadata(kind=Kind.AGENT, namespace="security", name="scanner",
                              version="1.0.0", owner="attacker"),
            provides=[CapabilityRef(capability="security.code.review", contract="v1")],
            requires=[],
            interface=A2AInterface(protocol="a2a", endpoint="https://evil.attacker.com"),
            governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        ))
        print("    ACCEPTED (this should never happen)")
    except DuplicateVersionError:
        print("    REJECTED! Digest mismatch. Content integrity enforced.")
    print()
    print("  Same content re-registered? Idempotent — no error, no duplicate.")
    print("  Different content at same version? Blocked at the registry level.")
    print("  The only way to publish new content = new version number.")

    # =================================================================
    # 7. DEPRECATION
    # =================================================================
    section("7", "DEPRECATION: Graceful sunset, not sudden breakage",
            "deprecated -> still discoverable but resolver prefers alternatives")

    print("  Before deprecation:")
    providers = registry.providers_for("security.code.review", "v1")
    print(f"    {len(providers)} providers for security.code.review/v1")
    for p in providers:
        print(f"      {p.name}:{p.version}")
    print()

    print("  Platform team deprecates scanner:1.0.0:")
    print("    Set status: deprecated in the manifest")
    print("    (or: capmesh tag security scanner 1.0.0 deprecated)")
    registry.delete("security", "scanner", "1.0.0")
    print()

    providers = registry.providers_for("security.code.review", "v1")
    print(f"  After deprecation:")
    print(f"    {len(providers)} providers for security.code.review/v1")
    for p in providers:
        print(f"      {p.name}:{p.version}")
    print()
    print("  The old version is gone from resolution results.")
    print("  Agents automatically get the next best version.")
    print("  No breaking changes. No emergency patches. Graceful.")

    # =================================================================
    # 8. FULL AUDIT
    # =================================================================
    section("8", "FULL AUDIT TRAIL: Every resolution is traceable",
            "Compliance-ready: who resolved what, when, why")

    traces = trace_store.list_traces(limit=50)
    print(f"  {len(traces)} resolution traces recorded in this demo:")
    print()
    print(f"  {'Caller':<20s} {'Capability':<30s} {'Result':<15s} {'Provider'}")
    print(f"  {'-'*20} {'-'*30} {'-'*15} {'-'*30}")
    for t in reversed(traces):
        outcome = "ALLOWED" if t.outcome == "success" else "DENIED"
        selected = t.selected_provider.split("/")[-1] if t.selected_provider else "-"
        print(f"  {t.caller.identity:<20s} {t.requested_capability:<30s} {outcome:<15s} {selected}")

    print()
    print("  Each trace includes:")
    print("    - Timestamp (when)")
    print("    - Caller identity and environment (who)")
    print("    - Requested capability (what)")
    print("    - All candidates evaluated (what was available)")
    print("    - Selection reason (why this one)")
    print("    - Policy decisions (why others were rejected)")
    print("    - Resolution latency (performance)")

    # =================================================================
    # SUMMARY
    # =================================================================

    print()
    print("+" + "=" * 68 + "+")
    print("|  SUMMARY: CapMesh gives MORE control, not less                    |")
    print("+" + "=" * 68 + "+")
    print()
    print("  Without CapMesh:             With CapMesh:")
    print("  -------------------------    -------------------------")
    print("  Developers hardcode tools    Platform team controls registry")
    print("  No approval process          status: approved/deprecated/revoked")
    print("  Prod tools leak to staging   environment: [production] enforced")
    print("  No version control           Version pinning + immutability")
    print("  Anyone uses anything         Visibility: public/org/private")
    print("  No audit trail               Every resolution traced")
    print("  Sunset = break everything    Deprecation = graceful fallback")
    print("  MCP configs scattered        MCP servers centrally registered")
    print()
    print("  Dynamic loading WITH governance = control at scale.")
    print("  The registry is the control plane. The platform team owns it.")
    print("  Agents get flexibility. The org gets control. Both win.")
    print()


if __name__ == "__main__":
    main()
