import json
import os
import yaml
from pathlib import Path

import typer
from rich.console import Console

console = Console()


def _load_config() -> dict:
    root_str = os.environ.get("CAPMESH_ROOT")
    root = Path(root_str) if root_str else Path.home() / ".capmesh"
    config_path = root / "config.yaml"
    if not config_path.exists():
        return {}
    return yaml.safe_load(config_path.read_text()) or {}


def _get_client():
    """Get httpx client with auth headers from config."""
    import httpx
    config = _load_config()
    server = config.get("server", "http://localhost:8080")
    headers = {}
    if config.get("api_key"):
        headers["Authorization"] = f"Bearer {config['api_key']}"
    return httpx.Client(base_url=server, headers=headers, timeout=30.0)


def add_push_command(artifact_app: typer.Typer, kind_value: str) -> None:
    """Add a push command to an artifact app."""
    @artifact_app.command()
    def push(
        file: str = typer.Option("manifest.yaml", help="Path to manifest.yaml"),
    ) -> None:
        """Push a manifest to the remote registry."""
        manifest_path = Path(file)
        if not manifest_path.exists():
            console.print(f"[red]Error: {manifest_path} not found[/red]")
            raise typer.Exit(code=1)

        yaml_str = manifest_path.read_text(encoding="utf-8")
        manifest_data = yaml.safe_load(yaml_str)

        try:
            client = _get_client()
            response = client.post("/v1/providers/register", json=manifest_data)
            if response.status_code == 200:
                data = response.json()
                console.print(f"[green]Pushed successfully[/green]")
                console.print(f"  Digest: sha256:{data.get('digest', 'unknown')[:16]}...")
            elif response.status_code == 409:
                console.print(f"[yellow]Already exists with same version[/yellow]")
            else:
                console.print(f"[red]Error: {response.status_code} - {response.text}[/red]")
                raise typer.Exit(code=1)
        except Exception as e:
            if "Connection" in str(type(e).__name__):
                console.print(f"[red]Error: Cannot connect to server. Run 'capmesh login' first.[/red]")
                raise typer.Exit(code=1)
            raise


def add_pull_command(artifact_app: typer.Typer, kind_value: str) -> None:
    """Add a pull command to an artifact app."""
    @artifact_app.command()
    def pull(
        namespace: str = typer.Argument(..., help="Artifact namespace"),
        name: str = typer.Argument(..., help="Artifact name"),
        version: str = typer.Argument(..., help="Artifact version"),
        directory: str = typer.Option(".", help="Target directory"),
    ) -> None:
        """Pull a manifest from the remote registry."""
        try:
            client = _get_client()
            response = client.get(f"/v1/artifacts/{namespace}/{name}/{version}")
            if response.status_code == 200:
                data = response.json()
                target = Path(directory)
                target.mkdir(parents=True, exist_ok=True)
                manifest_path = target / "manifest.yaml"
                manifest_path.write_text(
                    yaml.dump(data, sort_keys=True, default_flow_style=False),
                    encoding="utf-8",
                )
                console.print(f"[green]Pulled {namespace}/{name}:{version}[/green]")
                console.print(f"  Saved to {manifest_path}")
            elif response.status_code == 404:
                console.print(f"[red]Error: {namespace}/{name}:{version} not found[/red]")
                raise typer.Exit(code=1)
            else:
                console.print(f"[red]Error: {response.status_code} - {response.text}[/red]")
                raise typer.Exit(code=1)
        except Exception as e:
            if "Connection" in str(type(e).__name__):
                console.print(f"[red]Error: Cannot connect to server. Run 'capmesh login' first.[/red]")
                raise typer.Exit(code=1)
            raise
