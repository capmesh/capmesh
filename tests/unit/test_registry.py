import pytest
from pathlib import Path

from capmesh.models import (
    A2AInterface,
    CapabilityRef,
    Governance,
    Kind,
    Manifest,
    Metadata,
    Status,
    Visibility,
)
from capmesh.registry import Registry
from capmesh.registry.storage import DuplicateVersionError


def _agent_manifest() -> Manifest:
    return Manifest(
        metadata=Metadata(
            kind=Kind.AGENT,
            namespace="security",
            name="security-reviewer",
            version="2.4.0",
            owner="security-engineering",
        ),
        provides=[CapabilityRef(capability="security.code.review", contract="v1")],
        requires=[CapabilityRef(capability="repository.read", contract="v1")],
        interface=A2AInterface(protocol="a2a", endpoint="https://security-agent.example"),
        governance=Governance(visibility=Visibility.ORGANIZATION, status=Status.APPROVED),
    )


@pytest.fixture
def registry(tmp_path: Path) -> Registry:
    return Registry(root=tmp_path)


def test_register_and_get(registry: Registry):
    digest = registry.register(_agent_manifest())
    assert len(digest) == 64

    manifest = registry.get("security", "security-reviewer", "2.4.0")
    assert manifest is not None
    assert manifest.metadata.name == "security-reviewer"


def test_register_idempotent(registry: Registry):
    d1 = registry.register(_agent_manifest())
    d2 = registry.register(_agent_manifest())
    assert d1 == d2


def test_register_rejects_different_digest(registry: Registry):
    registry.register(_agent_manifest())
    m2 = _agent_manifest()
    m2.interface = A2AInterface(protocol="a2a", endpoint="https://different.example")
    with pytest.raises(DuplicateVersionError):
        registry.register(m2)


def test_providers_for(registry: Registry):
    registry.register(_agent_manifest())
    providers = registry.providers_for("security.code.review", "v1")
    assert len(providers) == 1
    assert providers[0].name == "security-reviewer"


def test_search(registry: Registry):
    registry.register(_agent_manifest())
    results = registry.search("security")
    assert len(results) == 1


def test_list_all(registry: Registry):
    registry.register(_agent_manifest())
    all_items = registry.list()
    assert len(all_items) == 1


def test_tag(registry: Registry):
    registry.register(_agent_manifest())
    registry.tag("security", "security-reviewer", "2.4.0", "stable")
    items = registry.list()
    assert "stable" in items[0].tags


def test_delete(registry: Registry):
    registry.register(_agent_manifest())
    registry.delete("security", "security-reviewer", "2.4.0")
    providers = registry.providers_for("security.code.review", "v1")
    assert len(providers) == 0
