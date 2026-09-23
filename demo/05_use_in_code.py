#!/usr/bin/env python3
"""
STEP 5: How to use CapMesh in your code

This shows a real orchestrator agent using CapMesh to discover, resolve,
and bind to providers — then perform actual work with results.
"""
import sqlite3
import tempfile
from pathlib import Path

print("""
===============================================================
  STEP 5: Using CapMesh in Code (with real results)
===============================================================
""")

# ---- Setup (would be done once at app startup) ----
from capmesh.adapters.defaults import default_adapter_registry
from capmesh.models import (
    A2AInterface, MCPInterface, CapabilityRef, Governance, Kind,
    Manifest, Metadata, Status, Visibility,
)
from capmesh.models.resolution import CallerContext, ResolveRequest
from capmesh.policy import default_policy_engine
from capmesh.registry import Registry
from capmesh.resolver import Resolver, ResolutionError
from capmesh.telemetry import TraceStore

root = Path(tempfile.mkdtemp(prefix="capmesh-code-"))
registry = Registry(root=root)
policy = default_policy_engine()
db = sqlite3.connect(str(root / "traces.db"))
db.row_factory = sqlite3.Row
trace_store = TraceStore(db)
trace_store.init_schema()
resolver = Resolver(registry=registry, policy_engine=policy, trace_store=trace_store)
adapter_reg = default_adapter_registry(resolver=resolver)
resolver._adapter_registry = adapter_reg

# ---- Simulated real services ----
class GitHubService:
    def read(self, repo):
        return {"files": ["app.py", "auth.py", "db.py", "config.py"], "loc": 4200}

class SecurityScanService:
    def scan(self, files):
        return {
            "findings": [
                {"severity": "HIGH", "file": "auth.py", "issue": "Hardcoded API key"},
                {"severity": "MEDIUM", "file": "db.py", "issue": "SQL injection risk"},
                {"severity": "LOW", "file": "config.py", "issue": "Debug mode enabled"},
            ]
        }

class ReportService:
    def generate(self, findings, repo_info):
        high = sum(1 for f in findings if f["severity"] == "HIGH")
        med = sum(1 for f in findings if f["severity"] == "MEDIUM")
        low = sum(1 for f in findings if f["severity"] == "LOW")
        return {
            "summary": f"Scanned {repo_info['loc']} lines across {len(repo_info['files'])} files",
            "high": high, "medium": med, "low": low,
            "verdict": "FAIL" if high > 0 else "PASS",
            "findings": findings,
        }

# Map endpoints to simulated services
SERVICES = {
    "github-mcp": GitHubService(),
    "https://scanner.example.com": SecurityScanService(),
    "https://reporter.example.com": ReportService(),
}

def call_service(binding):
    """Use a resolved binding to call the actual service."""
    conn = binding.connection
    key = conn.get("server") or conn.get("endpoint")
    return SERVICES.get(key)

# ---- Register providers (platform team does this) ----
print("  [SETUP] Platform team registers providers")
print("  " + "-" * 55)

registry.register(Manifest(
    metadata=Metadata(kind=Kind.TOOL, namespace="repo", name="github",
                      version="1.0.0", owner="platform"),
    provides=[CapabilityRef(capability="repository.read", contract="v1")],
    requires=[],
    interface=MCPInterface(protocol="mcp", server="github-mcp", tool_name="read"),
    governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
))
print("  + repo/github:1.0.0 (MCP) -> repository.read/v1")

registry.register(Manifest(
    metadata=Metadata(kind=Kind.AGENT, namespace="security", name="scanner",
                      version="3.1.0", owner="security-team"),
    provides=[CapabilityRef(capability="security.scan", contract="v1")],
    requires=[],
    interface=A2AInterface(protocol="a2a", endpoint="https://scanner.example.com"),
    governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
))
print("  + security/scanner:3.1.0 (A2A) -> security.scan/v1")

