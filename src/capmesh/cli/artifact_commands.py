from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from capmesh.models.enums import Kind
from capmesh.models.serialization import compute_digest, manifest_from_yaml, manifest_to_yaml
from capmesh.registry import Registry, DuplicateVersionError
from capmesh.cli.scaffold import scaffold_manifest, write_scaffold

console = Console()

_KIND_COLORS = {"agent": "bright_cyan", "tool": "bright_yellow", "skill": "bright_magenta"}
_PROTO_COLORS = {"a2a": "bright_green", "mcp": "bright_blue", "rest": "bright_yellow", "skill": "bright_magenta"}


def _kind_tag(kind: str) -> str:
    color = _KIND_COLORS.get(kind, "white")
    return f"[{color}]\\[{kind}][/{color}]"


def _proto_tag(protocol: str) -> str:
    color = _PROTO_COLORS.get(protocol, "white")
    return f"[{color}]\\[{protocol}][/{color}]"


def _get_registry() -> Registry:
    root = os.environ.get("CAPMESH_ROOT")
    return Registry(root=Path(root) if root else None)


def _make_artifact_app(kind: Kind) -> typer.Typer:
    from capmesh.cli.remote_commands import add_push_command, add_pull_command
    artifact_app = typer.Typer(help=f"Manage {kind.value} artifacts.", no_args_is_help=True)

    @artifact_app.command()
    def init(
        namespace: str = typer.Option(..., help="Artifact namespace"),
        name: str = typer.Option(..., help="Artifact name"),
        version: str = typer.Option("0.1.0", help="Artifact version"),
        owner: str = typer.Option(..., help="Artifact owner"),
        directory: str = typer.Option(".", help="Target directory"),
    ) -> None:
        """Scaffold a new manifest."""
        manifest = scaffold_manifest(kind, namespace, name, version, owner)
        path = write_scaffold(Path(directory), manifest)
        console.print(f"[green]Created {path}[/green]")

    @artifact_app.command()
    def build(
        directory: str = typer.Option(".", help="Directory containing manifest.yaml"),
    ) -> None:
        """Validate manifest and compute digest."""
        manifest_path = Path(directory) / "manifest.yaml"
        if not manifest_path.exists():
            console.print(f"[red]Error: {manifest_path} not found[/red]")
            raise typer.Exit(code=1)
        yaml_str = manifest_path.read_text(encoding="utf-8")
        manifest = manifest_from_yaml(yaml_str)
        digest = compute_digest(manifest)
        console.print(f"[green]Valid {kind.value} manifest[/green]")
        console.print(f"  Name:    {manifest.metadata.namespace}/{manifest.metadata.name}")
        console.print(f"  Version: {manifest.metadata.version}")
        console.print(f"  Digest:  sha256:{digest}")

    @artifact_app.command()
    def register(
        file: str = typer.Option(..., help="Path to manifest.yaml"),
    ) -> None:
        """Register a manifest into the local registry."""
        manifest_path = Path(file)
        if not manifest_path.exists():
            console.print(f"[red]Error: {manifest_path} not found[/red]")
            raise typer.Exit(code=1)
        yaml_str = manifest_path.read_text(encoding="utf-8")
        manifest = manifest_from_yaml(yaml_str)

        if manifest.metadata.kind != kind:
            console.print(
                f"[red]Error: manifest kind is {manifest.metadata.kind.value}, expected {kind.value}[/red]"
            )
            raise typer.Exit(code=1)

        registry = _get_registry()
        try:
            digest = registry.register(manifest)
        except DuplicateVersionError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(code=1)

        kind_tag = _kind_tag(manifest.metadata.kind.value)
        proto_tag = _proto_tag(manifest.interface.protocol)
        console.print(
            f"[green]Registered {manifest.metadata.namespace}/{manifest.metadata.name}:{manifest.metadata.version}[/green]  {kind_tag} {proto_tag}"
        )
        console.print(f"  Digest: sha256:{digest}")

    @artifact_app.command()
    def inspect(
        namespace: str = typer.Argument(..., help="Artifact namespace"),
        name: str = typer.Argument(..., help="Artifact name"),
        version: str = typer.Argument(..., help="Artifact version"),
        output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    ) -> None:
        """Show manifest details from registry."""
        registry = _get_registry()
        manifest = registry.get(namespace, name, version)
        if manifest is None:
            console.print(f"[red]Error: {namespace}/{name}:{version} not found[/red]")
            raise typer.Exit(code=1)

        if output_json:
            data = manifest.model_dump(mode="json")
            data["_tags"] = {"kind": manifest.metadata.kind.value, "protocol": manifest.interface.protocol}
            print(json.dumps(data, indent=2))
        else:
            kind_tag = _kind_tag(manifest.metadata.kind.value)
            proto_tag = _proto_tag(manifest.interface.protocol)
            console.print(f"[bold]{namespace}/{name}:{version}[/bold]  {kind_tag} {proto_tag}")
            console.print(f"  Owner:      {manifest.metadata.owner}")
            console.print(f"  Digest:     sha256:{manifest.metadata.digest}")
            console.print(f"  Visibility: {manifest.governance.visibility.value}")
            console.print(f"  Status:     {manifest.governance.status.value}")
            if manifest.provides:
                console.print("  Provides:")
                for cap in manifest.provides:
                    console.print(f"    - {cap.capability}/{cap.contract}")
            if manifest.requires:
                console.print("  Requires:")
                for cap in manifest.requires:
                    console.print(f"    - {cap.capability}/{cap.contract}")

    add_push_command(artifact_app, kind.value)
    add_pull_command(artifact_app, kind.value)

    return artifact_app


