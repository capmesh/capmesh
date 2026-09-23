import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from capmesh.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def set_capmesh_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point all CLI commands to a temp registry root."""
    monkeypatch.setenv("CAPMESH_ROOT", str(tmp_path))


# --- init ---


def test_agent_init(tmp_path: Path):
    target = tmp_path / "my-agent"
    result = runner.invoke(
        app,
        ["agent", "init", "--namespace", "myorg", "--name", "my-agent",
         "--version", "0.1.0", "--owner", "me", "--directory", str(target)],
    )
    assert result.exit_code == 0, result.output
    assert (target / "manifest.yaml").exists()


def test_skill_init(tmp_path: Path):
    target = tmp_path / "my-skill"
    result = runner.invoke(
        app,
        ["skill", "init", "--namespace", "myorg", "--name", "my-skill",
         "--version", "0.1.0", "--owner", "me", "--directory", str(target)],
    )
    assert result.exit_code == 0, result.output
    assert (target / "manifest.yaml").exists()


def test_tool_init(tmp_path: Path):
    target = tmp_path / "my-tool"
    result = runner.invoke(
        app,
        ["tool", "init", "--namespace", "myorg", "--name", "my-tool",
         "--version", "0.1.0", "--owner", "me", "--directory", str(target)],
    )
    assert result.exit_code == 0, result.output
    assert (target / "manifest.yaml").exists()


# --- build ---


def test_build(tmp_path: Path):
    # First init
    target = tmp_path / "my-agent"
    runner.invoke(
        app,
        ["agent", "init", "--namespace", "myorg", "--name", "my-agent",
         "--version", "0.1.0", "--owner", "me", "--directory", str(target)],
    )

    # Then build
    result = runner.invoke(app, ["agent", "build", "--directory", str(target)])
    assert result.exit_code == 0, result.output
    assert "digest:" in result.output.lower() or "sha256:" in result.output.lower()


# --- register ---


def test_register(tmp_path: Path):
    # Init
    target = tmp_path / "my-agent"
    runner.invoke(
        app,
        ["agent", "init", "--namespace", "myorg", "--name", "my-agent",
         "--version", "0.1.0", "--owner", "me", "--directory", str(target)],
    )

    # Register
    result = runner.invoke(
        app, ["agent", "register", "--file", str(target / "manifest.yaml")]
    )
    assert result.exit_code == 0, result.output
    assert "registered" in result.output.lower()


# --- inspect ---


def test_inspect(tmp_path: Path):
    # Init + register
    target = tmp_path / "my-agent"
    runner.invoke(
        app,
        ["agent", "init", "--namespace", "myorg", "--name", "my-agent",
         "--version", "0.1.0", "--owner", "me", "--directory", str(target)],
    )
    runner.invoke(app, ["agent", "register", "--file", str(target / "manifest.yaml")])

    # Inspect
    result = runner.invoke(app, ["agent", "inspect", "myorg", "my-agent", "0.1.0"])
    assert result.exit_code == 0, result.output
    assert "my-agent" in result.output


def test_inspect_json(tmp_path: Path):
    target = tmp_path / "my-agent"
    runner.invoke(
        app,
        ["agent", "init", "--namespace", "myorg", "--name", "my-agent",
         "--version", "0.1.0", "--owner", "me", "--directory", str(target)],
    )
    runner.invoke(app, ["agent", "register", "--file", str(target / "manifest.yaml")])

    result = runner.invoke(
        app, ["agent", "inspect", "myorg", "my-agent", "0.1.0", "--json"]
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["metadata"]["name"] == "my-agent"


# --- search ---


def test_search(tmp_path: Path):
    # Register an agent
    target = tmp_path / "my-agent"
    runner.invoke(
        app,
        ["agent", "init", "--namespace", "security", "--name", "sec-reviewer",
         "--version", "1.0.0", "--owner", "me", "--directory", str(target)],
    )
    runner.invoke(app, ["agent", "register", "--file", str(target / "manifest.yaml")])

    result = runner.invoke(app, ["search", "security"])
    assert result.exit_code == 0, result.output
    assert "sec-reviewer" in result.output


def test_search_json(tmp_path: Path):
    target = tmp_path / "my-agent"
    runner.invoke(
        app,
        ["agent", "init", "--namespace", "security", "--name", "sec-reviewer",
         "--version", "1.0.0", "--owner", "me", "--directory", str(target)],
    )
    runner.invoke(app, ["agent", "register", "--file", str(target / "manifest.yaml")])

    result = runner.invoke(app, ["search", "security", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["name"] == "sec-reviewer"


# --- tag ---


def test_tag(tmp_path: Path):
    target = tmp_path / "my-agent"
    runner.invoke(
        app,
        ["agent", "init", "--namespace", "myorg", "--name", "my-agent",
         "--version", "0.1.0", "--owner", "me", "--directory", str(target)],
    )
    runner.invoke(app, ["agent", "register", "--file", str(target / "manifest.yaml")])

    result = runner.invoke(app, ["tag", "myorg", "my-agent", "0.1.0", "stable"])
    assert result.exit_code == 0, result.output
    assert "stable" in result.output.lower()


# --- register rejects duplicate with different content ---


def test_register_rejects_different_digest(tmp_path: Path):
    target1 = tmp_path / "v1"
    runner.invoke(
        app,
        ["agent", "init", "--namespace", "myorg", "--name", "my-agent",
         "--version", "0.1.0", "--owner", "me", "--directory", str(target1)],
    )
    runner.invoke(app, ["agent", "register", "--file", str(target1 / "manifest.yaml")])

    # Create a different manifest with the same name+version
    target2 = tmp_path / "v2"
    runner.invoke(
        app,
        ["agent", "init", "--namespace", "myorg", "--name", "my-agent",
         "--version", "0.1.0", "--owner", "different-owner", "--directory", str(target2)],
    )
    result = runner.invoke(
        app, ["agent", "register", "--file", str(target2 / "manifest.yaml")]
    )
    assert result.exit_code != 0 or "error" in result.output.lower() or "already exists" in result.output.lower()
