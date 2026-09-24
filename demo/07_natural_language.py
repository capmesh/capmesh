#!/usr/bin/env python3
"""
NATURAL LANGUAGE CAPABILITY DISCOVERY

Instead of:  resolver.resolve("repository.read/v1")
Write:       resolver.need("read code from a repo")

CapMesh maps natural language to capability IDs using keyword matching,
synonyms, and descriptions. No LLM required. Deterministic and fast.
"""
import sqlite3
import tempfile
from pathlib import Path

from capmesh.adapters.defaults import default_adapter_registry
from capmesh.models import (
    A2AInterface, MCPInterface, RESTInterface, SkillInterface,
    CapabilityRef, Governance, Kind, Manifest, Metadata, Status, Visibility,
)
from capmesh.models.resolution import CallerContext
from capmesh.policy import default_policy_engine
from capmesh.registry import Registry
from capmesh.resolver import Resolver, ResolutionError
from capmesh.telemetry import TraceStore


def setup():
    root = Path(tempfile.mkdtemp(prefix="capmesh-nlp-"))
    registry = Registry(root=root)
    policy = default_policy_engine()
    db = sqlite3.connect(str(root / "traces.db"))
    db.row_factory = sqlite3.Row
    trace_store = TraceStore(db)
    trace_store.init_schema()
    resolver = Resolver(registry=registry, policy_engine=policy, trace_store=trace_store)
    adapter_reg = default_adapter_registry(resolver=resolver)
    resolver._adapter_registry = adapter_reg
    return registry, resolver