def make_search_command() -> typer.Typer:
    """Create the top-level search command."""
    search_app = typer.Typer(context_settings={"allow_interspersed_args": True})

    @search_app.callback(invoke_without_command=True)
    def search(
        ctx: typer.Context,
        query: str = typer.Argument(..., help="Search query"),
        output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    ) -> None:
        """Search for artifacts in the registry."""
        registry = _get_registry()
        results = registry.search(query)

        if output_json:
            data = [
                {
                    "namespace": r.namespace,
                    "name": r.name,
                    "kind": r.kind.value,
                    "version": r.version,
                    "digest": r.digest,
                }
                for r in results
            ]
            print(json.dumps(data, indent=2))
        elif not results:
            console.print("No results found.")
        else:
            table = Table()
            table.add_column("NAMESPACE")
            table.add_column("NAME")
            table.add_column("VERSION")
            table.add_column("KIND")
            table.add_column("PROTOCOL")
            for r in results:
                manifest = registry.get(r.namespace, r.name, r.version)
                protocol = manifest.interface.protocol if manifest else "?"
                kind_color = _KIND_COLORS.get(r.kind.value, "white")
                proto_color = _PROTO_COLORS.get(protocol, "white")
                table.add_row(
                    r.namespace, r.name, r.version,
                    f"[{kind_color}]{r.kind.value}[/{kind_color}]",
                    f"[{proto_color}]{protocol}[/{proto_color}]",
                )
            console.print(table)

    return search_app


def make_tag_command() -> typer.Typer:
    """Create the top-level tag command."""
    tag_app = typer.Typer(context_settings={"allow_interspersed_args": True})

    @tag_app.callback(invoke_without_command=True)
    def tag(
        ctx: typer.Context,
        namespace: str = typer.Argument(..., help="Artifact namespace"),
        name: str = typer.Argument(..., help="Artifact name"),
        version: str = typer.Argument(..., help="Artifact version"),
        tag_name: str = typer.Argument(..., help="Tag name"),
    ) -> None:
        """Tag an artifact version."""
        registry = _get_registry()
        try:
            registry.tag(namespace, name, version, tag_name)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(code=1)
        console.print(
            f"[green]Tagged {namespace}/{name}:{version} as '{tag_name}'[/green]"
        )

    return tag_app


skill_app = _make_artifact_app(Kind.SKILL)
tool_app = _make_artifact_app(Kind.TOOL)
agent_app = _make_artifact_app(Kind.AGENT)
search_app = make_search_command()
tag_app = make_tag_command()
