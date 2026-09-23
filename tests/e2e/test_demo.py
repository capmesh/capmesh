import sqlite3
from pathlib import Path

import pytest

from capmesh.adapters.defaults import default_adapter_registry
from capmesh.models import (
    A2AInterface, CapabilityRef, Governance, Kind, MCPInterface,
    Manifest, Metadata, SkillInterface, Status, Visibility,
)
from capmesh.models.resolution import CallerContext, ResolveRequest
from capmesh.policy import default_policy_engine
from capmesh.registry import Registry
from capmesh.resolver import Resolver, ResolutionError
from capmesh.telemetry import TraceStore


@pytest.fixture
def system(tmp_path: Path):
    registry = Registry(root=tmp_path)
    policy = default_policy_engine()
    db = sqlite3.connect(str(tmp_path / "traces.db"))
    db.row_factory = sqlite3.Row
    trace_store = TraceStore(db)
    trace_store.init_schema()
    resolver = Resolver(registry=registry, policy_engine=policy, trace_store=trace_store)
    adapter_reg = default_adapter_registry(resolver=resolver)
    resolver._adapter_registry = adapter_reg
    return registry, resolver, trace_store


def _agent(namespace, name, version, capability, contract="v1", endpoint="https://a.example"):
    return Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace=namespace, name=name, version=version, owner="team"),
        provides=[CapabilityRef(capability=capability, contract=contract)],
        requires=[], interface=A2AInterface(protocol="a2a", endpoint=endpoint),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )


def _tool(namespace, name, version, capability, server="mcp-server", tool_name="tool"):
    return Manifest(
        metadata=Metadata(kind=Kind.TOOL, namespace=namespace, name=name, version=version, owner="team"),
        provides=[CapabilityRef(capability=capability, contract="v1")],
        requires=[], interface=MCPInterface(protocol="mcp", server=server, tool_name=tool_name),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )


def _skill(namespace, name, version, capability, requires_caps):
    return Manifest(
        metadata=Metadata(kind=Kind.SKILL, namespace=namespace, name=name, version=version, owner="team"),
        provides=[CapabilityRef(capability=capability, contract="v1")],
        requires=[CapabilityRef(capability=c, contract="v1") for c in requires_caps],
        interface=SkillInterface(protocol="skill", instructions="SKILL.md", assets=[]),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )


def test_full_lifecycle(system):
    """V1 acceptance test: register, resolve, swap, trace."""
    registry, resolver, trace_store = system

    # 1. Register providers
    registry.register(_agent("security", "reviewer", "2.4.0", "security.code.review"))
    registry.register(_tool("repository", "github-reader", "1.0.0", "repository.read", "gh-mcp", "read_file"))

    # 2. Resolve security.code.review
    req = ResolveRequest(
        capability="security.code.review", contract="v1",
        caller=CallerContext(identity="orchestrator"),
    )
    res = resolver.resolve(req)
    assert res.provider_name == "reviewer"
    assert res.provider_version == "2.4.0"
    assert res.binding.protocol == "a2a"
    assert res.trace.outcome == "success"

    # 3. Verify trace is auditable
    trace = trace_store.get_trace(res.trace.trace_id)
    assert trace is not None
    assert trace.selected_provider == "security/reviewer:2.4.0"

    # 4. Add new provider dynamically (no restart)
    registry.register(_agent("performance", "perf-analyzer", "1.0.0", "performance.analyze"))
    perf_res = resolver.resolve(ResolveRequest(
        capability="performance.analyze", contract="v1",
        caller=CallerContext(identity="orchestrator"),
    ))
    assert perf_res.provider_name == "perf-analyzer"

    # 5. Swap provider — register higher version
    registry.register(_agent("security", "reviewer-v3", "3.0.0", "security.code.review"))
    res2 = resolver.resolve(req)
    assert res2.provider_version == "3.0.0"  # Highest semver wins
    assert res2.provider_name == "reviewer-v3"

    # 6. Verify trace count
    traces = trace_store.list_traces(limit=100)
    assert len(traces) >= 3


def test_skill_dual_binding(system):
    """Skill declares capabilities, resolver binds tools independently."""
    registry, resolver, _ = system

    # Register the tool that satisfies the skill's requirement
    registry.register(_tool("repository", "gh-reader", "1.0.0", "repository.read", "gh-mcp", "read"))

    # Register the skill
    registry.register(_skill("security", "review-skill", "1.0.0", "security.code.review", ["repository.read"]))

    # Resolve the skill
    res = resolver.resolve(ResolveRequest(
        capability="security.code.review", contract="v1",
        caller=CallerContext(identity="orchestrator"),
    ))
    assert res.binding.protocol == "skill"
    assert res.binding.connection["instructions"] == "SKILL.md"
    # Skill adapter should have resolved the required capability
    assert len(res.binding.connection["tool_bindings"]) == 1
    assert res.binding.connection["tool_bindings"][0]["protocol"] == "mcp"


def test_provider_swap_without_consumer_changes(system):
    """Replace a compatible provider without consumer code changes."""
    registry, resolver, _ = system

    # Register v1
    registry.register(_tool("repository", "github-reader", "1.0.0", "repository.read", "gh-mcp", "read"))

    # Resolve
    req = ResolveRequest(
        capability="repository.read", contract="v1",
        caller=CallerContext(identity="consumer"),
    )
    res1 = resolver.resolve(req)
    assert res1.provider_name == "github-reader"

    # Register a compatible replacement (higher version)
    registry.register(_tool("repository", "gitlab-reader", "2.0.0", "repository.read", "gl-mcp", "read"))

    # Same request, different provider — no consumer code changes
    res2 = resolver.resolve(req)
    assert res2.provider_version == "2.0.0"
    assert res2.provider_name == "gitlab-reader"


def test_cross_framework_discovery(system):
    """Discover providers from different agent frameworks."""
    registry, resolver, _ = system

    # LangGraph agent
    registry.register(_agent("security", "langgraph-reviewer", "1.0.0", "security.code.review"))
    # "Strands" agent (different framework, same capability)
    registry.register(_agent("security", "strands-reviewer", "2.0.0", "security.code.review"))

    # Both are discoverable
    providers = registry.providers_for("security.code.review", "v1")
    assert len(providers) == 2

    # Resolver picks highest version
    res = resolver.resolve(ResolveRequest(
        capability="security.code.review", contract="v1",
        caller=CallerContext(identity="orchestrator"),
    ))
    assert res.provider_version == "2.0.0"


def test_immutable_version_rejects_different_digest(system):
    """Same name+version with different digest is rejected."""
    registry, _, _ = system

    registry.register(_agent("security", "reviewer", "1.0.0", "security.code.review"))

    with pytest.raises(Exception):  # DuplicateVersionError
        registry.register(_agent("security", "reviewer", "1.0.0", "security.code.review",
                                 endpoint="https://different.example"))
