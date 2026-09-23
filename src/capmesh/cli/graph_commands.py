import os
import json
from pathlib import Path
import typer
from rich.console import Console
from rich.tree import Tree
from capmesh.registry import Registry

console = Console()


def make_graph_command() -> typer.Typer:
    graph_app = typer.Typer(context_settings={"allow_interspersed_args": True})

    @graph_app.callback(invoke_without_command=True)
    def graph(
        ctx: typer.Context,
        capability: str = typer.Argument(..., help="Capability ID"),
        contract: str = typer.Option("v1", help="Contract version"),
        output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    ) -> None:
        """Show dependency graph for a capability."""
        root_str = os.environ.get("CAPMESH_ROOT")
        root = Path(root_str) if root_str else None
        registry = Registry(root=root)

        providers = registry.providers_for(capability, contract)

        if output_json:
            result = []
            for p in providers:
                manifest = registry.get(p.namespace, p.name, p.version)
                entry = {
                    "provider": f"{p.namespace}/{p.name}:{p.version}",
                    "protocol": manifest.interface.protocol if manifest else "unknown",
                    "requires": [],
                }
                if manifest:
                    for req in manifest.requires:
                        sub_providers = registry.providers_for(req.capability, req.contract)
                        entry["requires"].append(
                            {
                                "capability": req.capability,
                                "contract": req.contract,
                                "providers": [
                                    f"{sp.namespace}/{sp.name}:{sp.version}" for sp in sub_providers
                                ],
                            }
                        )
                result.append(entry)
            print(json.dumps(result, indent=2))
        elif not providers:
            console.print(f"No providers found for {capability}/{contract}")
        else:
            tree = Tree(f"[bold]{capability}/{contract}[/bold]")
            for p in providers:
                manifest = registry.get(p.namespace, p.name, p.version)
                protocol = manifest.interface.protocol if manifest else "?"
                branch = tree.add(
                    f"[green]{p.namespace}/{p.name}:{p.version}[/green] ({protocol})"
                )
                if manifest and manifest.requires:
                    for req in manifest.requires:
                        req_branch = branch.add(
                            f"[yellow]requires: {req.capability}/{req.contract}[/yellow]"
                        )
                        sub_providers = registry.providers_for(req.capability, req.contract)
                        for sp in sub_providers:
                            req_branch.add(f"[blue]{sp.namespace}/{sp.name}:{sp.version}[/blue]")
                        if not sub_providers:
                            req_branch.add("[red]no provider found[/red]")
            console.print(tree)

    return graph_app


graph_app = make_graph_command()
