from __future__ import annotations

from pathlib import Path

from capmesh.models.enums import Kind, Status, Visibility
from capmesh.models.interfaces import A2AInterface, MCPInterface, SkillInterface
from capmesh.models.manifest import CapabilityRef, Governance, Manifest, Metadata
from capmesh.models.serialization import manifest_to_yaml


def scaffold_manifest(
    kind: Kind,
    namespace: str,
    name: str,
    version: str,
    owner: str,
) -> Manifest:
    """Create a starter manifest with sensible defaults."""
    metadata = Metadata(
        kind=kind,
        namespace=namespace,
        name=name,
        version=version,
        owner=owner,
    )

    governance = Governance(
        visibility=Visibility.PRIVATE,
        status=Status.APPROVED,
    )

    if kind == Kind.AGENT:
        interface = A2AInterface(protocol="a2a", endpoint="https://your-agent.example")
    elif kind == Kind.SKILL:
        interface = SkillInterface(protocol="skill", instructions="SKILL.md", assets=[])
    else:
        interface = MCPInterface(protocol="mcp", server="your-mcp-server")

    return Manifest(
        metadata=metadata,
        provides=[],
        requires=[],
        interface=interface,
        governance=governance,
    )


def write_scaffold(directory: Path, manifest: Manifest) -> Path:
    """Write a manifest.yaml file to the given directory."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "manifest.yaml"
    path.write_text(manifest_to_yaml(manifest), encoding="utf-8")
    return path