registry.register(Manifest(
    metadata=Metadata(kind=Kind.AGENT, namespace="reporting", name="reporter",
                      version="2.0.0", owner="platform"),
    provides=[CapabilityRef(capability="report.generate", contract="v1")],
    requires=[],
    interface=A2AInterface(protocol="a2a", endpoint="https://reporter.example.com"),
    governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
))
print("  + reporting/reporter:2.0.0 (A2A) -> report.generate/v1")
print()

# ====================================================================
# THIS IS YOUR ORCHESTRATOR CODE
# Notice: NO imports of GitHub, Scanner, or Reporter
# Only CapMesh resolver + capability names
# ====================================================================

print("  [ORCHESTRATOR] Your application code")
print("  " + "=" * 55)
print()
print("  # Your code only knows CAPABILITY NAMES, not tools:")
print('  repo     = resolver.resolve("repository.read/v1")')
print('  scanner  = resolver.resolve("security.scan/v1")')
print('  reporter = resolver.resolve("report.generate/v1")')
print()

caller = CallerContext(identity="my-app", environment="production")

# Step 1: Resolve and call repository.read
print("  Step 1: Read repository")
print("  " + "-" * 55)
repo_resolution = resolver.resolve(ResolveRequest(
    capability="repository.read", contract="v1", caller=caller,
))
print(f"  Resolved to: {repo_resolution.provider_namespace}/{repo_resolution.provider_name}:{repo_resolution.provider_version}")
print(f"  Protocol:    {repo_resolution.binding.protocol}")
print(f"  Server:      {repo_resolution.binding.connection.get('server')}")

repo_service = call_service(repo_resolution.binding)
repo_data = repo_service.read("myorg/webapp")
print(f"  Result:      {len(repo_data['files'])} files, {repo_data['loc']} lines of code")
print()

# Step 2: Resolve and call security.scan
print("  Step 2: Security scan")
print("  " + "-" * 55)
scan_resolution = resolver.resolve(ResolveRequest(
    capability="security.scan", contract="v1", caller=caller,
))
print(f"  Resolved to: {scan_resolution.provider_namespace}/{scan_resolution.provider_name}:{scan_resolution.provider_version}")
print(f"  Protocol:    {scan_resolution.binding.protocol}")
print(f"  Endpoint:    {scan_resolution.binding.connection.get('endpoint')}")

scan_service = call_service(scan_resolution.binding)
scan_data = scan_service.scan(repo_data["files"])
print(f"  Result:      {len(scan_data['findings'])} findings")
for f in scan_data["findings"]:
    print(f"               [{f['severity']:6s}] {f['file']}: {f['issue']}")
print()

# Step 3: Resolve and call report.generate
print("  Step 3: Generate report")
print("  " + "-" * 55)
report_resolution = resolver.resolve(ResolveRequest(
    capability="report.generate", contract="v1", caller=caller,
))
print(f"  Resolved to: {report_resolution.provider_namespace}/{report_resolution.provider_name}:{report_resolution.provider_version}")
print(f"  Protocol:    {report_resolution.binding.protocol}")

report_service = call_service(report_resolution.binding)
report = report_service.generate(scan_data["findings"], repo_data)
print()
print("  " + "=" * 55)
print("  FINAL REPORT")
print("  " + "=" * 55)
print(f"  Summary:  {report['summary']}")
print(f"  HIGH:     {report['high']}")
print(f"  MEDIUM:   {report['medium']}")
print(f"  LOW:      {report['low']}")
print(f"  Verdict:  {report['verdict']}")
print()
print("  Findings:")
for f in report["findings"]:
    print(f"    [{f['severity']:6s}] {f['file']}: {f['issue']}")
print()

# Show the full audit trail
print("  [AUDIT] Complete resolution trace")
print("  " + "-" * 55)
traces = trace_store.list_traces(limit=10)
for t in reversed(traces):
    candidates = len(t.candidates)
    print(f"  {t.trace_id} | {t.requested_capability:25s} -> {t.selected_provider:35s} | {candidates} candidates | {t.resolution_ms:.0f}ms")
print()
