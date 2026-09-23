#!/usr/bin/env python3
"""
Generate all provider YAML manifests into demo/registry/{tools,agents,skills}/<name>/manifest.yaml

Run once to populate the registry directory.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Base directory (demo/registry/)
# ---------------------------------------------------------------------------
REGISTRY_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _CanonicalDumper(yaml.Dumper):
    """YAML dumper that never uses indentless blocks."""
    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        return super().increase_indent(flow, False)


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(data, Dumper=_CanonicalDumper, sort_keys=True, default_flow_style=False),
        encoding="utf-8",
    )


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")


def _governance(env: list[str] | None = None, labels: dict | None = None,
                status: str = "approved", visibility: str = "public") -> dict:
    return {
        "environment": env or [],
        "labels": labels or {},
        "status": status,
        "visibility": visibility,
    }


def _cap(capability: str, contract: str = "v1") -> dict:
    return {"capability": capability, "contract": contract}


def _mcp_interface(server: str, tool_name: str | None = None) -> dict:
    d: dict = {"protocol": "mcp", "server": server}
    if tool_name:
        d["tool_name"] = tool_name
    return d


def _rest_interface(endpoint: str, auth_type: str = "bearer") -> dict:
    return {
        "protocol": "rest",
        "endpoint": endpoint,
        "auth_type": auth_type,
        "request_mapping": {},
        "response_mapping": {},
    }


def _a2a_interface(endpoint: str) -> dict:
    return {"protocol": "a2a", "endpoint": endpoint}


def _skill_interface(instructions: str = "SKILL.md") -> dict:
    return {"protocol": "skill", "instructions": instructions, "assets": []}


def _metadata(kind: str, namespace: str, name: str, version: str, owner: str) -> dict:
    return {
        "api_version": "capmesh.io/v1alpha1",
        "kind": kind,
        "name": name,
        "namespace": namespace,
        "owner": owner,
        "version": version,
    }


def _manifest(metadata: dict, provides: list[dict], requires: list[dict],
              interface: dict, governance: dict) -> dict:
    return {
        "governance": governance,
        "interface": interface,
        "metadata": metadata,
        "provides": provides,
        "requires": requires,
    }


# ===========================================================================
# TOOLS (12)
# ===========================================================================

TOOLS: list[dict] = [
    # 1. github-reader
    _manifest(
        metadata=_metadata("tool", "repository", "github-reader", "1.0.0", "platform-team"),
        provides=[_cap("repository.read"), _cap("repository.search")],
        requires=[],
        interface=_mcp_interface("github-mcp", "read_file"),
        governance=_governance(env=["production", "staging"],
                               labels={"team": "platform"}),
    ),
    # 2. gitlab-reader
    _manifest(
        metadata=_metadata("tool", "repository", "gitlab-reader", "2.0.0", "platform-team"),
        provides=[_cap("repository.read"), _cap("repository.search")],
        requires=[],
        interface=_mcp_interface("gitlab-mcp", "read_file"),
        governance=_governance(env=["production", "staging"],
                               labels={"team": "platform"}),
    ),
    # 3. bitbucket-reader
    _manifest(
        metadata=_metadata("tool", "repository", "bitbucket-reader", "1.5.0", "platform-team"),
        provides=[_cap("repository.read")],
        requires=[],
        interface=_mcp_interface("bitbucket-mcp", "read_file"),
        governance=_governance(env=["production", "staging"],
                               labels={"team": "platform"}),
    ),
    # 4. snyk-scanner
    _manifest(
        metadata=_metadata("tool", "security", "snyk-scanner", "1.3.0", "security-team"),
        provides=[_cap("security.scan")],
        requires=[],
        interface=_mcp_interface("snyk-mcp", "scan_project"),
        governance=_governance(env=["production", "staging", "development"],
                               labels={"team": "security"}),
    ),
    # 5. sonarqube
    _manifest(
        metadata=_metadata("tool", "quality", "sonarqube", "1.2.0", "quality-team"),
        provides=[_cap("code.quality")],
        requires=[],
        interface=_rest_interface("https://sonarqube.example.com/api"),
        governance=_governance(env=["production", "staging"],
                               labels={"team": "quality"}),
    ),
    # 6. slack-notifier
    _manifest(
        metadata=_metadata("tool", "notifications", "slack-notifier", "1.0.0", "platform-team"),
        provides=[_cap("notification.send")],
        requires=[],
        interface=_rest_interface("https://slack.example.com/api/v1", "oauth2"),
        governance=_governance(env=["production", "staging", "development"],
                               labels={"team": "platform"}),
    ),
    # 7. teams-notifier
    _manifest(
        metadata=_metadata("tool", "notifications", "teams-notifier", "2.0.0", "platform-team"),
        provides=[_cap("notification.send")],
        requires=[],
        interface=_rest_interface("https://teams.example.com/webhooks/v2", "webhook"),
        governance=_governance(env=["production", "staging", "development"],
                               labels={"team": "platform"}),
    ),
    # 8. jira-tracker
    _manifest(
        metadata=_metadata("tool", "issues", "jira-tracker", "1.4.0", "devops-team"),
        provides=[_cap("issue.create"), _cap("issue.update")],
        requires=[],
        interface=_rest_interface("https://jira.example.com/rest/api/3", "basic"),
        governance=_governance(env=["production", "staging"],
                               labels={"team": "devops"}),
    ),
    # 9. linear-tracker
    _manifest(
        metadata=_metadata("tool", "issues", "linear-tracker", "2.0.0", "devops-team"),
        provides=[_cap("issue.create"), _cap("issue.update")],
        requires=[],
        interface=_rest_interface("https://api.linear.app/graphql", "apikey"),
        governance=_governance(env=["production", "staging"],
                               labels={"team": "devops"}),
    ),
    # 10. s3-storage
    _manifest(
        metadata=_metadata("tool", "storage", "s3-storage", "1.1.0", "platform-team"),
        provides=[_cap("artifact.store")],
        requires=[],
        interface=_rest_interface("https://s3.amazonaws.com", "iam"),
        governance=_governance(env=["production", "staging"],
                               labels={"team": "platform"}),
    ),
    # 11. grafana-metrics
    _manifest(
        metadata=_metadata("tool", "observability", "grafana-metrics", "1.0.0", "sre-team"),
        provides=[_cap("metrics.query")],
        requires=[],
        interface=_rest_interface("https://grafana.example.com/api", "apikey"),
        governance=_governance(env=["production", "staging", "development"],
                               labels={"team": "sre"}),
    ),
    # 12. postgres-query
    _manifest(
        metadata=_metadata("tool", "data", "postgres-query", "1.0.0", "data-team"),
        provides=[_cap("data.query")],
        requires=[],
        interface=_mcp_interface("postgres-mcp", "execute_query"),
        governance=_governance(env=["production", "staging"],
                               labels={"team": "data"}),
    ),
]


# ===========================================================================
# AGENTS (12)
# ===========================================================================

AGENTS: list[dict] = [
    # 1. langgraph-security-reviewer
    _manifest(
        metadata=_metadata("agent", "security", "langgraph-security-reviewer", "2.4.0",
                           "security-engineering"),
        provides=[_cap("security.code.review")],
        requires=[_cap("repository.read")],
        interface=_a2a_interface("https://langgraph-security.example.com"),
        governance=_governance(env=["production", "staging"],
                               labels={"framework": "langgraph", "team": "security-engineering"}),
    ),
    # 2. crewai-security-reviewer
    _manifest(
        metadata=_metadata("agent", "security", "crewai-security-reviewer", "3.1.0",
                           "security-engineering"),
        provides=[_cap("security.code.review")],
        requires=[_cap("repository.read")],
        interface=_a2a_interface("https://crewai-security.example.com"),
        governance=_governance(env=["production", "staging"],
                               labels={"framework": "crewai", "team": "security-engineering"}),
    ),
    # 3. strands-perf-analyzer
    _manifest(
        metadata=_metadata("agent", "performance", "strands-perf-analyzer", "1.2.0",
                           "sre-team"),
        provides=[_cap("performance.analyze")],
        requires=[_cap("repository.read"), _cap("metrics.query")],
        interface=_a2a_interface("https://strands-perf.example.com"),
        governance=_governance(env=["production", "staging"],
                               labels={"framework": "strands", "team": "sre"}),
    ),
    # 4. autogen-test-generator
    _manifest(
        metadata=_metadata("agent", "testing", "autogen-test-generator", "1.5.0",
                           "qa-team"),
        provides=[_cap("test.generate")],
        requires=[_cap("repository.read")],
        interface=_a2a_interface("https://autogen-test.example.com"),
        governance=_governance(env=["production", "staging", "development"],
                               labels={"framework": "autogen", "team": "qa"}),
    ),
    # 5. langgraph-code-reviewer
    _manifest(
        metadata=_metadata("agent", "quality", "langgraph-code-reviewer", "2.0.0",
                           "quality-team"),
        provides=[_cap("code.review")],
        requires=[_cap("repository.read"), _cap("code.quality")],
        interface=_a2a_interface("https://langgraph-codereview.example.com"),
        governance=_governance(env=["production", "staging"],
                               labels={"framework": "langgraph", "team": "quality"}),
    ),
    # 6. crewai-doc-generator
    _manifest(
        metadata=_metadata("agent", "documentation", "crewai-doc-generator", "1.8.0",
                           "developer-experience"),
        provides=[_cap("documentation.generate")],
        requires=[_cap("repository.read")],
        interface=_a2a_interface("https://crewai-docs.example.com"),
        governance=_governance(env=["production", "staging", "development"],
                               labels={"framework": "crewai", "team": "developer-experience"}),
    ),
    # 7. strands-deploy-agent
    _manifest(
        metadata=_metadata("agent", "deployment", "strands-deploy-agent", "2.2.0",
                           "devops-team"),
        provides=[_cap("deploy.execute")],
        requires=[_cap("artifact.store")],
        interface=_a2a_interface("https://strands-deploy.example.com"),
        governance=_governance(env=["production", "staging"],
                               labels={"framework": "strands", "team": "devops"}),
    ),
    # 8. semantic-kernel-planner
    _manifest(
        metadata=_metadata("agent", "orchestration", "semantic-kernel-planner", "1.0.0",
                           "platform-team"),
        provides=[_cap("task.plan")],
        requires=[],
        interface=_a2a_interface("https://semantic-kernel-planner.example.com"),
        governance=_governance(env=["production", "staging"],
                               labels={"framework": "semantic-kernel", "team": "platform"}),
    ),
    # 9. langgraph-incident-responder
    _manifest(
        metadata=_metadata("agent", "reliability", "langgraph-incident-responder", "1.3.0",
                           "sre-team"),
        provides=[_cap("incident.respond")],
        requires=[_cap("metrics.query"), _cap("notification.send")],
        interface=_a2a_interface("https://langgraph-incident.example.com"),
        governance=_governance(env=["production"],
                               labels={"framework": "langgraph", "team": "sre"}),
    ),
    # 10. crewai-data-analyst
    _manifest(
        metadata=_metadata("agent", "data", "crewai-data-analyst", "2.1.0",
                           "data-team"),
        provides=[_cap("data.analyze")],
        requires=[_cap("data.query")],
        interface=_a2a_interface("https://crewai-data.example.com"),
        governance=_governance(env=["production", "staging"],
                               labels={"framework": "crewai", "team": "data"}),
    ),
    # 11. autogen-refactor-agent
    _manifest(
        metadata=_metadata("agent", "engineering", "autogen-refactor-agent", "1.1.0",
                           "platform-team"),
        provides=[_cap("code.refactor")],
        requires=[_cap("repository.read"), _cap("test.generate")],
        interface=_a2a_interface("https://autogen-refactor.example.com"),
        governance=_governance(env=["production", "staging", "development"],
                               labels={"framework": "autogen", "team": "platform"}),
    ),
    # 12. strands-release-manager
    _manifest(
        metadata=_metadata("agent", "release", "strands-release-manager", "3.0.0",
                           "devops-team"),
        provides=[_cap("release.manage")],
        requires=[_cap("deploy.execute"), _cap("notification.send"), _cap("issue.update")],
        interface=_a2a_interface("https://strands-release.example.com"),
        governance=_governance(env=["production", "staging"],
                               labels={"framework": "strands", "team": "devops"}),
    ),
]


# ===========================================================================
# SKILLS (10)
# ===========================================================================

SKILLS: list[tuple[dict, str]] = [
    # (manifest_data, SKILL.md content)
    (
        _manifest(
            metadata=_metadata("skill", "security", "security-code-review", "1.2.0",
                               "security-engineering"),
            provides=[_cap("security.code.review")],
            requires=[_cap("repository.read"), _cap("repository.search"),
                      _cap("security.scan")],
            interface=_skill_interface(),
            governance=_governance(env=["production", "staging"],
                                   labels={"team": "security-engineering"}),
        ),
        """
        # Security Code Review Skill

        ## Purpose
        Perform a thorough security review of a code repository, identifying
        vulnerabilities, misconfigurations, and compliance issues.

        ## Procedure

        ### Step 1 — Fetch Repository Context
        Use `repository.read/v1` to fetch the target branch at HEAD.
        Retrieve: all source files, dependency manifests (package.json,
        requirements.txt, go.mod, pom.xml), CI/CD configuration files,
        and infrastructure-as-code templates.

        ### Step 2 — Search for Known Patterns
        Use `repository.search/v1` to scan for:
        - Hardcoded secrets (API keys, tokens, passwords)
        - Insecure function calls (eval, exec, shell injection sinks)
        - Deprecated cryptographic primitives (MD5, SHA1, DES)
        - SQL injection patterns (string-concatenated queries)
        - SSRF-prone URL construction patterns

        ### Step 3 — Run Automated Scan
        Use `security.scan/v1` to run the full dependency and SAST scan.
        Collect:
        - CVE list with severity (critical/high/medium/low)
        - License compliance report
        - OWASP Top 10 checklist results

        ### Step 4 — Triage and Score
        Classify each finding by:
        - Severity: Critical / High / Medium / Low / Informational
        - Exploitability: Direct / Indirect / Theoretical
        - Fix effort: Trivial / Moderate / Complex

        ### Step 5 — Produce Report
        Output a structured SecurityReviewReport containing:
        - Executive summary (1 paragraph)
        - Critical findings table (finding, location, CWE, recommendation)
        - CVE table (package, version, CVE-ID, severity, fix version)
        - Overall risk score (0-100)
        - Sign-off decision: APPROVED / CONDITIONAL / BLOCKED
        """,
    ),
    (
        _manifest(
            metadata=_metadata("skill", "quality", "full-code-review", "1.0.0",
                               "quality-team"),
            provides=[_cap("code.review")],
            requires=[_cap("repository.read"), _cap("code.quality"),
                      _cap("security.scan")],
            interface=_skill_interface(),
            governance=_governance(env=["production", "staging"],
                                   labels={"team": "quality"}),
        ),
        """
        # Full Code Review Skill

        ## Purpose
        Deliver a comprehensive code review combining quality metrics,
        architecture assessment, and security scanning.

        ## Procedure

        ### Step 1 — Fetch Code
        Use `repository.read/v1` to retrieve all modified files in the
        target diff or branch.

        ### Step 2 — Static Analysis
        Use `code.quality/v1` to obtain:
        - Code coverage percentage
        - Cyclomatic complexity per module
        - Technical debt estimate (hours)
        - Duplication ratio
        - Maintainability index

        ### Step 3 — Security Pass
        Use `security.scan/v1` for a lightweight security pass:
        - Dependency vulnerabilities
        - Obvious injection sinks

        ### Step 4 — Architecture Review
        Assess:
        - Layer boundary violations
        - Circular dependency detection
        - API contract consistency

        ### Step 5 — Report
        Produce a CodeReviewReport with:
        - Per-file quality scores
        - Actionable improvement list (ranked by impact)
        - Security finding summary
        - Overall recommendation: APPROVE / REQUEST_CHANGES / REJECT
        """,
    ),
    (
        _manifest(
            metadata=_metadata("skill", "devops", "pr-review", "2.0.0", "platform-team"),
            provides=[_cap("pr.review")],
            requires=[_cap("repository.read"), _cap("code.review"),
                      _cap("security.code.review")],
            interface=_skill_interface(),
            governance=_governance(env=["production", "staging"],
                                   labels={"team": "platform"}),
        ),
        """
        # Pull Request Review Skill

        ## Purpose
        End-to-end pull request review combining code quality and security
        analysis, producing a single actionable PR report.

        ## Procedure

        ### Step 1 — Load PR Metadata
        Use `repository.read/v1` to load:
        - PR title, description, linked issues
        - Diff summary (files changed, lines added/removed)
        - Reviewer assignments and prior comments

        ### Step 2 — Code Quality Review
        Invoke `code.review/v1` on the PR diff to obtain quality findings.

        ### Step 3 — Security Review
        Invoke `security.code.review/v1` on the PR diff to obtain security
        findings.

        ### Step 4 — Consolidate
        Merge findings, deduplicate overlapping issues, and rank by
        severity and impact.

        ### Step 5 — Author Summary
        Produce a PRReviewReport with:
        - LGTM / Changes Requested verdict
        - Inline comment suggestions for each finding
        - Summary paragraph for reviewers
        - Checklist: tests added, docs updated, breaking changes flagged
        """,
    ),
    (
        _manifest(
            metadata=_metadata("skill", "reliability", "incident-triage", "1.5.0",
                               "sre-team"),
            provides=[_cap("incident.triage")],
            requires=[_cap("metrics.query"), _cap("notification.send"),
                      _cap("issue.create")],
            interface=_skill_interface(),
            governance=_governance(env=["production"],
                                   labels={"team": "sre"}),
        ),
        """
        # Incident Triage Skill

        ## Purpose
        Rapidly diagnose production incidents, create tracking tickets,
        and notify on-call responders.

        ## Procedure

        ### Step 1 — Gather Metrics
        Use `metrics.query/v1` to pull the last 30 minutes of:
        - Latency percentiles (p50, p95, p99)
        - Error rate and 5xx counts
        - Throughput (requests/sec)
        - Infrastructure metrics (CPU, memory, disk I/O)
        - Downstream service health

        ### Step 2 — Correlate and Hypothesize
        Compare current metrics against baseline (same time last week).
        Identify the most likely root cause from:
        - Traffic spike
        - Memory leak / GC pressure
        - Database slow queries
        - Downstream dependency failure
        - Deployment regression

        ### Step 3 — Create Incident Ticket
        Use `issue.create/v1` to open a P1/P2 ticket with:
        - Incident timeline
        - Hypothesis and supporting data
        - Affected services and customers
        - Assigned on-call engineer

        ### Step 4 — Notify
        Use `notification.send/v1` to alert:
        - On-call Slack channel with incident summary
        - Management escalation if P1
        - Status page update if customer-facing

        ### Step 5 — Produce Triage Report
        Output an IncidentTriageReport with severity, hypotheses ranked
        by confidence, and recommended next actions.
        """,
    ),
    (
        _manifest(
            metadata=_metadata("skill", "release", "release-checklist", "1.1.0",
                               "devops-team"),
            provides=[_cap("release.check")],
            requires=[_cap("test.generate"), _cap("security.code.review"),
                      _cap("deploy.execute")],
            interface=_skill_interface(),
            governance=_governance(env=["production", "staging"],
                                   labels={"team": "devops"}),
        ),
        """
        # Release Checklist Skill

        ## Purpose
        Execute a full pre-release checklist: generate missing tests,
        security sign-off, and gate-controlled deployment.

        ## Procedure

        ### Step 1 — Test Coverage Gate
        Use `test.generate/v1` to identify untested code paths and
        generate unit/integration tests. Require minimum 80% coverage
        before proceeding.

        ### Step 2 — Security Clearance
        Use `security.code.review/v1` on the release branch.
        Block release if any Critical/High findings remain unresolved.

        ### Step 3 — Deployment Gate
        Use `deploy.execute/v1` to deploy to staging with:
        - Blue/green switch
        - Smoke test suite run
        - Rollback plan verified

        ### Step 4 — Sign-Off Report
        Produce a ReleaseChecklistReport with:
        - Test gate: PASSED/FAILED (coverage %)
        - Security gate: CLEARED/BLOCKED (finding count by severity)
        - Staging deploy: SUCCESS/FAILED
        - Overall: GO / NO-GO
        """,
    ),
    (
        _manifest(
            metadata=_metadata("skill", "developer-experience", "onboarding-guide", "1.0.0",
                               "developer-experience"),
            provides=[_cap("onboarding.guide")],
            requires=[_cap("repository.read"), _cap("documentation.generate")],
            interface=_skill_interface(),
            governance=_governance(env=["production", "staging", "development"],
                                   labels={"team": "developer-experience"}),
        ),
        """
        # Onboarding Guide Skill

        ## Purpose
        Generate a personalized onboarding guide for new engineers joining
        a team, based on actual repository structure and existing docs.

        ## Procedure

        ### Step 1 — Repository Survey
        Use `repository.read/v1` to inventory:
        - README files at every level
        - Architecture decision records (ADR)
        - CI/CD pipeline configurations
        - Service dependency graph (from docker-compose, k8s manifests)
        - Key entry points (main files, CLI commands)

        ### Step 2 — Gap Analysis
        Identify missing or outdated documentation sections.
        Flag services with no runbook.

        ### Step 3 — Generate Guide
        Use `documentation.generate/v1` to produce:
        - "Getting Started in 30 Minutes" step-by-step guide
        - Local development environment setup
        - Architecture overview with service map
        - Common workflows (deploy, rollback, add a feature)
        - Glossary of team-specific terms

        ### Step 4 — Output
        Produce an OnboardingGuide document with structured sections,
        estimated reading time, and links to authoritative sources.
        """,
    ),
    (
        _manifest(
            metadata=_metadata("skill", "reliability", "performance-audit", "1.3.0",
                               "sre-team"),
            provides=[_cap("performance.audit")],
            requires=[_cap("performance.analyze"), _cap("metrics.query"),
                      _cap("notification.send")],
            interface=_skill_interface(),
            governance=_governance(env=["production", "staging"],
                                   labels={"team": "sre"}),
        ),
        """
        # Performance Audit Skill

        ## Purpose
        Conduct a full-stack performance audit, identify bottlenecks,
        and alert stakeholders.

        ## Procedure

        ### Step 1 — Collect Metrics
        Use `metrics.query/v1` to gather 7-day trend data:
        - API latency by endpoint (p50, p95, p99)
        - Database query times
        - Cache hit/miss ratios
        - External dependency call times

        ### Step 2 — Deep Analysis
        Use `performance.analyze/v1` on the codebase and runtime profiles:
        - N+1 query detection
        - Missing indexes
        - Synchronous I/O in hot paths
        - Memory allocation hot spots
        - Thread pool / event loop blocking

        ### Step 3 — Benchmark Comparison
        Compare against SLO targets and industry benchmarks.
        Flag any metric exceeding threshold by >20%.

        ### Step 4 — Notify
        Use `notification.send/v1` to send audit summary to:
        - Engineering lead
        - SRE on-call channel

        ### Step 5 — Report
        Produce a PerformanceAuditReport with:
        - Executive summary
        - Top 5 bottlenecks with estimated impact
        - Optimisation recommendations ranked by effort vs. gain
        """,
    ),
    (
        _manifest(
            metadata=_metadata("skill", "data", "data-pipeline-review", "1.0.0",
                               "data-team"),
            provides=[_cap("data.pipeline.review")],
            requires=[_cap("data.query"), _cap("data.analyze")],
            interface=_skill_interface(),
            governance=_governance(env=["production", "staging"],
                                   labels={"team": "data"}),
        ),
        """
        # Data Pipeline Review Skill

        ## Purpose
        Review data pipeline health, data quality, and transformation
        logic correctness.

        ## Procedure

        ### Step 1 — Sample Data
        Use `data.query/v1` to sample recent pipeline output:
        - Last 10,000 rows from each output table
        - Row counts at each pipeline stage
        - Null/empty value ratios per column
        - Distribution of key categorical fields

        ### Step 2 — Quality Analysis
        Use `data.analyze/v1` to check:
        - Schema drift (unexpected column additions/removals)
        - Data type consistency
        - Referential integrity violations
        - Duplicate key detection
        - Outlier detection in numeric fields

        ### Step 3 — Lineage Audit
        Trace data from source to final sink.
        Verify transformation logic matches documented business rules.

        ### Step 4 — Report
        Produce a DataPipelineReport with:
        - Data quality score (0-100) per table
        - Anomaly list with row-level examples
        - Schema change log
        - Recommended fixes with effort estimate
        """,
    ),
    (
        _manifest(
            metadata=_metadata("skill", "architecture", "api-design-review", "1.2.0",
                               "platform-team"),
            provides=[_cap("api.review")],
            requires=[_cap("repository.read"), _cap("code.quality")],
            interface=_skill_interface(),
            governance=_governance(env=["production", "staging"],
                                   labels={"team": "platform"}),
        ),
        """
        # API Design Review Skill

        ## Purpose
        Review REST/GraphQL/gRPC API definitions for consistency,
        completeness, and adherence to design standards.

        ## Procedure

        ### Step 1 — Load API Specs
        Use `repository.read/v1` to load:
        - OpenAPI/Swagger specifications
        - GraphQL schema files
        - gRPC .proto definitions
        - Postman/Insomnia collections
        - API changelog

        ### Step 2 — Consistency Check
        Use `code.quality/v1` to validate:
        - Naming conventions (camelCase vs snake_case, plural resources)
        - HTTP method semantics (GET never mutates, etc.)
        - Status code correctness
        - Pagination patterns (cursor vs offset)
        - Error response format standardisation

        ### Step 3 — Completeness Review
        Verify:
        - All endpoints documented with request/response schemas
        - Authentication documented per endpoint
        - Rate limiting documented
        - Deprecation notices present where applicable

        ### Step 4 — Report
        Produce an APIDesignReport with:
        - Violations table (endpoint, issue, severity, recommendation)
        - Consistency score (0-100)
        - Breaking change analysis vs. previous version
        - Overall: APPROVED / REVISE
        """,
    ),
    (
        _manifest(
            metadata=_metadata("skill", "deployment", "deployment-validation", "1.4.0",
                               "devops-team"),
            provides=[_cap("deploy.validate")],
            requires=[_cap("deploy.execute"), _cap("metrics.query"),
                      _cap("notification.send")],
            interface=_skill_interface(),
            governance=_governance(env=["production", "staging"],
                                   labels={"team": "devops"}),
        ),
        """
        # Deployment Validation Skill

        ## Purpose
        Validate a deployment is healthy after rollout: check metrics,
        run smoke tests, and notify stakeholders.

        ## Procedure

        ### Step 1 — Trigger Canary
        Use `deploy.execute/v1` to deploy to 5% of traffic (canary).
        Wait 5 minutes.

        ### Step 2 — Monitor Canary
        Use `metrics.query/v1` to compare canary vs. baseline:
        - Error rate delta (alert if >0.1% increase)
        - Latency p99 delta (alert if >50ms increase)
        - Business metrics (conversions, API calls) for regressions

        ### Step 3 — Decide
        If canary is healthy: promote to 100% traffic.
        If canary is degraded: automatic rollback via `deploy.execute/v1`.

        ### Step 4 — Post-Deploy Validation
        Use `metrics.query/v1` at 15 min and 60 min post-deploy to
        confirm stability.

        ### Step 5 — Notify
        Use `notification.send/v1` to send deployment status to:
        - Engineering Slack channel
        - Deployment tracking ticket (if linked)

        ### Step 6 — Report
        Produce a DeploymentValidationReport with:
        - Canary verdict: HEALTHY / DEGRADED
        - Full deploy status: SUCCESS / ROLLED_BACK
        - Metric delta table
        - Timeline of events
        """,
    ),
]


# ===========================================================================
# Main generation logic
# ===========================================================================

def generate() -> None:
    counts: dict[str, int] = {"tools": 0, "agents": 0, "skills": 0}

    print("=" * 65)
    print("  CapMesh Registry Generator")
    print("=" * 65)

    # --- Tools ---
    print()
    print("  [TOOLS]")
    for tool in TOOLS:
        name = tool["metadata"]["name"]
        path = REGISTRY_DIR / "tools" / name / "manifest.yaml"
        _write_yaml(path, tool)
        caps = ", ".join(c["capability"] for c in tool["provides"])
        print(f"    Generated: {name} -> {caps}")
        counts["tools"] += 1

    # --- Agents ---
    print()
    print("  [AGENTS]")
    for agent in AGENTS:
        name = agent["metadata"]["name"]
        path = REGISTRY_DIR / "agents" / name / "manifest.yaml"
        _write_yaml(path, agent)
        framework = agent["governance"]["labels"].get("framework", "-")
        caps = ", ".join(c["capability"] for c in agent["provides"])
        print(f"    Generated: {name} [{framework}] -> {caps}")
        counts["agents"] += 1

    # --- Skills ---
    print()
    print("  [SKILLS]")
    for skill_data, skill_md in SKILLS:
        name = skill_data["metadata"]["name"]
        manifest_path = REGISTRY_DIR / "skills" / name / "manifest.yaml"
        skill_md_path = REGISTRY_DIR / "skills" / name / "SKILL.md"
        _write_yaml(manifest_path, skill_data)
        _write_text(skill_md_path, skill_md)
        caps = ", ".join(c["capability"] for c in skill_data["provides"])
        print(f"    Generated: {name} -> {caps}")
        counts["skills"] += 1

    # --- Summary ---
    total = sum(counts.values())
    print()
    print("-" * 65)
    print(f"  Generated {total} provider manifests:")
    print(f"    Tools:  {counts['tools']}")
    print(f"    Agents: {counts['agents']}")
    print(f"    Skills: {counts['skills']}")
    print(f"  Output directory: {REGISTRY_DIR}")
    print("-" * 65)
    print()


if __name__ == "__main__":
    generate()
