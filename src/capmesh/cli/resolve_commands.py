from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from capmesh.models.resolution import CallerContext, ResolveRequest
from capmesh.policy import default_policy_engine
from capmesh.registry import Registry
from capmesh.resolver import Resolver, ResolutionError
from capmesh.telemetry import TraceStore

console = Console()


def _get_registry() -> Registry:
    root = os.environ.get("CAPMESH_ROOT")
    return Registry(root=Path(root) if root else None)


def _get_resolver() -> tuple[Resolver, TraceStore]:
    root_str = os.environ.get("CAPMESH_ROOT")
    root = Path(root_str) if root_str else Path.home() / ".capmesh"

    registry = Registry(root=root)
    policy = default_policy_engine()

    db = sqlite3.connect(str(root / "traces.db"))
    db.row_factory = sqlite3.Row
    trace_store = TraceStore(db)
    trace_store.init_schema()

    resolver = Resolver(registry=registry, policy_engine=policy, trace_store=trace_store)
    return resolver, trace_store


def make_resolve_command() -> typer.Typer:
    resolve_app = typer.Typer(context_settings={"allow_interspersed_args": True})

    @resolve_app.callback(invoke_without_command=True)
    def resolve(
        ctx: typer.Context,
        capability: str = typer.Argument(..., help="Capability ID to resolve"),
        contract: str = typer.Option("v1", help="Contract version"),
        identity: str = typer.Option("cli-user", help="Caller identity"),
        environment: str = typer.Option(None, help="Caller environment"),
        version_constraint: str = typer.Option(None, "--version", help="Version constraint (e.g. '>=2.0,<3.0')"),
        show_trace: bool = typer.Option(False, "--trace", help="Show resolution trace"),
        output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    ) -> None:
        """Resolve a capability to a provider."""
        resolver, _ = _get_resolver()

        request = ResolveRequest(
            capability=capability,
            contract=contract,
            caller=CallerContext(identity=identity, environment=environment),
            version_constraint=version_constraint,
        )

        try:
            resolution = resolver.resolve(request)
        except ResolutionError as e:
            if output_json:
                print(json.dumps({"error": str(e)}))
            else:
                console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(code=1)

        if output_json:
            data = {
                "provider": f"{resolution.provider_namespace}/{resolution.provider_name}:{resolution.provider_version}",
                "protocol": resolution.binding.protocol,
                "binding": resolution.binding.connection,
                "trace_id": resolution.trace.trace_id,
            }
            if show_trace:
                data["trace"] = resolution.trace.model_dump(mode="json")
            print(json.dumps(data, indent=2, default=str))
        else:
            console.print(f"[green]\u2713 Resolved {capability}/{contract}[/green]")
            console.print(f"  Provider:  {resolution.provider_namespace}/{resolution.provider_name}:{resolution.provider_version}")
            console.print(f"  Protocol:  {resolution.binding.protocol}")
            for key, val in resolution.binding.connection.items():
                console.print(f"  {key.title():10s} {val}")
            console.print(f"  Trace:     {resolution.trace.trace_id}")

            if show_trace:
                console.print()
                console.print("[bold]Resolution Trace[/bold]")
                console.print(f"  Requested: {capability}/{contract}")
                console.print(f"  Candidates: {len(resolution.trace.candidates)}")
                for c in resolution.trace.candidates:
                    if c.passed:
                        console.print(f"    [green]\u2713[/green] {c.provider}:{c.version}")
                    else:
                        console.print(f"    [red]\u2717[/red] {c.provider}:{c.version} -> {c.rejection_reason}")
                console.print(f"  Selected: {resolution.trace.selected_provider}")
                console.print(f"  Protocol: {resolution.trace.selected_protocol}")
                console.print(f"  Resolution: {resolution.trace.resolution_ms:.1f} ms")

    return resolve_app


def make_providers_command() -> typer.Typer:
    providers_app = typer.Typer(context_settings={"allow_interspersed_args": True})

    @providers_app.callback(invoke_without_command=True)
    def providers(
        ctx: typer.Context,
        capability: str = typer.Argument(..., help="Capability ID"),
        contract: str = typer.Option("v1", help="Contract version"),
        output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    ) -> None:
        """List providers for a capability."""
        registry = _get_registry()
        results = registry.providers_for(capability, contract)

        if output_json:
            data = [
                {
                    "namespace": r.namespace,
                    "name": r.name,
                    "kind": r.kind.value,
                    "version": r.version,
                }
                for r in results
            ]
            print(json.dumps(data, indent=2))
        elif not results:
            console.print("No providers found.")
        else:
            table = Table()
            table.add_column("NAMESPACE")
            table.add_column("NAME")
            table.add_column("VERSION")
            table.add_column("STATUS")
            for r in results:
                table.add_row(r.namespace, r.name, r.version, "approved")
            console.print(table)

    return providers_app


resolve_app = make_resolve_command()
providers_app = make_providers_command()
