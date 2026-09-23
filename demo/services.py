"""
demo/services.py — Simulated service backends for the CapMesh demo.

Each class mimics a real service and returns realistic mock data.
Services are designed to chain: output from one feeds as input to the next.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _fmt_list(items: list[str], indent: int = 6) -> str:
    pad = " " * indent
    return "\n".join(f"{pad}- {item}" for item in items)


# ---------------------------------------------------------------------------
# Repository Service  (repository.read/v1, repository.search/v1)
# ---------------------------------------------------------------------------

@dataclass
class RepoFile:
    path: str
    size_bytes: int
    language: str


@dataclass
class RepositoryContent:
    repo: str
    branch: str
    commit_sha: str
    files: list[RepoFile] = field(default_factory=list)
    pr_title: str = ""
    pr_author: str = ""
    lines_added: int = 0
    lines_removed: int = 0


class RepositoryService:
    """Simulates github-reader / gitlab-reader / bitbucket-reader."""

    def read(self, repo: str, ref: str = "main", pr: str | None = None) -> RepositoryContent:
        files = [
            RepoFile("src/api/users.py",   4200, "Python"),
            RepoFile("src/api/auth.py",    2800, "Python"),
            RepoFile("src/db/models.py",   5100, "Python"),
            RepoFile("src/utils/cache.py", 1200, "Python"),
            RepoFile("tests/test_users.py", 900, "Python"),
            RepoFile("Dockerfile",          180, "Dockerfile"),
            RepoFile("requirements.txt",    220, "Text"),
            RepoFile(".github/workflows/ci.yml", 310, "YAML"),
        ]
        content = RepositoryContent(
            repo=repo,
            branch=ref,
            commit_sha="a3f9c2d1e84b57690f23",
            files=files,
            lines_added=412,
            lines_removed=87,
        )
        if pr:
            content.pr_title = f"feat: improve /api/users endpoint performance"
            content.pr_author = "alice@example.com"
        return content

    def search(self, repo: str, pattern: str) -> list[dict]:
        findings = [
            {"file": "src/utils/cache.py",  "line": 47,  "match": "eval(user_input)",
             "type": "injection_sink"},
            {"file": "src/api/auth.py",     "line": 112, "match": "MD5(password)",
             "type": "weak_crypto"},
            {"file": "src/db/models.py",    "line": 203, "match": 'query = "SELECT * FROM users WHERE id=" + user_id',
             "type": "sql_injection"},
            {"file": "src/api/users.py",    "line": 78,  "match": "requests.get(url)",
             "type": "potential_ssrf"},
        ]
        return findings


# ---------------------------------------------------------------------------
# Security Scanner  (security.scan/v1)
# ---------------------------------------------------------------------------

@dataclass
class CVE:
    package: str
    installed_version: str
    cve_id: str
    severity: str
    fix_version: str


@dataclass
class SecurityScanResult:
    repo: str
    scan_timestamp: str
    cves: list[CVE] = field(default_factory=list)
    sast_findings: list[dict] = field(default_factory=list)
    overall_risk_score: int = 0

    @property
    def critical_count(self) -> int:
        return sum(1 for c in self.cves if c.severity == "CRITICAL")

    @property
    def high_count(self) -> int:
        return sum(1 for c in self.cves if c.severity == "HIGH")


class SecurityScannerService:
    """Simulates snyk-scanner."""

    def scan(self, repo: str) -> SecurityScanResult:
        cves = [
            CVE("pillow",     "9.0.1",  "CVE-2023-44271", "CRITICAL", "10.0.0"),
            CVE("requests",   "2.28.0", "CVE-2023-32681", "HIGH",     "2.31.0"),
            CVE("cryptography","39.0.0","CVE-2023-49083", "HIGH",     "41.0.6"),
            CVE("urllib3",    "1.26.14","CVE-2023-45803", "MEDIUM",   "2.0.7"),
            CVE("certifi",    "2022.12.7","CVE-2023-37920","MEDIUM",  "2023.7.22"),
            CVE("PyYAML",     "5.4.1",  "CVE-2022-1471",  "LOW",      "6.0"),
        ]
        sast = [
            {"id": "CWE-78",  "title": "OS Command Injection",    "file": "src/utils/cache.py",  "line": 47, "severity": "CRITICAL"},
            {"id": "CWE-327", "title": "Weak Cryptographic Algorithm", "file": "src/api/auth.py","line": 112,"severity": "HIGH"},
            {"id": "CWE-89",  "title": "SQL Injection",            "file": "src/db/models.py",   "line": 203,"severity": "CRITICAL"},
            {"id": "CWE-918", "title": "Server-Side Request Forgery","file": "src/api/users.py", "line": 78, "severity": "HIGH"},
        ]
        return SecurityScanResult(
            repo=repo,
            scan_timestamp=_now(),
            cves=cves,
            sast_findings=sast,
            overall_risk_score=72,
        )


# ---------------------------------------------------------------------------
# Code Quality Service  (code.quality/v1)
# ---------------------------------------------------------------------------

@dataclass
class CodeQualityResult:
    repo: str
    coverage_pct: float
    tech_debt_hours: float
    duplication_pct: float
    maintainability_index: float
    complexity_violations: list[dict] = field(default_factory=list)

    @property
    def grade(self) -> str:
        if self.maintainability_index >= 80:
            return "A"
        if self.maintainability_index >= 65:
            return "B"
        if self.maintainability_index >= 50:
            return "C"
        return "D"


class CodeQualityService:
    """Simulates sonarqube."""

    def analyze(self, repo: str) -> CodeQualityResult:
        return CodeQualityResult(
            repo=repo,
            coverage_pct=74.2,
            tech_debt_hours=18.5,
            duplication_pct=6.3,
            maintainability_index=68.4,
            complexity_violations=[
                {"file": "src/api/users.py",  "function": "handle_request",  "complexity": 24, "threshold": 15},
                {"file": "src/db/models.py",  "function": "build_query",     "complexity": 19, "threshold": 15},
                {"file": "src/api/auth.py",   "function": "authenticate",    "complexity": 17, "threshold": 15},
            ],
        )


# ---------------------------------------------------------------------------
# Metrics Service  (metrics.query/v1)
# ---------------------------------------------------------------------------

@dataclass
class MetricPoint:
    timestamp: str
    value: float


@dataclass
class MetricsQueryResult:
    endpoint: str
    window_minutes: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    error_rate_pct: float
    requests_per_sec: float
    baseline_p99_ms: float
    anomalies: list[str] = field(default_factory=list)


class MetricsService:
    """Simulates grafana-metrics."""

    def query(self, endpoint: str, window_minutes: int = 30) -> MetricsQueryResult:
        anomalies = [
            "p99 latency 3.8x above 7-day baseline",
            "Error rate spiked from 0.1% to 4.7% at 14:32 UTC",
            "CPU utilization on api-pod-3 at 94% (threshold: 80%)",
            "DB connection pool exhausted (100/100 connections in use)",
        ]
        return MetricsQueryResult(
            endpoint=endpoint,
            window_minutes=window_minutes,
            p50_ms=245.0,
            p95_ms=892.0,
            p99_ms=2340.0,
            error_rate_pct=4.7,
            requests_per_sec=1840.0,
            baseline_p99_ms=620.0,
            anomalies=anomalies,
        )


# ---------------------------------------------------------------------------
# Issue Tracker  (issue.create/v1, issue.update/v1)
# ---------------------------------------------------------------------------

@dataclass
class Issue:
    issue_id: str
    title: str
    priority: str
    status: str
    url: str
    assigned_to: str


class IssueTrackerService:
    """Simulates jira-tracker / linear-tracker."""

    def create(self, title: str, priority: str = "P2", assigned_to: str = "on-call") -> Issue:
        issue_id = f"ENG-{random.randint(4000, 9999)}"
        return Issue(
            issue_id=issue_id,
            title=title,
            priority=priority,
            status="OPEN",
            url=f"https://jira.example.com/browse/{issue_id}",
            assigned_to=assigned_to,
        )

    def update(self, issue_id: str, status: str, comment: str = "") -> Issue:
        return Issue(
            issue_id=issue_id,
            title="(updated)",
            priority="P2",
            status=status,
            url=f"https://jira.example.com/browse/{issue_id}",
            assigned_to="on-call",
        )


# ---------------------------------------------------------------------------
# Notification Service  (notification.send/v1)
# ---------------------------------------------------------------------------

@dataclass
class NotificationResult:
    channel: str
    message_id: str
    delivered: bool
    timestamp: str


class NotificationService:
    """Simulates slack-notifier / teams-notifier."""

    def send(self, channel: str, subject: str, body: str) -> NotificationResult:
        msg_id = f"msg_{random.randint(10000, 99999)}"
        print(f"  [SLACK -> #{channel}] {subject}")
        return NotificationResult(
            channel=channel,
            message_id=msg_id,
            delivered=True,
            timestamp=_now(),
        )


# ---------------------------------------------------------------------------
# Artifact Storage  (artifact.store/v1)
# ---------------------------------------------------------------------------

@dataclass
class ArtifactStoreResult:
    artifact_id: str
    s3_uri: str
    size_bytes: int
    checksum: str
    stored_at: str


class ArtifactStorageService:
    """Simulates s3-storage."""

    def store(self, repo: str, version: str, artifact_type: str = "release") -> ArtifactStoreResult:
        artifact_id = f"{repo.replace('/', '-')}-{version}-{artifact_type}"
        return ArtifactStoreResult(
            artifact_id=artifact_id,
            s3_uri=f"s3://capmesh-releases/{repo}/{version}/{artifact_type}.tar.gz",
            size_bytes=84_204_032,
            checksum="sha256:9f3a1c2b8e7d4f05a612b3",
            stored_at=_now(),
        )


# ---------------------------------------------------------------------------
# Test Generator  (test.generate/v1)
# ---------------------------------------------------------------------------

@dataclass
class TestGenerationResult:
    repo: str
    tests_generated: int
    files_created: list[str]
    coverage_before: float
    coverage_after: float
    test_suite_pass: bool


class TestGeneratorService:
    """Simulates autogen-test-generator."""

    def generate(self, repo: str) -> TestGenerationResult:
        return TestGenerationResult(
            repo=repo,
            tests_generated=47,
            files_created=[
                "tests/test_users_edge_cases.py",
                "tests/test_auth_security.py",
                "tests/integration/test_api_contract.py",
            ],
            coverage_before=74.2,
            coverage_after=89.1,
            test_suite_pass=True,
        )


# ---------------------------------------------------------------------------
# Deploy Service  (deploy.execute/v1)
# ---------------------------------------------------------------------------

@dataclass
class DeployResult:
    repo: str
    version: str
    environment: str
    strategy: str
    status: str
    canary_health: str
    smoke_tests_passed: int
    smoke_tests_total: int
    rolled_back: bool
    deploy_url: str
    deployed_at: str


class DeployService:
    """Simulates strands-deploy-agent."""

    def deploy(self, repo: str, version: str, environment: str = "staging",
               strategy: str = "blue-green") -> DeployResult:
        return DeployResult(
            repo=repo,
            version=version,
            environment=environment,
            strategy=strategy,
            status="SUCCESS",
            canary_health="HEALTHY",
            smoke_tests_passed=23,
            smoke_tests_total=23,
            rolled_back=False,
            deploy_url=f"https://deploy.example.com/{repo}/{version}",
            deployed_at=_now(),
        )


# ---------------------------------------------------------------------------
# Data Query Service  (data.query/v1)
# ---------------------------------------------------------------------------

@dataclass
class DataQueryResult:
    query_id: str
    rows_sampled: int
    tables: list[str]
    anomalies_found: int
    schema_drifts: list[str]
    null_ratio_by_column: dict[str, float]


class DataQueryService:
    """Simulates postgres-query."""

    def query(self, dataset: str) -> DataQueryResult:
        return DataQueryResult(
            query_id=f"q_{random.randint(1000, 9999)}",
            rows_sampled=10000,
            tables=["events", "users", "sessions", "aggregates"],
            anomalies_found=3,
            schema_drifts=["events: new column 'device_type' (unexpected)"],
            null_ratio_by_column={
                "events.device_type": 0.42,
                "users.last_login":   0.08,
                "sessions.duration":  0.003,
            },
        )
