from pathlib import Path

from capmesh.models import Kind, Visibility, Status
from capmesh.cli.scaffold import scaffold_manifest, write_scaffold


def test_scaffold_agent():
    m = scaffold_manifest(Kind.AGENT, "myorg", "my-agent", "0.1.0", "me")
    assert m.metadata.kind == Kind.AGENT
    assert m.metadata.namespace == "myorg"
    assert m.metadata.name == "my-agent"
    assert m.metadata.version == "0.1.0"
    assert m.metadata.owner == "me"
    assert m.interface.protocol == "a2a"
    assert m.governance.visibility == Visibility.PRIVATE
    assert m.governance.status == Status.APPROVED
    assert m.provides == []
    assert m.requires == []


def test_scaffold_skill():
    m = scaffold_manifest(Kind.SKILL, "myorg", "my-skill", "0.1.0", "me")
    assert m.interface.protocol == "skill"
    assert m.interface.instructions == "SKILL.md"


def test_scaffold_tool():
    m = scaffold_manifest(Kind.TOOL, "myorg", "my-tool", "0.1.0", "me")
    assert m.interface.protocol == "mcp"


def test_write_scaffold(tmp_path: Path):
    m = scaffold_manifest(Kind.AGENT, "myorg", "my-agent", "0.1.0", "me")
    path = write_scaffold(tmp_path, m)
    assert path.exists()
    assert path.name == "manifest.yaml"
    content = path.read_text()
    assert "my-agent" in content
