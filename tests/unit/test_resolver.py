import sqlite3
from pathlib import Path

import pytest

from capmesh.models import (
    A2AInterface,
    CapabilityRef,
    Governance,
    Kind,
    MCPInterface,
    Manifest,
    Metadata,
    RESTInterface,
    Status,
    Visibility,
)
from capmesh.models.resolution import CallerContext, ResolveRequest
from capmesh.policy import PolicyEngine, default_policy_engine
from capmesh.registry import Registry
from capmesh.resolver import Resolver, ResolutionError
from capmesh.telemetry import TraceStore


def _agent(
    version: str = "2.4.0",
    visibility: Visibility = Visibility.PUBLIC,
    status: Status = Status.APPROVED,
    environment: list[str] | None = None,
) -> Manifest:
    return Manifest(
        metadata=Metadata(
            kind=Kind.AGENT,
            namespace="security",
            name="reviewer",
            version=version,
            owner="security-team",
        ),
        provides=[CapabilityRef(capability="security.code.review", contract="v1")],
        requires=[],
        interface=A2AInterface(protocol="a2a", endpoint="https://agent.example"),
        governance=Governance(
            visibility=visibility,
            status=status,
            environment=environment or [],
        ),
    )


def _tool(version: str = "1.0.0") -> Manifest:
    return Manifest(
        metadata=Metadata(
            kind=Kind.TOOL,
            namespace="repository",
            name="github-reader",
            version=version,
            owner="platform",
        ),
        provides=[CapabilityRef(capability="repository.read", contract="v1")],
        requires=[],
        interface=MCPInterface(protocol="mcp", server="github-mcp", tool_name="read_file"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )


@pytest.fixture
def setup(tmp_path: Path):
    registry = Registry(root=tmp_path / "registry")
    policy = default_policy_engine()
    db = sqlite3.connect(str(tmp_path / "traces.db"))
    db.row_factory = sqlite3.Row
    trace_store = TraceStore(db)
    trace_store.init_schema()
    resolver = Resolver(registry=registry, policy_engine=policy, trace_store=trace_store)
    return registry, resolver, trace_store


def _request(
    capability: str = "security.code.review",
    contract: str = "v1",
    environment: str | None = None,
    version_constraint: str | None = None,
) -> ResolveRequest:
    return ResolveRequest(
        capability=capability,
        contract=contract,
        caller=CallerContext(identity="test-user", environment=environment),
        version_constraint=version_constraint,
    )


def test_resolve_single_provider(setup):
    registry, resolver, _ = setup
    registry.register(_agent("2.4.0"))

    resolution = resolver.resolve(_request())
    assert resolution.provider_name == "reviewer"
    assert resolution.provider_version == "2.4.0"
    assert resolution.binding.protocol == "a2a"
    assert resolution.trace.outcome == "success"


def test_resolve_selects_highest_version(setup):
    registry, resolver, _ = setup
    registry.register(_agent("1.0.0"))
    registry.register(_agent("2.4.0"))
    registry.register(_agent("2.0.0"))

    resolution = resolver.resolve(_request())
    assert resolution.provider_version == "2.4.0"


def test_resolve_with_version_constraint(setup):
    registry, resolver, _ = setup
    registry.register(_agent("1.0.0"))
    registry.register(_agent("2.4.0"))
    registry.register(_agent("3.0.0"))

    resolution = resolver.resolve(_request(version_constraint=">=1.0,<3.0"))
    assert resolution.provider_version == "2.4.0"


def test_resolve_filters_revoked(setup):
    registry, resolver, _ = setup
    registry.register(_agent("2.4.0", status=Status.REVOKED))
    registry.register(_agent("1.0.0"))

    resolution = resolver.resolve(_request())
    assert resolution.provider_version == "1.0.0"


def test_resolve_filters_by_policy(setup):
    registry, resolver, _ = setup
    registry.register(_agent("2.4.0", visibility=Visibility.PRIVATE))
    registry.register(_agent("1.0.0", visibility=Visibility.PUBLIC))

    resolution = resolver.resolve(_request())
    assert resolution.provider_version == "1.0.0"


def test_resolve_no_candidates_raises(setup):
    _, resolver, _ = setup

    with pytest.raises(ResolutionError, match="no_candidates"):
        resolver.resolve(_request(capability="nonexistent"))


def test_resolve_all_filtered_raises(setup):
    registry, resolver, _ = setup
    registry.register(_agent("2.4.0", visibility=Visibility.PRIVATE))

    with pytest.raises(ResolutionError, match="all_filtered"):
        resolver.resolve(_request())


def test_resolve_produces_trace(setup):
    registry, resolver, trace_store = setup
    registry.register(_agent("2.4.0"))

    resolution = resolver.resolve(_request())
    assert resolution.trace.trace_id.startswith("res_")

    stored = trace_store.get_trace(resolution.trace.trace_id)
    assert stored is not None
    assert stored.requested_capability == "security.code.review"


def test_resolve_trace_records_candidates(setup):
    registry, resolver, _ = setup
    registry.register(_agent("2.4.0", visibility=Visibility.PUBLIC))
    registry.register(_agent("1.0.0", visibility=Visibility.PRIVATE))

    resolution = resolver.resolve(_request())
    assert len(resolution.trace.candidates) == 2
    passed = [c for c in resolution.trace.candidates if c.passed]
    rejected = [c for c in resolution.trace.candidates if not c.passed]
    assert len(passed) == 1
    assert len(rejected) == 1


def test_resolve_without_trace_store(tmp_path: Path):
    registry = Registry(root=tmp_path / "registry")
    resolver = Resolver(
        registry=registry,
        policy_engine=default_policy_engine(),
        trace_store=None,
    )
    registry.register(_agent("2.4.0"))

    resolution = resolver.resolve(_request())
    assert resolution.provider_version == "2.4.0"
    assert resolution.trace.outcome == "success"


def test_resolve_environment_filter(setup):
    registry, resolver, _ = setup
    registry.register(_agent("2.4.0", environment=["production"]))

    # Staging caller can't access production provider
    with pytest.raises(ResolutionError):
        resolver.resolve(_request(environment="staging"))

    # Production caller can
    resolution = resolver.resolve(_request(environment="production"))
    assert resolution.provider_version == "2.4.0"


def test_resolve_binding_has_connection_info(setup):
    registry, resolver, _ = setup
    registry.register(_agent("2.4.0"))

    resolution = resolver.resolve(_request())
    assert resolution.binding.connection.get("endpoint") == "https://agent.example"
    assert resolution.binding.trace_id == resolution.trace.trace_id


def test_resolve_mcp_tool_connection(tmp_path: Path):
    registry = Registry(root=tmp_path / "registry")
    resolver = Resolver(
        registry=registry,
        policy_engine=default_policy_engine(),
        trace_store=None,
    )
    registry.register(_tool("1.0.0"))

    req = ResolveRequest(
        capability="repository.read",
        contract="v1",
        caller=CallerContext(identity="test-user"),
    )
    resolution = resolver.resolve(req)
    assert resolution.binding.protocol == "mcp"
    assert resolution.binding.connection.get("server") == "github-mcp"
    assert resolution.binding.connection.get("tool_name") == "read_file"


def test_resolve_trace_id_format(setup):
    registry, resolver, _ = setup
    registry.register(_agent("2.4.0"))

    resolution = resolver.resolve(_request())
    trace_id = resolution.trace.trace_id
    assert trace_id.startswith("res_")
    # After "res_" prefix there should be 12 hex chars
    suffix = trace_id[4:]
    assert len(suffix) == 12
    assert all(c in "0123456789abcdef" for c in suffix)


def test_resolve_version_constraint_excludes_all(setup):
    registry, resolver, _ = setup
    registry.register(_agent("2.4.0"))
    registry.register(_agent("1.0.0"))

    with pytest.raises(ResolutionError, match="all_filtered"):
        resolver.resolve(_request(version_constraint=">=10.0"))
