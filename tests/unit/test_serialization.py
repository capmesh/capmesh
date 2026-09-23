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
from capmesh.models.serialization import (
    compute_digest,
    manifest_from_yaml,
    manifest_to_yaml,
)


def _sample_manifest() -> Manifest:
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


def test_manifest_to_yaml_returns_string():
    yaml_str = manifest_to_yaml(_sample_manifest())
    assert isinstance(yaml_str, str)
    assert "security-reviewer" in yaml_str


def test_manifest_roundtrip():
    original = _sample_manifest()
    yaml_str = manifest_to_yaml(original)
    restored = manifest_from_yaml(yaml_str)
    assert restored.metadata.name == original.metadata.name
    assert restored.metadata.kind == original.metadata.kind
    assert restored.provides == original.provides
    assert restored.requires == original.requires
    assert restored.interface == original.interface
    assert restored.governance == original.governance


def test_manifest_to_yaml_sorted_keys():
    yaml_str = manifest_to_yaml(_sample_manifest())
    lines = yaml_str.strip().split("\n")
    # Top-level keys should be alphabetically sorted
    top_keys = [l.split(":")[0] for l in lines if not l.startswith(" ") and ":" in l]
    assert top_keys == sorted(top_keys)


def test_compute_digest_is_deterministic():
    m = _sample_manifest()
    d1 = compute_digest(m)
    d2 = compute_digest(m)
    assert d1 == d2
    assert len(d1) == 64  # sha256 hex length


def test_compute_digest_changes_with_content():
    m1 = _sample_manifest()
    m2 = _sample_manifest()
    m2.metadata.version = "3.0.0"
    assert compute_digest(m1) != compute_digest(m2)


def test_digest_excluded_from_canonical_yaml():
    m = _sample_manifest()
    m.metadata.digest = "abc123"
    yaml_str = manifest_to_yaml(m)
    assert "abc123" not in yaml_str
