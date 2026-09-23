import pytest
from pathlib import Path

from capmesh.models import (
    A2AInterface,
    CapabilityRef,
    Governance,
    Kind,
    Manifest,
    MCPInterface,
    Metadata,
    Status,
    Visibility,
)
from capmesh.registry.storage import Storage, ArtifactRecord, DuplicateVersionError


def _agent_manifest(version: str = "2.4.0") -> Manifest:
    return Manifest(
        metadata=Metadata(
            kind=Kind.AGENT,
            namespace="security",
            name="security-reviewer",
            version=version,
            owner="security-engineering",
        ),
        provides=[CapabilityRef(capability="security.code.review", contract="v1")],
        requires=[CapabilityRef(capability="repository.read", contract="v1")],
        interface=A2AInterface(protocol="a2a", endpoint="https://security-agent.example"),
        governance=Governance(visibility=Visibility.ORGANIZATION, status=Status.APPROVED),
    )


def _tool_manifest() -> Manifest:
    return Manifest(
        metadata=Metadata(
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


@pytest.fixture
def storage(tmp_path: Path) -> Storage:
    s = Storage(root=tmp_path)
    s.init()
    return s


def test_init_creates_dirs_and_db(tmp_path: Path):
    s = Storage(root=tmp_path)
    s.init()
    assert (tmp_path / "artifacts").is_dir()
    assert (tmp_path / "registry.db").is_file()


def test_save_and_load_manifest(storage: Storage):
    manifest = _agent_manifest()
    digest = storage.save_manifest(manifest)
    assert len(digest) == 64

    loaded = storage.load_manifest("security", "security-reviewer", "2.4.0")
    assert loaded is not None
    assert loaded.metadata.name == "security-reviewer"
    assert loaded.metadata.digest == digest


def test_save_idempotent_same_digest(storage: Storage):
    manifest = _agent_manifest()
    d1 = storage.save_manifest(manifest)
    d2 = storage.save_manifest(manifest)
    assert d1 == d2


def test_save_rejects_different_digest(storage: Storage):
    m1 = _agent_manifest()
    storage.save_manifest(m1)

    m2 = _agent_manifest()
    m2.interface = A2AInterface(protocol="a2a", endpoint="https://different.example")
    with pytest.raises(DuplicateVersionError):
        storage.save_manifest(m2)


def test_load_nonexistent_returns_none(storage: Storage):
    assert storage.load_manifest("nope", "nope", "1.0.0") is None


def test_find_providers(storage: Storage):
    storage.save_manifest(_agent_manifest())
    storage.save_manifest(_tool_manifest())

    providers = storage.find_providers("security.code.review", "v1")
    assert len(providers) == 1
    assert providers[0].name == "security-reviewer"

    providers = storage.find_providers("repository.read", "v1")
    assert len(providers) == 1
    assert providers[0].name == "github-reader"

    providers = storage.find_providers("nonexistent", "v1")
    assert len(providers) == 0


def test_search(storage: Storage):
    storage.save_manifest(_agent_manifest())
    storage.save_manifest(_tool_manifest())

    results = storage.search("security")
    assert len(results) == 1
    assert results[0].name == "security-reviewer"

    results = storage.search("github")
    assert len(results) == 1
    assert results[0].name == "github-reader"

    results = storage.search("nonexistent")
    assert len(results) == 0


def test_list_artifacts(storage: Storage):
    storage.save_manifest(_agent_manifest())
    storage.save_manifest(_tool_manifest())

    all_artifacts = storage.list_artifacts()
    assert len(all_artifacts) == 2

    agents = storage.list_artifacts(kind=Kind.AGENT)
    assert len(agents) == 1
    assert agents[0].kind == Kind.AGENT

    security = storage.list_artifacts(namespace="security")
    assert len(security) == 1


def test_add_tag(storage: Storage):
    storage.save_manifest(_agent_manifest())
    storage.add_tag("security", "security-reviewer", "2.4.0", "stable")

    artifacts = storage.list_artifacts()
    tagged = [a for a in artifacts if "stable" in a.tags]
    assert len(tagged) == 1


def test_delete_soft_deletes(storage: Storage):
    storage.save_manifest(_agent_manifest())
    storage.delete_artifact("security", "security-reviewer", "2.4.0")

    # YAML file still exists
    loaded = storage.load_manifest("security", "security-reviewer", "2.4.0")
    assert loaded is not None

    # But governance status is revoked
    assert loaded.governance.status == Status.REVOKED

    # And it doesn't show up in provider searches
    providers = storage.find_providers("security.code.review", "v1")
    assert len(providers) == 0


def test_rebuild_index(storage: Storage):
    storage.save_manifest(_agent_manifest())
    storage.save_manifest(_tool_manifest())

    count = storage.rebuild_index()
    assert count == 2

    # Verify searches still work after rebuild
    providers = storage.find_providers("security.code.review", "v1")
    assert len(providers) == 1
