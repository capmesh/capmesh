import pytest
from pathlib import Path
from typer.testing import CliRunner
from capmesh.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def set_capmesh_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CAPMESH_ROOT", str(tmp_path))


def test_graph_no_providers():
    result = runner.invoke(app, ["graph", "nonexistent"])
    assert result.exit_code == 0
    assert "no providers" in result.output.lower()


def test_graph_json():
    result = runner.invoke(app, ["graph", "nonexistent", "--json"])
    assert result.exit_code == 0
    import json
    data = json.loads(result.output)
    assert data == []


def test_graph_json_with_contract():
    result = runner.invoke(app, ["graph", "nonexistent", "--contract", "v2", "--json"])
    assert result.exit_code == 0
    import json
    data = json.loads(result.output)
    assert data == []


def test_graph_with_contract_option():
    result = runner.invoke(app, ["graph", "nonexistent", "--contract", "v1"])
    assert result.exit_code == 0
    assert "no providers" in result.output.lower()
