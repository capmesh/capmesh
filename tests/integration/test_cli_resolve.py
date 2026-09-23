import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from capmesh.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def set_capmesh_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CAPMESH_ROOT", str(tmp_path))


def _register_agent(tmp_path: Path, namespace: str = "security", name: str = "reviewer", version: str = "2.4.0"):
    target = tmp_path / f"{name}-{version}"
    runner.invoke(app, [
        "agent", "init",
        "--namespace", namespace, "--name", name,
        "--version", version, "--owner", "test-team",
        "--directory", str(target),
    ])
    runner.invoke(app, ["agent", "register", "--file", str(target / "manifest.yaml")])


def test_providers_command(tmp_path: Path):
    _register_agent(tmp_path)
    result = runner.invoke(app, ["providers", "security.code.review"])
    # Scaffolded manifests have empty provides, so no providers found
    assert result.exit_code == 0


def test_providers_json(tmp_path: Path):
    result = runner.invoke(app, ["providers", "security.code.review", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)


def test_resolve_no_providers(tmp_path: Path):
    result = runner.invoke(app, ["resolve", "nonexistent.capability"])
    assert result.exit_code != 0 or "no" in result.output.lower()


def test_resolve_json_no_providers(tmp_path: Path):
    result = runner.invoke(app, ["resolve", "nonexistent.capability", "--json"])
    assert result.exit_code != 0 or "error" in result.output.lower()


def test_providers_empty_json(tmp_path: Path):
    result = runner.invoke(app, ["providers", "no.such.capability", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data == []


def test_resolve_with_contract_flag(tmp_path: Path):
    result = runner.invoke(app, ["resolve", "nonexistent.capability", "--contract", "v2"])
    # Should fail gracefully — capability doesn't exist
    assert result.exit_code != 0 or "no" in result.output.lower()


def test_providers_with_contract_flag(tmp_path: Path):
    result = runner.invoke(app, ["providers", "security.code.review", "--contract", "v2", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
