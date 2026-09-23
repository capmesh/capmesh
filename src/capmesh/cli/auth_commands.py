import os
import yaml
import typer
from pathlib import Path
from rich.console import Console

console = Console()
login_app = typer.Typer()

@login_app.callback(invoke_without_command=True)
def login(
    ctx: typer.Context,
    server: str = typer.Option("http://localhost:8080", help="Registry server URL"),
    api_key: str = typer.Option(..., prompt=True, hide_input=True, help="API key"),
) -> None:
    """Authenticate with a CapMesh registry server."""
    root_str = os.environ.get("CAPMESH_ROOT")
    root = Path(root_str) if root_str else Path.home() / ".capmesh"
    root.mkdir(parents=True, exist_ok=True)

    config_path = root / "config.yaml"
    config = {}
    if config_path.exists():
        config = yaml.safe_load(config_path.read_text()) or {}

    config["server"] = server
    config["api_key"] = api_key
    config_path.write_text(yaml.dump(config, default_flow_style=False))

    console.print(f"[green]Logged in to {server}[/green]")
    console.print(f"  Config saved to {config_path}")
