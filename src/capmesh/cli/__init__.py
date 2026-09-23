import typer

from capmesh.cli.artifact_commands import (
    agent_app,
    search_app,
    skill_app,
    tag_app,
    tool_app,
)
from capmesh.cli.auth_commands import login_app
from capmesh.cli.resolve_commands import providers_app, resolve_app
from capmesh.cli.server_commands import server_app

app = typer.Typer(
    name="capmesh",
    help="Service discovery for the agentic world.",
    no_args_is_help=True,
)

app.add_typer(skill_app, name="skill")
app.add_typer(tool_app, name="tool")
app.add_typer(agent_app, name="agent")
app.add_typer(search_app, name="search")
app.add_typer(tag_app, name="tag")
app.add_typer(resolve_app, name="resolve")
app.add_typer(providers_app, name="providers")
app.add_typer(server_app, name="server")
app.add_typer(login_app, name="login")
