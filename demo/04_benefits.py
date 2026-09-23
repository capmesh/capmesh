#!/usr/bin/env python3
"""
Step 4: True Benefits — same task, two ways, then change everything.

Scenario: Your company needs to review code for security vulnerabilities.

Part A: WITHOUT CapMesh — hardcoded tools
Part B: WITH CapMesh — capability-driven
Part C: Now change the requirements — watch what breaks vs what doesn't
"""
import sqlite3
import tempfile
from pathlib import Path

# =====================================================================
# Simulated services — these represent REAL tools/agents your org uses
# =====================================================================

class GitHubRepo:
    """Your GitHub MCP tool."""
    name = "GitHub"
    def read(self, repo):
        return {
            "files": [
                {"path": "auth.py", "content": "API_KEY = 'sk-hardcoded-key-123'\ndef login(user, pwd):\n  ..."},
                {"path": "db.py", "content": "def query(table, where):\n  sql = f'SELECT * FROM {table} WHERE ' + where"},
                {"path": "config.py", "content": "DEBUG = True\nALLOWED_HOSTS = ['*']"},
                {"path": "api.py", "content": "# No rate limiting\n@app.post('/login')\ndef login(): ..."},
            ],
            "source": self.name,
        }

class GitLabRepo:
    """Your GitLab MCP tool — same interface, different backend."""
    name = "GitLab"
    def read(self, repo):
        return {
            "files": [
                {"path": "auth.py", "content": "API_KEY = 'sk-hardcoded-key-123'\ndef login(user, pwd):\n  ..."},
                {"path": "db.py", "content": "def query(table, where):\n  sql = f'SELECT * FROM {table} WHERE ' + where"},
                {"path": "config.py", "content": "DEBUG = True\nALLOWED_HOSTS = ['*']"},
                {"path": "api.py", "content": "# No rate limiting\n@app.post('/login')\ndef login(): ..."},
            ],
            "source": self.name,
        }

class SnykScanner:
    """Security scanner v1 — finds basic issues."""
    name = "Snyk Scanner v1"
    def scan(self, files):
        return [
            {"severity": "HIGH", "file": "auth.py", "line": 1, "issue": "Hardcoded API key", "cwe": "CWE-798"},
            {"severity": "MEDIUM", "file": "db.py", "line": 2, "issue": "SQL injection via string concatenation", "cwe": "CWE-89"},
            {"severity": "LOW", "file": "config.py", "line": 1, "issue": "Debug mode enabled in production", "cwe": "CWE-489"},
        ]

class SemgrepScanner:
    """Security scanner v2 — finds MORE issues (better tool)."""
    name = "Semgrep Scanner v2"
    def scan(self, files):
        return [
            {"severity": "CRITICAL", "file": "auth.py", "line": 1, "issue": "Hardcoded API key exposed in source", "cwe": "CWE-798"},
            {"severity": "HIGH", "file": "api.py", "line": 2, "issue": "No rate limiting on authentication endpoint", "cwe": "CWE-307"},
            {"severity": "HIGH", "file": "db.py", "line": 2, "issue": "SQL injection via f-string interpolation", "cwe": "CWE-89"},
            {"severity": "MEDIUM", "file": "config.py", "line": 1, "issue": "Debug mode enabled", "cwe": "CWE-489"},
            {"severity": "MEDIUM", "file": "config.py", "line": 2, "issue": "Wildcard ALLOWED_HOSTS permits any origin", "cwe": "CWE-942"},
        ]


def print_report(findings, source, scanner_name):
    """Print a security report from scan findings."""
    critical = sum(1 for f in findings if f["severity"] == "CRITICAL")
    high = sum(1 for f in findings if f["severity"] == "HIGH")
    medium = sum(1 for f in findings if f["severity"] == "MEDIUM")
    low = sum(1 for f in findings if f["severity"] == "LOW")

    print(f"    Source:   {source}")
    print(f"    Scanner: {scanner_name}")
    print(f"    Findings: {len(findings)} total")
    print(f"      CRITICAL: {critical}  HIGH: {high}  MEDIUM: {medium}  LOW: {low}")
    print()
    for f in findings:
        print(f"      [{f['severity']:8s}] {f['file']}:{f['line']} - {f['issue']}")
        print(f"               {f['cwe']}")
    print()
    if critical > 0:
        verdict = "BLOCK DEPLOY - critical vulnerabilities found"
    elif high > 0:
        verdict = "FAIL - fix high severity issues before deploy"
    else:
        verdict = "PASS"
    print(f"    Verdict: {verdict}")
    return verdict


