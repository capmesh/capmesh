#!/usr/bin/env python3
"""
CapMesh — WITH vs WITHOUT comparison

Scenario: An orchestrator agent needs to:
  1. Read a repository
  2. Run a security scan
  3. Generate a report

Shows what happens WITH and WITHOUT CapMesh.
"""
import sqlite3
import tempfile
import time
from pathlib import Path

# =====================================================================
# SIMULATED TOOLS (pretend these are real services)
# =====================================================================

class GitHubTool:
    """Simulates a GitHub MCP tool."""
    def read_repo(self, repo: str) -> dict:
        return {
            "repo": repo,
            "files": ["app.py", "config.py", "auth.py", "database.py"],
            "languages": ["Python"],
            "size": "2.4 MB",
        }

class GitLabTool:
    """Simulates a GitLab MCP tool (compatible replacement)."""
    def read_repo(self, repo: str) -> dict:
        return {
            "repo": repo,
            "files": ["app.py", "config.py", "auth.py", "database.py"],
            "languages": ["Python"],
            "size": "2.4 MB",
            "source": "GitLab",  # same interface, different backend
        }

class SecurityScanner:
    """Simulates a security scanner agent."""
    def scan(self, files: list[str]) -> dict:
        return {
            "findings": [
                {"file": "auth.py", "severity": "HIGH", "issue": "Hardcoded API key on line 42"},
                {"file": "database.py", "severity": "MEDIUM", "issue": "SQL query built with string concatenation"},
                {"file": "config.py", "severity": "LOW", "issue": "Debug mode enabled"},
            ],
            "total": 3,
            "critical": 0,
            "high": 1,
            "medium": 1,
            "low": 1,
        }

class ReportGenerator:
    """Simulates a report generator."""
    def generate(self, scan_results: dict, repo_info: dict) -> str:
        findings = scan_results["findings"]
        lines = [
            f"Security Report for {repo_info['repo']}",
            f"{'=' * 50}",
            f"Files scanned: {len(repo_info['files'])}",
            f"Total findings: {scan_results['total']}",
            f"  Critical: {scan_results['critical']}",
            f"  High:     {scan_results['high']}",
            f"  Medium:   {scan_results['medium']}",
            f"  Low:      {scan_results['low']}",
            "",
            "Findings:",
        ]
        for f in findings:
            lines.append(f"  [{f['severity']}] {f['file']}: {f['issue']}")
        lines.append("")
        lines.append("Recommendation: Fix HIGH severity issues before deployment.")
        return "\n".join(lines)


# Simulated tool registry (maps binding info to actual tool instances)
TOOL_INSTANCES = {
    "github-mcp": GitHubTool(),
    "gitlab-mcp": GitLabTool(),
    "security-scanner.example.com": SecurityScanner(),
    "report-gen.example.com": ReportGenerator(),
}

def get_tool(connection: dict):
    """Look up a tool instance from binding connection info."""
    key = connection.get("server") or connection.get("endpoint", "").replace("https://", "")
    return TOOL_INSTANCES.get(key)


# =====================================================================
# WITHOUT CAPMESH — Hardcoded everything
# =====================================================================

def without_capmesh():
    print("=" * 70)
    print("  WITHOUT CAPMESH — Hardcoded orchestrator")
    print("=" * 70)
    print()

    print("  [Orchestrator code]")
    print("  " + "-" * 50)
    print("  github = GitHubTool()           # HARDCODED")
    print("  scanner = SecurityScanner()     # HARDCODED")
    print("  reporter = ReportGenerator()    # HARDCODED")
    print()

    start = time.monotonic()

    # Hardcoded tool instantiation
    github = GitHubTool()
    scanner = SecurityScanner()
    reporter = ReportGenerator()

    # Step 1: Read repo
    print("  Step 1: Read repository...")
    repo_info = github.read_repo("myorg/myapp")
    print(f"    Found {len(repo_info['files'])} files")

    # Step 2: Scan
    print("  Step 2: Run security scan...")
    scan_results = scanner.scan(repo_info["files"])
    print(f"    Found {scan_results['total']} issues")

    # Step 3: Report
    print("  Step 3: Generate report...")
    report = reporter.generate(scan_results, repo_info)

    elapsed = (time.monotonic() - start) * 1000
    print()
    print(f"  Result ({elapsed:.0f}ms):")
    print()
    for line in report.split("\n"):
        print(f"    {line}")
    print()

    # Now show the problems
    print("  PROBLEMS:")
    print("  " + "-" * 50)
    print("  1. Changing GitHub -> GitLab requires CODE CHANGES")
    print("  2. Adding a new scanner requires CODE CHANGES")
    print("  3. No audit trail of which tools were used")
    print("  4. No policy enforcement (who can use what)")
    print("  5. Orchestrator must know about every tool directly")
    print("  6. Can't swap tools without redeployment")
    print()

    # Simulate the pain of swapping
    print("  Want to switch from GitHub to GitLab?")
    print("  " + "-" * 50)
    print("  1. Find every file that imports GitHubTool")
    print("  2. Change imports to GitLabTool")
    print("  3. Update instantiation code")
    print("  4. Update tests")
    print("  5. Code review")
    print("  6. Deploy")
    print("  7. Hope nothing breaks")
    print()
    return report


