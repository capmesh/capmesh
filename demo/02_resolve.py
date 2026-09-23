#!/usr/bin/env python3
"""
Step 2: Resolve capabilities and show CapMesh in action.

An orchestrator agent needs to do a security review. It doesn't know
which tools or agents exist — it just asks CapMesh for capabilities.

Shows: resolution, traces, dynamic discovery, provider swap, skill
dual binding, policy enforcement, and cross-framework discovery.
"""
import sqlite3
from pathlib import Path

from capmesh.adapters.defaults import default_adapter_registry
from capmesh.models import (
    A2AInterface, CapabilityRef, Governance, Kind,
    Manifest, Metadata, Status, Visibility,
)
from capmesh.models.resolution import CallerContext, ResolveRequest
from capmesh.policy import default_policy_engine
from capmesh.registry import Registry
from capmesh.resolver import Resolver, ResolutionError
from capmesh.telemetry import TraceStore

# Load the registry from Step 1
demo_root_file = Path(__file__).parent / ".demo_root"
if not demo_root_file.exists():
    print("  Run 01_register.py first!")
    raise SystemExit(1)

DEMO_ROOT = Path(demo_root_file.read_text().strip())
registry = Registry(root=DEMO_ROOT)
policy = default_policy_engine()
db = sqlite3.connect(str(DEMO_ROOT / "traces.db"))
db.row_factory = sqlite3.Row
trace_store = TraceStore(db)
trace_store.init_schema()
resolver = Resolver(registry=registry, policy_engine=policy, trace_store=trace_store)
adapter_reg = default_adapter_registry(resolver=resolver)
resolver._adapter_registry = adapter_reg


# ---- Simulated services (pretend these are real remote services) ----

class GitHubService:
    def read(self, repo):
        return {
            "files": ["app.py", "auth.py", "database.py", "config.py", "api.py"],
            "loc": 5200,
            "source": "GitHub",
        }

class GitLabService:
    def read(self, repo):
        return {
            "files": ["app.py", "auth.py", "database.py", "config.py", "api.py"],
            "loc": 5200,
            "source": "GitLab",
        }

class SecurityScanService:
    def scan(self, files):
        return [
            {"severity": "HIGH", "file": "auth.py", "issue": "Hardcoded API key on line 42"},
            {"severity": "HIGH", "file": "api.py", "issue": "Missing rate limiting on /login"},
            {"severity": "MEDIUM", "file": "database.py", "issue": "SQL built with string concat"},
            {"severity": "LOW", "file": "config.py", "issue": "Debug mode enabled"},
        ]

SERVICES = {
    "github-mcp": GitHubService(),
    "gitlab-mcp": GitLabService(),
    "https://langgraph-security.example.com": SecurityScanService(),
    "https://crewai-security.example.com": SecurityScanService(),
}

def call(binding):
    conn = binding.connection
    key = conn.get("server") or conn.get("endpoint")
    return SERVICES.get(key)


# ====================================================================

def section(title):
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)
    print()

caller = CallerContext(identity="orchestrator", environment="production")


# ---- 1. RESOLVE: Security code review ----
section("1. RESOLVE — Orchestrator asks for 'security.code.review'")

print("  The orchestrator doesn't know which agent to use.")
print("  It just says: 'I need security.code.review/v1'")
print()

res = resolver.resolve(ResolveRequest(
    capability="security.code.review", contract="v1", caller=caller,
))

print(f"  Resolved to: {res.provider_namespace}/{res.provider_name}:{res.provider_version}")
print(f"  Protocol:    {res.binding.protocol}")
print(f"  Endpoint:    {res.binding.connection.get('endpoint', 'N/A')}")
print(f"  Trace:       {res.trace.trace_id}")
print()
print(f"  Why this one? Highest semver among {len(res.trace.candidates)} candidates:")
for c in res.trace.candidates:
    icon = ">>>" if c.passed and c.version == res.provider_version else "   "
    status = "PASS" if c.passed else f"FAIL ({c.rejection_reason})"
    print(f"  {icon} {c.provider}:{c.version} [{status}]")


# ---- 2. USE IT: Call the resolved agent ----
section("2. USE IT — Call the resolved agent, get real results")

print(f"  Using {res.provider_name} to scan myorg/webapp...")
print()

# First resolve repository.read (the agent needs it)
repo_res = resolver.resolve(ResolveRequest(
    capability="repository.read", contract="v1", caller=caller,
))
repo_svc = call(repo_res.binding)
repo_data = repo_svc.read("myorg/webapp")
print(f"  Step 1: Read repo via {repo_res.provider_name} ({repo_res.binding.protocol})")
print(f"          {len(repo_data['files'])} files, {repo_data['loc']} LOC, source: {repo_data['source']}")