# =====================================================================
# PART A: WITHOUT CAPMESH
# =====================================================================

def part_a():
    print()
    print("=" * 70)
    print("  PART A: WITHOUT CapMesh")
    print("  (How most teams do it today)")
    print("=" * 70)
    print()

    print("  Your orchestrator code:")
    print("  " + "-" * 60)
    print("    from tools.github import GitHubRepo      # HARDCODED")
    print("    from tools.snyk import SnykScanner        # HARDCODED")
    print()
    print("    repo = GitHubRepo()                       # HARDCODED")
    print("    scanner = SnykScanner()                   # HARDCODED")
    print("    files = repo.read('myorg/webapp')")
    print("    findings = scanner.scan(files)")
    print()

    repo = GitHubRepo()
    scanner = SnykScanner()

    files = repo.read("myorg/webapp")
    findings = scanner.scan(files["files"])

    print("  Results:")
    print("  " + "-" * 60)
    verdict_a = print_report(findings, files["source"], scanner.name)

    return verdict_a, len(findings)


# =====================================================================
# PART B: WITH CAPMESH
# =====================================================================

def part_b():
    from capmesh.adapters.defaults import default_adapter_registry
    from capmesh.models import (
        A2AInterface, MCPInterface, CapabilityRef, Governance, Kind,
        Manifest, Metadata, Status, Visibility,
    )
    from capmesh.models.resolution import CallerContext, ResolveRequest
    from capmesh.policy import default_policy_engine
    from capmesh.registry import Registry
    from capmesh.resolver import Resolver
    from capmesh.telemetry import TraceStore

    print()
    print("=" * 70)
    print("  PART B: WITH CapMesh")
    print("  (Same task, capability-driven)")
    print("=" * 70)
    print()

    # Setup
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

    # Service lookup (in production this would be A2A/MCP protocol calls)
    services = {
        "github-mcp": GitHubRepo(),
        "gitlab-mcp": GitLabRepo(),
        "https://snyk.example.com": SnykScanner(),
        "https://semgrep.example.com": SemgrepScanner(),
    }
    def get_service(binding):
        conn = binding.connection
        return services.get(conn.get("server") or conn.get("endpoint"))

    # Register the SAME providers as Part A
    registry.register(Manifest(
        metadata=Metadata(kind=Kind.TOOL, namespace="repo", name="github-reader",
                          version="1.0.0", owner="platform"),
        provides=[CapabilityRef(capability="repository.read", contract="v1")],
        requires=[],
        interface=MCPInterface(protocol="mcp", server="github-mcp", tool_name="read"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ))
    registry.register(Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="security", name="snyk-scanner",
                          version="1.0.0", owner="security-team"),
        provides=[CapabilityRef(capability="security.scan", contract="v1")],
        requires=[],
        interface=A2AInterface(protocol="a2a", endpoint="https://snyk.example.com"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ))

    print("  Your orchestrator code:")
    print("  " + "-" * 60)
    print("    repo     = resolver.resolve('repository.read/v1')")
    print("    scanner  = resolver.resolve('security.scan/v1')")
    print("    files    = call(repo_binding, 'myorg/webapp')")
    print("    findings = call(scanner_binding, files)")
    print()
    print("    # NO imports. NO hardcoded tool names. Just capabilities.")
    print()

    caller = CallerContext(identity="ci-pipeline", environment="production")

    repo_res = resolver.resolve(ResolveRequest(
        capability="repository.read", contract="v1", caller=caller))
    scan_res = resolver.resolve(ResolveRequest(
        capability="security.scan", contract="v1", caller=caller))

    repo_svc = get_service(repo_res.binding)
    scan_svc = get_service(scan_res.binding)

    files = repo_svc.read("myorg/webapp")
    findings = scan_svc.scan(files["files"])

    print(f"  Resolved: repository.read -> {repo_res.provider_name}:{repo_res.provider_version}")
    print(f"  Resolved: security.scan   -> {scan_res.provider_name}:{scan_res.provider_version}")
    print()
    print("  Results:")
    print("  " + "-" * 60)
    verdict_b1 = print_report(findings, files["source"], scan_svc.name)

    # ---- NOW: Part C happens inside Part B ----

    print()
    print("=" * 70)
    print("  PART C: Requirements change — watch what happens")
    print("=" * 70)

    # ---- Change 1: Swap GitHub for GitLab ----
    print()
    print("  CHANGE 1: Company migrates from GitHub to GitLab")
    print("  " + "-" * 60)
    print()
    print("  WITHOUT CapMesh:")
    print("    1. Find every file importing GitHubRepo")
    print("    2. Change imports to GitLabRepo")
    print("    3. Update all instantiation code")
    print("    4. Update config files")
    print("    5. Update tests")
    print("    6. PR review")
    print("    7. Deploy all affected services")
    print("    8. Estimated: 2-3 days across 5 repos")
    print()
    print("  WITH CapMesh:")

    registry.register(Manifest(
        metadata=Metadata(kind=Kind.TOOL, namespace="repo", name="gitlab-reader",
                          version="2.0.0", owner="platform"),
        provides=[CapabilityRef(capability="repository.read", contract="v1")],
        requires=[],
        interface=MCPInterface(protocol="mcp", server="gitlab-mcp", tool_name="read"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ))
    print("    1. Register gitlab-reader:2.0.0 (one command)")
    print("    2. Done.")
    print()

    # Re-resolve — SAME orchestrator code
    repo_res2 = resolver.resolve(ResolveRequest(
        capability="repository.read", contract="v1", caller=caller))
    repo_svc2 = get_service(repo_res2.binding)
    files2 = repo_svc2.read("myorg/webapp")

    print(f"    Before: {repo_res.provider_name}:{repo_res.provider_version} (server: {repo_res.binding.connection.get('server')})")
    print(f"    After:  {repo_res2.provider_name}:{repo_res2.provider_version} (server: {repo_res2.binding.connection.get('server')})")
    print(f"    Source confirmed: {files2['source']}")
    print(f"    Orchestrator code changed: 0 lines")
    print(f"    Services redeployed: 0")
    print(f"    Time: 30 seconds")

    # ---- Change 2: Upgrade scanner ----
    print()
    print()
    print("  CHANGE 2: Upgrade from Snyk to Semgrep (finds more issues)")
    print("  " + "-" * 60)
    print()
    print("  WITHOUT CapMesh:")
    print("    1. Replace snyk SDK with semgrep SDK in requirements")
    print("    2. Rewrite scanner integration code (different API)")
    print("    3. Update response parsing")
    print("    4. Update tests")
    print("    5. Deploy")
    print("    6. Estimated: 1-2 days")
    print()
    print("  WITH CapMesh:")

    registry.register(Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="security", name="semgrep-scanner",
                          version="2.0.0", owner="security-team"),
        provides=[CapabilityRef(capability="security.scan", contract="v1")],
        requires=[],
        interface=A2AInterface(protocol="a2a", endpoint="https://semgrep.example.com"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ))
    print("    1. Register semgrep-scanner:2.0.0 (one command)")
    print("    2. Done. Higher version wins automatically.")
    print()

    # Re-resolve — SAME orchestrator code
    scan_res2 = resolver.resolve(ResolveRequest(
        capability="security.scan", contract="v1", caller=caller))
    scan_svc2 = get_service(scan_res2.binding)
    findings2 = scan_svc2.scan(files2["files"])

    print(f"    Before: {scan_res.provider_name}:{scan_res.provider_version} -> {len(findings)} findings")
    print(f"    After:  {scan_res2.provider_name}:{scan_res2.provider_version} -> {len(findings2)} findings")
    print()
    print("    New results (Semgrep finds MORE vulnerabilities):")
    print("  " + "-" * 60)
    verdict_c = print_report(findings2, files2["source"], scan_svc2.name)

    # ---- Change 3: Restrict access ----
    print()
    print()
    print("  CHANGE 3: Intern should NOT access the security scanner")
    print("  " + "-" * 60)
    print()
    print("  WITHOUT CapMesh:")
    print("    1. Add auth middleware to every service")
    print("    2. Implement role checking")
    print("    3. Maintain ACLs somewhere")
    print("    4. Estimated: days of work")
    print()
    print("  WITH CapMesh:")

    # Register a private scanner
    registry.register(Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="security", name="deep-scanner",
                          version="3.0.0", owner="security-team"),
        provides=[CapabilityRef(capability="security.deep-scan", contract="v1")],
        requires=[],
        interface=A2AInterface(protocol="a2a", endpoint="https://deep.example.com"),
        governance=Governance(visibility=Visibility.PRIVATE, status=Status.APPROVED),
    ))
    print("    Set visibility: private in the manifest YAML. That's it.")
    print()

    from capmesh.resolver import ResolutionError

    print("    Intern (identity='intern') tries to resolve:")
    try:
        resolver.resolve(ResolveRequest(
            capability="security.deep-scan", contract="v1",
            caller=CallerContext(identity="intern")))
        print("      ALLOWED (bad!)")
    except ResolutionError:
        print("      DENIED by visibility policy")

    print()
    print("    Security team (identity='security-team') resolves:")
    r = resolver.resolve(ResolveRequest(
        capability="security.deep-scan", contract="v1",
        caller=CallerContext(identity="security-team")))
    print(f"      ALLOWED -> {r.provider_name}:{r.provider_version}")

    # ---- Final audit ----
    print()
    print()
    print("  AUDIT: What tools were used in this session?")
    print("  " + "-" * 60)
    traces = trace_store.list_traces(limit=50)
    successful = [t for t in traces if t.outcome == "success"]
    denied = [t for t in traces if t.outcome != "success"]
    print(f"    {len(successful)} successful resolutions")
    print(f"    {len(denied)} denied/failed resolutions")
    print()
    for t in reversed(traces):
        status = "OK" if t.outcome == "success" else "DENIED"
        selected = t.selected_provider or "-"
        print(f"    [{status:6s}] {t.caller.identity:15s} -> {t.requested_capability:25s} -> {selected}")

    return verdict_c, len(findings2), registry, resolver, trace_store