# =====================================================================
# WITH CAPMESH — Dynamic discovery and binding
# =====================================================================

def with_capmesh():
    from capmesh.adapters.defaults import default_adapter_registry
    from capmesh.models import (
        A2AInterface, CapabilityRef, Governance, Kind, MCPInterface,
        Manifest, Metadata, Status, Visibility,
    )
    from capmesh.models.resolution import CallerContext, ResolveRequest
    from capmesh.policy import default_policy_engine
    from capmesh.registry import Registry
    from capmesh.resolver import Resolver
    from capmesh.telemetry import TraceStore

    print("=" * 70)
    print("  WITH CAPMESH — Dynamic orchestrator")
    print("=" * 70)
    print()

    # Setup CapMesh
    root = Path(tempfile.mkdtemp(prefix="capmesh-compare-"))
    registry = Registry(root=root)
    policy = default_policy_engine()
    db = sqlite3.connect(str(root / "traces.db"))
    db.row_factory = sqlite3.Row
    trace_store = TraceStore(db)
    trace_store.init_schema()
    resolver = Resolver(registry=registry, policy_engine=policy, trace_store=trace_store)
    adapter_reg = default_adapter_registry(resolver=resolver)
    resolver._adapter_registry = adapter_reg

    # Register providers (done ONCE by platform team, not by orchestrator)
    print("  [Platform team registers providers — orchestrator doesn't care]")
    print("  " + "-" * 50)

    providers = [
        Manifest(
            metadata=Metadata(kind=Kind.TOOL, namespace="repo", name="github-reader",
                              version="1.0.0", owner="platform"),
            provides=[CapabilityRef(capability="repository.read", contract="v1")],
            requires=[],
            interface=MCPInterface(protocol="mcp", server="github-mcp", tool_name="read"),
            governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        ),
        Manifest(
            metadata=Metadata(kind=Kind.AGENT, namespace="security", name="scanner",
                              version="2.0.0", owner="security-team"),
            provides=[CapabilityRef(capability="security.scan", contract="v1")],
            requires=[],
            interface=A2AInterface(protocol="a2a", endpoint="https://security-scanner.example.com"),
            governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        ),
        Manifest(
            metadata=Metadata(kind=Kind.AGENT, namespace="reporting", name="report-gen",
                              version="1.0.0", owner="platform"),
            provides=[CapabilityRef(capability="report.generate", contract="v1")],
            requires=[],
            interface=A2AInterface(protocol="a2a", endpoint="https://report-gen.example.com"),
            governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        ),
    ]

    for p in providers:
        registry.register(p)
        print(f"  Registered: {p.metadata.namespace}/{p.metadata.name}:{p.metadata.version}")
    print()

    print("  [Orchestrator code — ZERO knowledge of specific tools]")
    print("  " + "-" * 50)
    print('  repo_binding  = resolver.resolve("repository.read/v1")')
    print('  scan_binding  = resolver.resolve("security.scan/v1")')
    print('  report_binding = resolver.resolve("report.generate/v1")')
    print()

    caller = CallerContext(identity="orchestrator-agent", environment="production")
    start = time.monotonic()

    # Step 1: Resolve & use repository.read
    print("  Step 1: Resolve repository.read/v1...")
    repo_res = resolver.resolve(ResolveRequest(
        capability="repository.read", contract="v1", caller=caller,
    ))
    repo_tool = get_tool(repo_res.binding.connection)
    print(f"    Resolved: {repo_res.provider_namespace}/{repo_res.provider_name}:{repo_res.provider_version} ({repo_res.binding.protocol})")
    repo_info = repo_tool.read_repo("myorg/myapp")
    print(f"    Result: Found {len(repo_info['files'])} files")

    # Step 2: Resolve & use security.scan
    print("  Step 2: Resolve security.scan/v1...")
    scan_res = resolver.resolve(ResolveRequest(
        capability="security.scan", contract="v1", caller=caller,
    ))
    scanner = get_tool(scan_res.binding.connection)
    print(f"    Resolved: {scan_res.provider_namespace}/{scan_res.provider_name}:{scan_res.provider_version} ({scan_res.binding.protocol})")
    scan_results = scanner.scan(repo_info["files"])
    print(f"    Result: Found {scan_results['total']} issues")

    # Step 3: Resolve & use report.generate
    print("  Step 3: Resolve report.generate/v1...")
    report_res = resolver.resolve(ResolveRequest(
        capability="report.generate", contract="v1", caller=caller,
    ))
    reporter = get_tool(report_res.binding.connection)
    print(f"    Resolved: {report_res.provider_namespace}/{report_res.provider_name}:{report_res.provider_version} ({report_res.binding.protocol})")
    report = reporter.generate(scan_results, repo_info)

    elapsed = (time.monotonic() - start) * 1000
    print()
    print(f"  Result ({elapsed:.0f}ms):")
    print()
    for line in report.split("\n"):
        print(f"    {line}")
    print()

    # Show audit trail
    print("  AUDIT TRAIL:")
    print("  " + "-" * 50)
    traces = trace_store.list_traces(limit=10)
    for t in reversed(traces):
        print(f"  [{t.trace_id}] {t.requested_capability}/{t.requested_contract}")
        print(f"    -> {t.selected_provider} ({t.outcome}, {t.resolution_ms:.1f}ms)")
    print()

    # NOW: Swap GitHub -> GitLab WITHOUT any code changes
    print("  " + "=" * 50)
    print("  LIVE SWAP: GitHub -> GitLab (ZERO code changes)")
    print("  " + "=" * 50)
    print()

    # Register GitLab as a higher version
    gitlab = Manifest(
        metadata=Metadata(kind=Kind.TOOL, namespace="repo", name="gitlab-reader",
                          version="2.0.0", owner="platform"),
        provides=[CapabilityRef(capability="repository.read", contract="v1")],
        requires=[],
        interface=MCPInterface(protocol="mcp", server="gitlab-mcp", tool_name="read"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )
    registry.register(gitlab)
    print("  Platform team registers: repo/gitlab-reader:2.0.0")
    print("  Orchestrator code: UNCHANGED")
    print()

    # Same orchestrator code, different result
    print("  Re-running the same orchestrator...")
    repo_res2 = resolver.resolve(ResolveRequest(
        capability="repository.read", contract="v1", caller=caller,
    ))
    repo_tool2 = get_tool(repo_res2.binding.connection)
    print(f"    Resolved: {repo_res2.provider_namespace}/{repo_res2.provider_name}:{repo_res2.provider_version}")
    repo_info2 = repo_tool2.read_repo("myorg/myapp")
    source = repo_info2.get("source", "GitHub")
    print(f"    Source:   {source}")
    print(f"    Files:    {len(repo_info2['files'])}")
    print()
    print(f"  Before: github-reader:1.0.0 (GitHub)")
    print(f"  After:  gitlab-reader:2.0.0 (GitLab)")
    print(f"  Code changes: 0")
    print(f"  Redeployment: No")
    print(f"  Downtime: None")
    print()

    return report


# =====================================================================
# MAIN — Run both side by side
# =====================================================================

def main():
    print()
    print("#" * 70)
    print("#  SCENARIO: Security review of a repository")
    print("#  Task: Read repo -> Scan for vulnerabilities -> Generate report")
    print("#" * 70)
    print()

    report1 = without_capmesh()
    print()
    report2 = with_capmesh()

    # Final comparison
    print("=" * 70)
    print("  COMPARISON SUMMARY")
    print("=" * 70)
    print()
    print(f"  {'Feature':<35s} {'WITHOUT':<15s} {'WITH CAPMESH':<15s}")
    print(f"  {'-' * 35} {'-' * 15} {'-' * 15}")
    print(f"  {'Same result?':<35s} {'Yes':<15s} {'Yes':<15s}")
    print(f"  {'Hardcoded tool names?':<35s} {'Yes':<15s} {'No':<15s}")
    print(f"  {'Swap provider at runtime?':<35s} {'No':<15s} {'Yes':<15s}")
    print(f"  {'Audit trail?':<35s} {'No':<15s} {'Yes':<15s}")
    print(f"  {'Policy enforcement?':<35s} {'No':<15s} {'Yes':<15s}")
    print(f"  {'Code change to swap tool?':<35s} {'Yes':<15s} {'No':<15s}")
    print(f"  {'Redeployment to swap tool?':<35s} {'Yes':<15s} {'No':<15s}")
    print(f"  {'Cross-framework discovery?':<35s} {'No':<15s} {'Yes':<15s}")
    print()


if __name__ == "__main__":
    main()