# Call the security scanner
scanner_svc = call(res.binding)
findings = scanner_svc.scan(repo_data["files"])
print(f"  Step 2: Scan via {res.provider_name} ({res.binding.protocol})")
print(f"          {len(findings)} findings")
print()

high = sum(1 for f in findings if f["severity"] == "HIGH")
med = sum(1 for f in findings if f["severity"] == "MEDIUM")
low = sum(1 for f in findings if f["severity"] == "LOW")

print(f"  +-----------------------------------------------------------+")
print(f"  |  SECURITY REPORT - myorg/webapp                          |")
print(f"  +-----------------------------------------------------------+")
print(f"  |  Files scanned: {len(repo_data['files']):<5}  Lines: {repo_data['loc']:<10}              |")
print(f"  |  HIGH: {high}    MEDIUM: {med}    LOW: {low}                         |")
print(f"  +-----------------------------------------------------------+")
for f in findings:
    line = f"  |  [{f['severity']:6s}] {f['file']:12s} {f['issue']}"
    print(f"{line:<62s}|")
print(f"  +-----------------------------------------------------------+")
verdict = "FAIL - fix HIGH issues before deploy" if high > 0 else "PASS"
print(f"  |  Verdict: {verdict:<49s}|")
print(f"  +-----------------------------------------------------------+")


# ---- 3. CROSS-FRAMEWORK: Show all providers ----
section("3. CROSS-FRAMEWORK — Multiple frameworks, one capability")

providers = registry.providers_for("security.code.review", "v1")
print(f"  {len(providers)} providers for security.code.review/v1:")
print()
for p in providers:
    m = registry.get(p.namespace, p.name, p.version)
    framework = m.governance.labels.get("framework", "n/a") if m else "?"
    protocol = m.interface.protocol if m else "?"
    print(f"    {p.namespace}/{p.name}:{p.version}")
    print(f"      Framework: {framework} | Protocol: {protocol}")
print()
print("  CapMesh doesn't care about frameworks — only capability contracts.")
print("  LangGraph, CrewAI, Strands agents all compete on the same contract.")


# ---- 4. DYNAMIC DISCOVERY: Add a new capability at runtime ----
section("4. DYNAMIC DISCOVERY — Add provider without restart")

print("  Before: Resolve ai.summarize/v1...")
try:
    resolver.resolve(ResolveRequest(
        capability="ai.summarize", contract="v1", caller=caller))
    print("  Found (unexpected)")
except ResolutionError:
    print("  Result: NOT FOUND (no provider registered)")

print()
print("  [Register a new agent at runtime — no restart, no redeploy]")
registry.register(Manifest(
    metadata=Metadata(kind=Kind.AGENT, namespace="ai", name="summarizer",
                      version="1.0.0", owner="ai-team"),
    provides=[CapabilityRef(capability="ai.summarize", contract="v1")],
    requires=[],
    interface=A2AInterface(protocol="a2a", endpoint="https://summarizer.example.com"),
    governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
))
print("  Registered: ai/summarizer:1.0.0")
print()

print("  After: Resolve ai.summarize/v1...")
res2 = resolver.resolve(ResolveRequest(
    capability="ai.summarize", contract="v1", caller=caller))
print(f"  Result: {res2.provider_namespace}/{res2.provider_name}:{res2.provider_version}")
print(f"  The orchestrator discovered it INSTANTLY. No code changes.")


# ---- 5. PROVIDER SWAP: Replace GitHub with GitLab ----
section("5. PROVIDER SWAP — Replace tool, zero code changes")

print(f"  Current: repository.read resolves to {repo_res.provider_name}:{repo_res.provider_version}")
print(f"           Server: {repo_res.binding.connection.get('server')}")
print()

# GitLab was already registered in Step 1 (version 2.0.0 > 1.0.0)
# But let's show the swap explicitly
repo_res2 = resolver.resolve(ResolveRequest(
    capability="repository.read", contract="v1", caller=caller))

if repo_res2.provider_name != repo_res.provider_name:
    print(f"  After:   repository.read resolves to {repo_res2.provider_name}:{repo_res2.provider_version}")
    print(f"           Server: {repo_res2.binding.connection.get('server')}")
    print()
    # Use the new provider
    new_svc = call(repo_res2.binding)
    new_data = new_svc.read("myorg/webapp")
    print(f"  Same data, different backend: source={new_data['source']}")
else:
    print(f"  Still using: {repo_res2.provider_name}:{repo_res2.provider_version}")

print()
print(f"  Orchestrator code changed: NOTHING")
print(f"  Redeployment needed: NO")
print(f"  Downtime: ZERO")


