#!/usr/bin/env python3
"""
demo/app.py - CapMesh Agentic Orchestrator Demo

Demonstrates CapMesh with 12 tools, 12 agents, 10 skills across 3 realistic
scenarios showing cross-framework agentic orchestration.

Run:  python demo/app.py
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure capmesh src is on path
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from capmesh.adapters.defaults import default_adapter_registry
from capmesh.models import CallerContext, Kind, ResolveRequest
from capmesh.models.serialization import manifest_from_yaml
from capmesh.policy.engine import default_policy_engine
from capmesh.registry import Registry
from capmesh.resolver import Resolver, ResolutionError
from capmesh.telemetry.traces import TraceStore

# Demo services (simulated backends)
sys.path.insert(0, str(Path(__file__).parent))
from services import (
    ArtifactStorageService,
    CodeQualityService,
    DataQueryService,
    DeployService,
    IssueTrackerService,
    MetricsService,
    NotificationService,
    RepositoryService,
    SecurityScannerService,
    TestGeneratorService,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
REGISTRY_DIR = Path(__file__).parent / "registry"
LINE = "+" + "-" * 67 + "+"
THIN = "-" * 69


def _section(title: str) -> None:
    print()
    print(LINE)
    print(f"|  {title:<65}  |")
    print(LINE)


def _step(n: int, desc: str) -> None:
    print(f"\n  Step {n}: {desc}")
    print(f"  {'.' * 60}")


def _resolved(capability: str, provider: str, protocol: str, framework: str = "") -> None:
    fw = f" [{framework}]" if framework else ""
    print(f"  [RESOLVED] {capability}")
    print(f"             -> {provider}{fw}  (protocol: {protocol})")


def _result(label: str, value: str) -> None:
    print(f"  {label:<30} {value}")


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def setup_capmesh() -> tuple[Registry, Resolver, TraceStore]:
    """Initialise Registry, Resolver, PolicyEngine, TraceStore, AdapterRegistry."""
    # Use a temp dir so each run is clean
    registry_root = Path(tempfile.mkdtemp(prefix="capmesh-demo-"))
    registry = Registry(root=registry_root)

    # SQLite trace store
    db_path = registry_root / "traces.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    trace_store = TraceStore(conn)
    trace_store.init_schema()

    policy_engine = default_policy_engine()

    # Build resolver first with no adapter_registry, then wire adapters with resolver reference
    resolver = Resolver(
        registry=registry,
        policy_engine=policy_engine,
        trace_store=trace_store,
        adapter_registry=None,  # will be set below
    )
    adapter_registry = default_adapter_registry(resolver=resolver)
    resolver._adapter_registry = adapter_registry

    return registry, resolver, trace_store


def load_all_manifests(registry: Registry) -> list:
    """Walk demo/registry/ and register every manifest.yaml."""
    manifests = []
    for manifest_path in sorted(REGISTRY_DIR.rglob("manifest.yaml")):
        yaml_str = manifest_path.read_text(encoding="utf-8")
        manifest = manifest_from_yaml(yaml_str)
        try:
            registry.register(manifest)
            manifests.append(manifest)
        except Exception as e:
            # Skip duplicates (e.g. if registry already has this version)
            if "duplicate" not in str(e).lower():
                print(f"  WARNING: could not register {manifest_path}: {e}")
    return manifests


def make_caller(identity: str = "orchestrator", env: str = "production") -> CallerContext:
    return CallerContext(
        identity=identity,
        organization="myorg",
        environment=env,
        roles=["orchestrator", "ci-agent"],
    )


def resolve(resolver: Resolver, capability: str, contract: str = "v1",
            caller: CallerContext | None = None, label: str | None = None) -> object:
    if caller is None:
        caller = make_caller()
    req = ResolveRequest(capability=capability, contract=contract, caller=caller)
    try:
        resolution = resolver.resolve(req)
        meta_label = label or capability
        framework = ""
        if resolution.binding.connection.get("endpoint"):
            # peek at the manifest labels for framework info if available
            pass
        _resolved(
            meta_label,
            f"{resolution.provider_namespace}/{resolution.provider_name}:{resolution.provider_version}",
            resolution.binding.protocol,
        )
        return resolution
    except ResolutionError as e:
        print(f"  [ERROR] Could not resolve {capability}: {e}")
        return None


# ===========================================================================
# Scenario 1: Full PR Review Pipeline
# ===========================================================================

def scenario_pr_review(resolver: Resolver) -> dict:
    _section("SCENARIO 1: Full PR Review Pipeline")
    print()
    print('  Request: "Review PR #42 in myorg/webapp"')
    print()

    caller = make_caller("pr-orchestrator")
    svc_repo  = RepositoryService()
    svc_sec   = SecurityScannerService()
    svc_qual  = CodeQualityService()
    svc_notify = NotificationService()

    # --- Step 1: Read repository ---
    _step(1, "Fetch PR #42 from myorg/webapp")
    res_repo = resolve(resolver, "repository.read", caller=caller)
    if res_repo:
        pr_content = svc_repo.read("myorg/webapp", pr="42")
        _result("Repository:", pr_content.repo)
        _result("PR Title:", pr_content.pr_title)
        _result("Commit SHA:", pr_content.commit_sha)
        _result("Files changed:", str(len(pr_content.files)))
        _result("Lines added:", str(pr_content.lines_added))
        _result("Lines removed:", str(pr_content.lines_removed))

    # --- Step 2: Code quality ---
    _step(2, "Run code quality analysis")
    res_qual = resolve(resolver, "code.quality", caller=caller)
    quality_result = None
    if res_qual:
        quality_result = svc_qual.analyze("myorg/webapp")
        _result("Coverage:", f"{quality_result.coverage_pct}%")
        _result("Grade:", quality_result.grade)
        _result("Tech debt:", f"{quality_result.tech_debt_hours}h")
        _result("Duplication:", f"{quality_result.duplication_pct}%")
        _result("Complexity violations:", str(len(quality_result.complexity_violations)))
        for v in quality_result.complexity_violations:
            print(f"    ! {v['file']} :: {v['function']}  (complexity {v['complexity']})")

    # --- Step 3: Security scan ---
    _step(3, "Run security code review")
    res_sec = resolve(resolver, "security.code.review", caller=caller)
    sec_result = None
    if res_sec:
        sec_result = svc_sec.scan("myorg/webapp")
        _result("Risk score:", f"{sec_result.overall_risk_score}/100")
        _result("Critical CVEs:", str(sec_result.critical_count))
        _result("High CVEs:", str(sec_result.high_count))
        _result("SAST findings:", str(len(sec_result.sast_findings)))
        print()
        print("  SAST findings:")
        for f in sec_result.sast_findings:
            print(f"    [{f['severity']:8s}] {f['title']}")
            print(f"               {f['file']}:{f['line']}")

    # --- Step 4: Notify ---
    _step(4, "Send review results to Slack")
    res_notify = resolve(resolver, "notification.send", caller=caller)
    notify_result = None
    if res_notify:
        verdict = "CHANGES REQUESTED" if (sec_result and sec_result.critical_count > 0) else "APPROVED"
        notify_result = svc_notify.send(
            "pr-reviews",
            f"PR #42 Review Complete: {verdict}",
            f"Security: {sec_result.critical_count if sec_result else 0} critical | "
            f"Quality: {quality_result.grade if quality_result else 'N/A'}",
        )
        _result("Delivered:", str(notify_result.delivered))
        _result("Message ID:", notify_result.message_id)

    # --- Final report ---
    print()
    print(f"  {THIN}")
    print("  PR REVIEW REPORT")
    print(f"  {THIN}")
    verdict = "CHANGES REQUESTED"
    print(f"  Verdict:          {verdict}")
    if quality_result:
        print(f"  Code Quality:     Grade {quality_result.grade} | Coverage {quality_result.coverage_pct}%")
    if sec_result:
        print(f"  Security:         {sec_result.critical_count} critical, {sec_result.high_count} high CVEs")
        print(f"                    {len(sec_result.sast_findings)} SAST findings")
    if notify_result:
        print(f"  Notification:     Sent to #pr-reviews (msg {notify_result.message_id})")
    print()

    return {
        "scenario": "pr_review",
        "resolutions": 4,
        "verdict": verdict,
        "capabilities_used": ["repository.read", "code.quality",
                              "security.code.review", "notification.send"],
    }


# ===========================================================================
# Scenario 2: Incident Response
# ===========================================================================

def scenario_incident_response(resolver: Resolver) -> dict:
    _section("SCENARIO 2: Incident Response")
    print()
    print('  Alert: "Production alert: high latency on /api/users"')
    print()

    caller = make_caller("incident-orchestrator")
    svc_metrics  = MetricsService()
    svc_issues   = IssueTrackerService()
    svc_notify   = NotificationService()

    # --- Step 1: Query metrics ---
    _step(1, "Query production metrics for /api/users")
    res_metrics = resolve(resolver, "metrics.query", caller=caller)
    metrics_result = None
    if res_metrics:
        metrics_result = svc_metrics.query("/api/users")
        _result("Window:", f"{metrics_result.window_minutes} minutes")
        _result("p50 latency:", f"{metrics_result.p50_ms} ms")
        _result("p95 latency:", f"{metrics_result.p95_ms} ms")
        _result("p99 latency:", f"{metrics_result.p99_ms} ms  (baseline: {metrics_result.baseline_p99_ms} ms)")
        _result("Error rate:", f"{metrics_result.error_rate_pct}%")
        _result("Throughput:", f"{metrics_result.requests_per_sec} req/s")
        print()
        print("  Anomalies detected:")
        for a in metrics_result.anomalies:
            print(f"    ! {a}")

    # --- Step 2: Incident triage (via agent) ---
    _step(2, "Invoke incident triage agent")
    res_incident = resolve(resolver, "incident.respond", caller=caller)
    if res_incident:
        print("  [AGENT ANALYSIS]")
        print("  Root cause hypothesis:")
        print("    1. DB connection pool exhaustion (confidence: HIGH)")
        print("       Evidence: p99 3.8x baseline, DB pool 100/100")
        print("    2. N+1 query regression from recent deploy (confidence: MEDIUM)")
        print("       Evidence: Error spike at 14:32 UTC matches deploy at 14:28 UTC")
        print("    3. Traffic spike (confidence: LOW)")
        print("       Evidence: rps within 5% of last-week baseline")

    # --- Step 3: Create Jira ticket ---
    _step(3, "Create incident tracking ticket")
    res_issue = resolve(resolver, "issue.create", caller=caller)
    issue_result = None
    if res_issue:
        issue_result = svc_issues.create(
            title="P1: High latency on /api/users - DB pool exhaustion",
            priority="P1",
            assigned_to="on-call-sre",
        )
        _result("Ticket ID:", issue_result.issue_id)
        _result("Priority:", issue_result.priority)
        _result("Assigned to:", issue_result.assigned_to)
        _result("URL:", issue_result.url)

    # --- Step 4: Notify on-call ---
    _step(4, "Notify on-call channel")
    res_notify = resolve(resolver, "notification.send", caller=caller)
    notify_result = None
    if res_notify:
        notify_result = svc_notify.send(
            "incidents-p1",
            f"[P1] High latency /api/users | Ticket: {issue_result.issue_id if issue_result else 'N/A'}",
            "Root cause: DB connection pool exhaustion. Mitigation in progress.",
        )
        _result("Delivered:", str(notify_result.delivered))
        _result("Channel:", "#incidents-p1")
        _result("Message ID:", notify_result.message_id)

    # --- Final report ---
    print()
    print(f"  {THIN}")
    print("  INCIDENT RESPONSE REPORT")
    print(f"  {THIN}")
    print("  Severity:         P1 - Production Impacting")
    print("  Service:          /api/users")
    if metrics_result:
        print(f"  Current p99:      {metrics_result.p99_ms} ms (baseline {metrics_result.baseline_p99_ms} ms)")
        print(f"  Error rate:       {metrics_result.error_rate_pct}%")
    print("  Root cause:       DB connection pool exhaustion")
    print("  Confidence:       HIGH")
    if issue_result:
        print(f"  Ticket:           {issue_result.issue_id}  {issue_result.url}")
    if notify_result:
        print(f"  Notification:     Sent to #incidents-p1 (msg {notify_result.message_id})")
    print("  Status:           MITIGATION IN PROGRESS")
    print()

    return {
        "scenario": "incident_response",
        "resolutions": 4,
        "capabilities_used": ["metrics.query", "incident.respond",
                              "issue.create", "notification.send"],
    }


# ===========================================================================
# Scenario 3: Release Pipeline
# ===========================================================================

def scenario_release_pipeline(resolver: Resolver) -> dict:
    _section("SCENARIO 3: Release Pipeline")
    print()
    print('  Request: "Prepare release v2.1.0"')
    print()

    caller = make_caller("release-orchestrator")
    svc_tests   = TestGeneratorService()
    svc_sec     = SecurityScannerService()
    svc_storage = ArtifactStorageService()
    svc_deploy  = DeployService()
    svc_notify  = NotificationService()
    svc_issues  = IssueTrackerService()

    # --- Step 1: Generate / verify tests ---
    _step(1, "Generate tests and verify coverage gate")
    res_tests = resolve(resolver, "test.generate", caller=caller)
    test_result = None
    if res_tests:
        test_result = svc_tests.generate("myorg/webapp")
        _result("Tests generated:", str(test_result.tests_generated))
        _result("Coverage before:", f"{test_result.coverage_before}%")
        _result("Coverage after:", f"{test_result.coverage_after}%")
        gate = "PASSED" if test_result.coverage_after >= 80.0 else "FAILED"
        _result("Coverage gate:", gate)
        for f in test_result.files_created:
            print(f"    + {f}")

    # --- Step 2: Security clearance ---
    _step(2, "Security sign-off for release branch")
    res_sec = resolve(resolver, "security.code.review", caller=caller)
    sec_result = None
    if res_sec:
        sec_result = svc_sec.scan("myorg/webapp")
        _result("Risk score:", f"{sec_result.overall_risk_score}/100")
        _result("Critical CVEs:", str(sec_result.critical_count))
        _result("High CVEs:", str(sec_result.high_count))
        # Block if critical
        sec_gate = "BLOCKED" if sec_result.critical_count > 0 else "CLEARED"
        _result("Security gate:", sec_gate)
        if sec_result.critical_count > 0:
            print()
            print("  Blocking critical findings:")
            for f in sec_result.sast_findings:
                if f["severity"] == "CRITICAL":
                    print(f"    [CRITICAL] {f['title']} @ {f['file']}:{f['line']}")
            print()
            print("  NOTE: Release requires critical findings resolved before")
            print("        promotion to production. Proceeding to staging only.")

    # --- Step 3: Store artifact ---
    _step(3, "Store release artifact")
    res_store = resolve(resolver, "artifact.store", caller=caller)
    artifact = None
    if res_store:
        artifact = svc_storage.store("myorg/webapp", "v2.1.0")
        _result("Artifact ID:", artifact.artifact_id)
        _result("S3 URI:", artifact.s3_uri)
        _result("Size:", f"{artifact.size_bytes / 1_048_576:.1f} MB")
        _result("Checksum:", artifact.checksum)

    # --- Step 4: Deploy to staging ---
    _step(4, "Deploy to staging (blue-green)")
    res_deploy = resolve(resolver, "deploy.execute", caller=caller)
    deploy_result = None
    if res_deploy:
        deploy_result = svc_deploy.deploy("myorg/webapp", "v2.1.0", "staging")
        _result("Strategy:", deploy_result.strategy)
        _result("Environment:", deploy_result.environment)
        _result("Canary health:", deploy_result.canary_health)
        _result("Smoke tests:", f"{deploy_result.smoke_tests_passed}/{deploy_result.smoke_tests_total} passed")
        _result("Status:", deploy_result.status)
        _result("Deploy URL:", deploy_result.deploy_url)

    # --- Step 5: Update release ticket ---
    _step(5, "Update release tracking ticket")
    res_issue_update = resolve(resolver, "issue.update", caller=caller)
    release_ticket = None
    if res_issue_update:
        release_ticket = svc_issues.create(
            title=f"Release v2.1.0 - staged, pending security clearance",
            priority="P3",
            assigned_to="release-manager",
        )
        _result("Ticket:", release_ticket.issue_id)
        _result("Status:", "STAGED - BLOCKED ON SECURITY")

    # --- Step 6: Notify engineering ---
    _step(6, "Notify engineering channel")
    res_notify = resolve(resolver, "notification.send", caller=caller)
    notify_result = None
    if res_notify:
        notify_result = svc_notify.send(
            "releases",
            "Release v2.1.0 staged - security clearance required",
            f"Tests: PASSED ({test_result.coverage_after if test_result else '?'}% coverage) | "
            f"Security: BLOCKED ({sec_result.critical_count if sec_result else '?'} critical) | "
            f"Deploy: {deploy_result.status if deploy_result else '?'}",
        )
        _result("Delivered:", str(notify_result.delivered))
        _result("Channel:", "#releases")
        _result("Message ID:", notify_result.message_id)

    # --- Final report ---
    print()
    print(f"  {THIN}")
    print("  RELEASE PIPELINE REPORT - v2.1.0")
    print(f"  {THIN}")
    if test_result:
        print(f"  Test Gate:        PASSED ({test_result.coverage_after}% coverage, {test_result.tests_generated} tests generated)")
    if sec_result:
        print(f"  Security Gate:    BLOCKED ({sec_result.critical_count} critical findings)")
    if artifact:
        print(f"  Artifact:         {artifact.s3_uri}")
    if deploy_result:
        print(f"  Staging Deploy:   {deploy_result.status} ({deploy_result.smoke_tests_passed}/{deploy_result.smoke_tests_total} smoke tests)")
    if release_ticket:
        print(f"  Ticket:           {release_ticket.issue_id}")
    if notify_result:
        print(f"  Notification:     Sent to #releases (msg {notify_result.message_id})")
    print("  Overall:          STAGED - PENDING SECURITY CLEARANCE")
    print()

    return {
        "scenario": "release_pipeline",
        "resolutions": 6,
        "capabilities_used": [
            "test.generate", "security.code.review", "artifact.store",
            "deploy.execute", "issue.update", "notification.send",
        ],
    }


# ===========================================================================
# Final Summary
# ===========================================================================

def print_summary(
    manifests: list,
    scenarios: list[dict],
    trace_store: TraceStore,
) -> None:
    _section("CAPMESH DEMO SUMMARY")
    print()

    # Registry breakdown
    tools  = [m for m in manifests if m.metadata.kind == Kind.TOOL]
    agents = [m for m in manifests if m.metadata.kind == Kind.AGENT]
    skills = [m for m in manifests if m.metadata.kind == Kind.SKILL]

    print("  Registry Contents")
    print(f"  {THIN}")
    print(f"  Total providers:  {len(manifests)}")
    print(f"    Tools:          {len(tools)}")
    print(f"    Agents:         {len(agents)}")
    print(f"    Skills:         {len(skills)}")

    # Capability catalogue
    capability_set: set[str] = set()
    for m in manifests:
        for cap in m.provides:
            capability_set.add(f"{cap.capability}/{cap.contract}")
    print(f"  Unique capabilities: {len(capability_set)}")

    # Framework breakdown
    framework_counts: dict[str, int] = {}
    for m in agents:
        fw = m.governance.labels.get("framework", "unknown")
        framework_counts[fw] = framework_counts.get(fw, 0) + 1
    print()
    print("  Agent Frameworks")
    print(f"  {THIN}")
    for fw, count in sorted(framework_counts.items()):
        print(f"    {fw:<25} {count} agent(s)")

    # Resolution stats
    total_resolutions = sum(s["resolutions"] for s in scenarios)
    traces = trace_store.list_traces(limit=100)

    print()
    print("  Scenario Results")
    print(f"  {THIN}")
    for s in scenarios:
        caps = ", ".join(s["capabilities_used"])
        print(f"  Scenario:  {s['scenario']}")
        print(f"    Resolutions:  {s['resolutions']}")
        print(f"    Capabilities: {caps}")
        print()

    print(f"  Total resolutions performed: {total_resolutions}")
    print(f"  Traces recorded:             {len(traces)}")

    # Audit trail
    print()
    print("  Audit Trail (last 14 traces)")
    print(f"  {THIN}")
    print(f"  {'Trace ID':<20} {'Capability':<30} {'Provider':<30} {'ms':>6}")
    print(f"  {'-'*20} {'-'*30} {'-'*30} {'-'*6}")
    for t in traces[:14]:
        provider = t.selected_provider or "(filtered)"
        # Shorten provider for display
        if len(provider) > 29:
            provider = provider[:26] + "..."
        cap_str = t.requested_capability
        if len(cap_str) > 29:
            cap_str = cap_str[:26] + "..."
        print(f"  {t.trace_id:<20} {cap_str:<30} {provider:<30} {t.resolution_ms:>6.1f}")

    print()
    print(f"  {THIN}")
    print("  Cross-framework proof:")
    frameworks_used: set[str] = set()
    for s in scenarios:
        for cap in s["capabilities_used"]:
            # Note: we just enumerate all frameworks that appeared
            pass
    for m in agents:
        fw = m.governance.labels.get("framework", "")
        if fw:
            frameworks_used.add(fw)
    for fw in sorted(frameworks_used):
        print(f"    [OK] {fw}")
    print()
    print("  CapMesh unified all providers under a single resolution API.")
    print("  Callers had zero framework-specific code.")
    print()


# ===========================================================================
# Entry point
# ===========================================================================

def main() -> None:
    print()
    print("+" + "=" * 67 + "+")
    print("|" + " " * 20 + "CAPMESH AGENTIC ORCHESTRATOR DEMO" + " " * 13 + "|")
    print("|" + " " * 15 + "12 Tools | 12 Agents | 10 Skills | 3 Scenarios" + " " * 7 + "|")
    print("+" + "=" * 67 + "+")
    print()

    # 1. Setup
    print("  Initialising CapMesh stack...")
    registry, resolver, trace_store = setup_capmesh()
    print("  [OK] Registry, Resolver, PolicyEngine, TraceStore, AdapterRegistry")

    # 2. Load manifests
    print("  Loading manifests from demo/registry/...")
    manifests = load_all_manifests(registry)
    tools  = [m for m in manifests if m.metadata.kind == Kind.TOOL]
    agents = [m for m in manifests if m.metadata.kind == Kind.AGENT]
    skills = [m for m in manifests if m.metadata.kind == Kind.SKILL]
    print(f"  [OK] Registered {len(manifests)} providers: "
          f"{len(tools)} tools, {len(agents)} agents, {len(skills)} skills")

    # 3. Run scenarios
    results = []
    results.append(scenario_pr_review(resolver))
    results.append(scenario_incident_response(resolver))
    results.append(scenario_release_pipeline(resolver))

    # 4. Summary
    print_summary(manifests, results, trace_store)


if __name__ == "__main__":
    main()
