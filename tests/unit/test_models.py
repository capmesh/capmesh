from capmesh.models.enums import Kind, Visibility, Status


def test_kind_enum_has_three_values():
    assert set(Kind) == {Kind.AGENT, Kind.SKILL, Kind.TOOL}


def test_visibility_enum_has_three_values():
    assert set(Visibility) == {Visibility.PUBLIC, Visibility.ORGANIZATION, Visibility.PRIVATE}


def test_status_enum_has_three_values():
    assert set(Status) == {Status.APPROVED, Status.DEPRECATED, Status.REVOKED}


import pytest
from pydantic import ValidationError
from capmesh.models.interfaces import (
    A2AInterface,
    MCPInterface,
    SkillInterface,
    RESTInterface,
)


def test_a2a_interface():
    iface = A2AInterface(protocol="a2a", endpoint="https://agent.example")
    assert iface.protocol == "a2a"
    assert iface.endpoint == "https://agent.example"


def test_a2a_interface_rejects_wrong_protocol():
    with pytest.raises(ValidationError):
        A2AInterface(protocol="mcp", endpoint="https://agent.example")


def test_mcp_interface():
    iface = MCPInterface(protocol="mcp", server="github-mcp", tool_name="search")
    assert iface.protocol == "mcp"
    assert iface.server == "github-mcp"
    assert iface.tool_name == "search"


def test_mcp_interface_optional_tool_name():
    iface = MCPInterface(protocol="mcp", server="github-mcp")
    assert iface.tool_name is None


def test_skill_interface():
    iface = SkillInterface(
        protocol="skill", instructions="SKILL.md", assets=["templates/"]
    )
    assert iface.protocol == "skill"
    assert iface.instructions == "SKILL.md"
    assert iface.assets == ["templates/"]


def test_skill_interface_empty_assets():
    iface = SkillInterface(protocol="skill", instructions="SKILL.md", assets=[])
    assert iface.assets == []


def test_rest_interface():
    iface = RESTInterface(
        protocol="rest",
        endpoint="https://api.example/v1",
        auth_type="bearer",
        request_mapping={"input": "$.body"},
        response_mapping={"output": "$.result"},
    )
    assert iface.protocol == "rest"
    assert iface.auth_type == "bearer"


from capmesh.models.manifest import (
    CapabilityRef,
    Governance,
    HealthCheck,
    Metadata,
    Manifest,
)
from capmesh.models.enums import Kind, Visibility, Status


def test_capability_ref():
    ref = CapabilityRef(capability="security.code.review", contract="v1")
    assert ref.capability == "security.code.review"
    assert ref.contract == "v1"


def test_governance_defaults():
    gov = Governance(
        visibility=Visibility.PUBLIC,
        status=Status.APPROVED,
    )
    assert gov.environment == []
    assert gov.labels == {}


def test_health_check():
    hc = HealthCheck(enabled=True, endpoint="https://agent.example/health", interval_seconds=30)
    assert hc.enabled is True
    assert hc.interval_seconds == 30


def test_health_check_disabled():
    hc = HealthCheck(enabled=False)
    assert hc.endpoint is None
    assert hc.interval_seconds == 60


def test_metadata():
    meta = Metadata(
        api_version="capmesh.io/v1alpha1",
        kind=Kind.AGENT,
        namespace="security",
        name="security-reviewer",
        version="2.4.0",
        owner="security-engineering",
    )
    assert meta.digest is None
    assert meta.kind == Kind.AGENT


def test_manifest_agent():
    manifest = Manifest(
        metadata=Metadata(
            api_version="capmesh.io/v1alpha1",
            kind=Kind.AGENT,
            namespace="security",
            name="security-reviewer",
            version="2.4.0",
            owner="security-engineering",
        ),
        provides=[CapabilityRef(capability="security.code.review", contract="v1")],
        requires=[CapabilityRef(capability="repository.read", contract="v1")],
        interface=A2AInterface(protocol="a2a", endpoint="https://security-agent.example"),
        governance=Governance(
            visibility=Visibility.ORGANIZATION,
            status=Status.APPROVED,
        ),
    )
    assert manifest.metadata.name == "security-reviewer"
    assert len(manifest.provides) == 1
    assert manifest.interface.protocol == "a2a"


def test_manifest_skill():
    manifest = Manifest(
        metadata=Metadata(
            api_version="capmesh.io/v1alpha1",
            kind=Kind.SKILL,
            namespace="security",
            name="security-code-review",
            version="1.2.0",
            owner="security-engineering",
        ),
        provides=[CapabilityRef(capability="security.code.review", contract="v1")],
        requires=[
            CapabilityRef(capability="repository.read", contract="v1"),
            CapabilityRef(capability="security.scan", contract="v1"),
        ],
        interface=SkillInterface(protocol="skill", instructions="SKILL.md", assets=[]),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )
    assert manifest.metadata.kind == Kind.SKILL
    assert len(manifest.requires) == 2


def test_manifest_tool():
    manifest = Manifest(
        metadata=Metadata(
            api_version="capmesh.io/v1alpha1",
            kind=Kind.TOOL,
            namespace="repository",
            name="github-reader",
            version="1.0.0",
            owner="platform-team",
        ),
        provides=[CapabilityRef(capability="repository.read", contract="v1")],
        requires=[],
        interface=MCPInterface(protocol="mcp", server="github-mcp", tool_name="read_file"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )
    assert manifest.interface.protocol == "mcp"
    assert manifest.interface.tool_name == "read_file"


def test_manifest_rejects_missing_fields():
    with pytest.raises(ValidationError):
        Manifest(
            metadata=Metadata(
                api_version="capmesh.io/v1alpha1",
                kind=Kind.AGENT,
                namespace="security",
                name="test",
                version="1.0.0",
                owner="test",
            ),
            provides=[],
            requires=[],
            # missing interface and governance
        )
