import pytest
from pathlib import Path
from typer.testing import CliRunner
from capmesh.cli import app

runner = CliRunner()

@pytest.fixture(autouse=True)
def set_capmesh_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CAPMESH_ROOT", str(tmp_path))

def test_login(tmp_path: Path):
    result = runner.invoke(app, ["login", "--server", "http://test:8080", "--api-key", "test-key"])
    assert result.exit_code == 0
    assert "logged in" in result.output.lower()
    # Verify config was saved
    import yaml
    config = yaml.safe_load((tmp_path / "config.yaml").read_text())
    assert config["server"] == "http://test:8080"
    assert config["api_key"] == "test-key"

def test_push_no_file():
    result = runner.invoke(app, ["agent", "push", "--file", "nonexistent.yaml"])
    assert result.exit_code != 0

def test_pull_no_server():
    result = runner.invoke(app, ["agent", "pull", "ns", "name", "1.0.0"])
    assert result.exit_code != 0