# ---- 6. SKILL DUAL BINDING ----
section("6. SKILL DUAL BINDING — Skill resolves its own tool deps")

print("  The security-code-review-skill requires repository.read and")
print("  repository.search, but doesn't name specific tools.")
print()

skill_res = resolver.resolve(ResolveRequest(
    capability="security.code.review", contract="v1", caller=caller,
    version_constraint=">=1.0,<2.0",  # force skill selection (v1.2.0)
))

print(f"  Resolved:     {skill_res.provider_namespace}/{skill_res.provider_name}:{skill_res.provider_version}")
print(f"  Protocol:     {skill_res.binding.protocol}")
print(f"  Instructions: {skill_res.binding.connection.get('instructions')}")
print()
print(f"  Tool bindings (resolved automatically by CapMesh):")
for tb in skill_res.binding.connection.get("tool_bindings", []):
    if "error" not in tb:
        print(f"    {tb['capability']}/{tb['contract']} -> {tb['protocol']} via {tb['provider']}")
    else:
        print(f"    {tb['capability']}/{tb['contract']} -> UNRESOLVED")
print()
print("  The skill said 'I need repository.read' — CapMesh figured out WHO provides it.")
print("  Swap GitHub for GitLab? The skill YAML never changes.")


# ---- 7. POLICY ENFORCEMENT ----
section("7. POLICY — Discovery does NOT mean authorization")

# Register a private provider
registry.register(Manifest(
    metadata=Metadata(kind=Kind.AGENT, namespace="internal", name="secret-scanner",
                      version="1.0.0", owner="security-team"),
    provides=[CapabilityRef(capability="internal.deep-scan", contract="v1")],
    requires=[],
    interface=A2AInterface(protocol="a2a", endpoint="https://internal.secret.com"),
    governance=Governance(visibility=Visibility.PRIVATE, status=Status.APPROVED),
))

print("  Registered: internal/secret-scanner:1.0.0 (PRIVATE, owner=security-team)")
print()

print("  random-user tries to resolve internal.deep-scan:")
try:
    resolver.resolve(ResolveRequest(
        capability="internal.deep-scan", contract="v1",
        caller=CallerContext(identity="random-user")))
    print("    ALLOWED (bad!)")
except ResolutionError:
    print("    DENIED — visibility policy blocked it")

print()
print("  security-team (owner) tries to resolve:")
r = resolver.resolve(ResolveRequest(
    capability="internal.deep-scan", contract="v1",
    caller=CallerContext(identity="security-team")))
print(f"    ALLOWED -> {r.provider_name}:{r.provider_version}")

print()
print("  staging caller tries production-only agent:")
try:
    resolver.resolve(ResolveRequest(
        capability="security.code.review", contract="v1",
        caller=CallerContext(identity="dev", environment="staging"),
        version_constraint=">=3.0",  # crewai-reviewer is prod-only
    ))
    print("    ALLOWED")
except ResolutionError:
    print("    DENIED — environment policy: staging can't access production-only providers")


# ---- 8. AUDIT TRAIL ----
section("8. AUDIT TRAIL — Every resolution is traceable")

traces = trace_store.list_traces(limit=20)
print(f"  {len(traces)} resolutions recorded in this session:")
print()
print(f"  {'TRACE ID':<22s} {'CAPABILITY':<30s} {'SELECTED':<35s} {'TIME':>6s}")
print(f"  {'-' * 22} {'-' * 30} {'-' * 35} {'-' * 6}")
for t in reversed(traces):
    selected = t.selected_provider or "NONE"
    print(f"  {t.trace_id:<22s} {t.requested_capability:<30s} {selected:<35s} {t.resolution_ms:>5.0f}ms")

print()
print("  Every decision: who asked, what was available, what was")
print("  selected, and why. Queryable via CLI or API.")
print("  $ capmesh resolve security.code.review --trace")


# ---- SUMMARY ----
section("SUMMARY")

print("  What just happened:")
print()
print("  1. Loaded 7 providers from YAML files (3 tools, 3 agents, 1 skill)")
print("  2. Orchestrator resolved capabilities — never named a specific tool")
print("  3. Got real scan results: 4 findings, 2 HIGH severity")
print("  4. Multiple frameworks (LangGraph, CrewAI, Strands) — same registry")
print("  5. Added a new capability at runtime — no restart")
print("  6. Swapped GitHub for GitLab — zero code changes")
print("  7. Skill auto-resolved its tool dependencies (dual binding)")
print("  8. Private provider blocked for unauthorized callers")
print(f"  9. {len(traces)} resolution traces recorded for audit")
print()
print("  The orchestrator code never imported a single tool or framework.")
print("  It asked for WHAT it needed. CapMesh found WHO provides it.")
print()