def main():
    registry, resolver = setup()
    caller = CallerContext(identity="agent")

    print()
    print("+" + "=" * 68 + "+")
    print("|  NATURAL LANGUAGE CAPABILITY DISCOVERY                             |")
    print("|  Say what you need. CapMesh finds who provides it.                |")
    print("+" + "=" * 68 + "+")

    # Register providers with descriptions
    providers = [
        Manifest(
            metadata=Metadata(kind=Kind.TOOL, namespace="repository", name="github-reader",
                              version="1.0.0", owner="platform"),
            provides=[
                CapabilityRef(capability="repository.read", contract="v1",
                              description="Read files and code from a git repository"),
                CapabilityRef(capability="repository.search", contract="v1",
                              description="Search for files and code patterns in a repository"),
            ],
            requires=[],
            interface=MCPInterface(protocol="mcp", server="github-mcp", tool_name="read"),
            governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        ),
        Manifest(
            metadata=Metadata(kind=Kind.AGENT, namespace="security", name="security-reviewer",
                              version="3.1.0", owner="security-team"),
            provides=[
                CapabilityRef(capability="security.code.review", contract="v1",
                              description="Review code for security vulnerabilities and OWASP issues"),
            ],
            requires=[CapabilityRef(capability="repository.read", contract="v1")],
            interface=A2AInterface(protocol="a2a", endpoint="https://sec-reviewer.example.com"),
            governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        ),
        Manifest(
            metadata=Metadata(kind=Kind.AGENT, namespace="security", name="vulnerability-scanner",
                              version="2.0.0", owner="security-team"),
            provides=[
                CapabilityRef(capability="security.scan", contract="v1",
                              description="Scan code for CVEs, SAST findings, and dependency vulnerabilities"),
            ],
            requires=[],
            interface=A2AInterface(protocol="a2a", endpoint="https://scanner.example.com"),
            governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        ),
        Manifest(
            metadata=Metadata(kind=Kind.TOOL, namespace="notifications", name="slack-notifier",
                              version="1.0.0", owner="platform"),
            provides=[
                CapabilityRef(capability="notification.send", contract="v1",
                              description="Send notifications and alerts to Slack channels or Teams"),
            ],
            requires=[],
            interface=RESTInterface(protocol="rest", endpoint="https://slack.example.com/api",
                                    auth_type="bearer", request_mapping={}, response_mapping={}),
            governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        ),
        Manifest(
            metadata=Metadata(kind=Kind.TOOL, namespace="issues", name="jira-tracker",
                              version="1.0.0", owner="platform"),
            provides=[
                CapabilityRef(capability="issue.create", contract="v1",
                              description="Create bug tickets and issues in project tracker"),
                CapabilityRef(capability="issue.update", contract="v1",
                              description="Update existing tickets and issues"),
            ],
            requires=[],
            interface=RESTInterface(protocol="rest", endpoint="https://jira.example.com/api",
                                    auth_type="bearer", request_mapping={}, response_mapping={}),
            governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        ),
        Manifest(
            metadata=Metadata(kind=Kind.AGENT, namespace="performance", name="perf-analyzer",
                              version="1.0.0", owner="platform"),
            provides=[
                CapabilityRef(capability="performance.analyze", contract="v1",
                              description="Analyze application performance, latency, and throughput"),
            ],
            requires=[],
            interface=A2AInterface(protocol="a2a", endpoint="https://perf.example.com"),
            governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        ),
        Manifest(
            metadata=Metadata(kind=Kind.TOOL, namespace="observability", name="grafana-metrics",
                              version="1.0.0", owner="platform"),
            provides=[
                CapabilityRef(capability="metrics.query", contract="v1",
                              description="Query metrics, dashboards, and monitoring data"),
            ],
            requires=[],
            interface=RESTInterface(protocol="rest", endpoint="https://grafana.example.com",
                                    auth_type="bearer", request_mapping={}, response_mapping={}),
            governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        ),
        Manifest(
            metadata=Metadata(kind=Kind.AGENT, namespace="testing", name="test-generator",
                              version="1.0.0", owner="platform"),
            provides=[
                CapabilityRef(capability="test.generate", contract="v1",
                              description="Generate unit tests and integration tests for code"),
            ],
            requires=[],
            interface=A2AInterface(protocol="a2a", endpoint="https://testgen.example.com"),
            governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        ),
        Manifest(
            metadata=Metadata(kind=Kind.AGENT, namespace="docs", name="doc-generator",
                              version="1.0.0", owner="platform"),
            provides=[
                CapabilityRef(capability="documentation.generate", contract="v1",
                              description="Generate documentation, READMEs, and API docs from code"),
            ],
            requires=[],
            interface=A2AInterface(protocol="a2a", endpoint="https://docgen.example.com"),
            governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        ),
        Manifest(
            metadata=Metadata(kind=Kind.AGENT, namespace="deployment", name="deploy-agent",
                              version="1.0.0", owner="platform"),
            provides=[
                CapabilityRef(capability="deploy.execute", contract="v1",
                              description="Deploy applications to staging or production environments"),
            ],
            requires=[],
            interface=A2AInterface(protocol="a2a", endpoint="https://deploy.example.com"),
            governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        ),
        Manifest(
            metadata=Metadata(kind=Kind.TOOL, namespace="database", name="db-connector",
                              version="1.0.0", owner="platform"),
            provides=[
                CapabilityRef(capability="data.query", contract="v1",
                              description="Query databases, run SQL, and fetch data"),
            ],
            requires=[],
            interface=MCPInterface(protocol="mcp", server="postgres-mcp", tool_name="query"),
            governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        ),
    ]

    print()
    print(f"  Registered {len(providers)} providers with capability descriptions.")
    for p in providers:
        registry.register(p)
    print()

    # =================================================================
    # PART 1: The old way vs the new way
    # =================================================================

    print("=" * 70)
    print("  BEFORE: Exact capability IDs (technical, rigid)")
    print("=" * 70)
    print()
    print("  resolver.resolve('repository.read/v1')      # must know the ID")
    print("  resolver.resolve('security.code.review/v1')  # must know the ID")
    print("  resolver.resolve('notification.send/v1')     # must know the ID")
    print()

    print("=" * 70)
    print("  AFTER: Natural language (human, flexible)")
    print("=" * 70)
    print()
    print("  resolver.need('read code from a repo')")
    print("  resolver.need('check for security vulnerabilities')")
    print("  resolver.need('notify the team')")
    print()

    # =================================================================
    # PART 2: Live demo — natural language queries
    # =================================================================

    print("=" * 70)
    print("  LIVE: Natural language -> capability -> provider")
    print("=" * 70)
    print()

    queries = [
        "read code from a repo",
        "scan for security vulnerabilities",
        "check for security issues",
        "notify the team",
        "send an alert",
        "create a bug ticket",
        "analyze performance",
        "query metrics",
        "generate tests",
        "write documentation",
        "deploy to production",
        "query the database",
        "search for code patterns",
        "review code for issues",
    ]

    print(f"  {'Natural Language Query':<40s} {'Matched Capability':<30s} {'Provider'}")
    print(f"  {'-'*40} {'-'*30} {'-'*30}")

    for query in queries:
        try:
            res = resolver.need(query, caller=caller)
            print(f"  {query:<40s} {res.trace.requested_capability:<30s} {res.provider_name}:{res.provider_version}")
        except ResolutionError:
            print(f"  {query:<40s} {'(no match)':<30s} -")

    # =================================================================
    # PART 3: Discovery — see what matches
    # =================================================================

    print()
    print("=" * 70)
    print("  DISCOVERY: See all matching capabilities ranked by relevance")
    print("=" * 70)
    print()

    discovery_queries = [
        "security",
        "read repo",
        "send notification",
        "database",
        "deploy",
    ]

    for query in discovery_queries:
        results = resolver.discover(query)
        print(f"  Query: '{query}'")
        if results:
            for r in results:
                print(f"    [{r.score:.1f}] {r.capability:<30s} ({r.reason})")
        else:
            print(f"    (no matches)")
        print()

    # =================================================================
    # PART 4: Agent workflow using natural language
    # =================================================================

    print("=" * 70)
    print("  AGENT WORKFLOW: PR Review using natural language")
    print("=" * 70)
    print()
    print("  An agent says what it needs in plain English.")
    print("  CapMesh figures out the rest.")
    print()

    workflow = [
        ("read the repository code", "Read PR diff"),
        ("review code for security issues", "Security review"),
        ("create a bug ticket", "Create findings ticket"),
        ("notify the team", "Alert the team"),
    ]

    for query, step_name in workflow:
        try:
            res = resolver.need(query, caller=caller)
            print(f"  Agent: '{query}'")
            print(f"    -> {res.trace.requested_capability} -> {res.provider_name} ({res.binding.protocol})")
            print()
        except ResolutionError as e:
            print(f"  Agent: '{query}'")
            print(f"    -> NO MATCH")
            print()

    # =================================================================
    # SUMMARY
    # =================================================================

    print("=" * 70)
    print("  HOW IT WORKS")
    print("=" * 70)
    print()
    print("  resolver.need() does 3 things:")
    print()
    print("  1. Try exact match (if query IS a capability ID, use it)")
    print("  2. Keyword match (decompose query + capability IDs into words)")
    print("  3. Synonym expansion ('notify' -> 'notification.send')")
    print()
    print("  No LLM required. Deterministic. Fast. Auditable.")
    print()
    print("  Still works with exact IDs too:")
    print("    resolver.need('repository.read')   # exact match, score 1.0")
    print("    resolver.need('read a repo')        # keyword match, score 0.8")
    print("    resolver.need('fetch source code')  # synonym match, score 0.5")
    print()
    print("  Three levels of specificity, one API:")
    print("    resolver.resolve(request)   # exact ID (strict)")
    print("    resolver.need('...')         # natural language (flexible)")
    print("    resolver.discover('...')     # explore what's available")
    print()


if __name__ == "__main__":
    main()