# =====================================================================
# MAIN
# =====================================================================

def main():
    print()
    print("#" * 70)
    print("#")
    print("#  CAPMESH: True Benefits Demo")
    print("#")
    print("#  Scenario: Security review of myorg/webapp")
    print("#  Then: Requirements change. Watch what breaks.")
    print("#")
    print("#" * 70)

    verdict_a, count_a = part_a()
    verdict_c, count_c, _, _, _ = part_b()

    print()
    print()
    print("=" * 70)
    print("  FINAL COMPARISON")
    print("=" * 70)
    print()
    print(f"  {'':30s} {'WITHOUT':>12s}   {'WITH CAPMESH':>12s}")
    print(f"  {'':30s} {'-' * 12}   {'-' * 12}")
    print(f"  {'Initial scan findings':30s} {count_a:>12d}   {count_a:>12d}")
    print(f"  {'After scanner upgrade':30s} {'(manual)':>12s}   {count_c:>12d}")
    print()
    print(f"  {'Swap GitHub to GitLab':30s} {'2-3 days':>12s}   {'30 seconds':>12s}")
    print(f"  {'Upgrade Snyk to Semgrep':30s} {'1-2 days':>12s}   {'30 seconds':>12s}")
    print(f"  {'Restrict intern access':30s} {'days':>12s}   {'1 YAML field':>12s}")
    print(f"  {'Orchestrator code changes':30s} {'3 changes':>12s}   {'0 changes':>12s}")
    print(f"  {'Redeployments':30s} {'3':>12s}   {'0':>12s}")
    print(f"  {'Audit trail':30s} {'none':>12s}   {'automatic':>12s}")
    print()
    print("  The orchestrator code WITH CapMesh never changed once.")
    print("  Three major requirement changes. Zero code changes. Full audit trail.")
    print()


if __name__ == "__main__":
    main()
