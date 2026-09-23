from __future__ import annotations

import os
from pathlib import Path

import typer

server_app = typer.Typer(help="Registry server commands.", no_args_is_help=True)


@server_app.command()
def start(
    host: str = typer.Option("0.0.0.0", help="Bind host"),
    port: int = typer.Option(8080, help="Bind port"),
) -> None:
    """Start the CapMesh registry server."""
    import uvicorn
    from capmesh.server.app import create_app

    root = os.environ.get("CAPMESH_ROOT")
    app = create_app(root=Path(root) if root else None)
    uvicorn.run(app, host=host, port=port)
