import typer

from capmesh.cli.artifact_commands import (
    agent_app,
    search_app,
    skill_app,
    tag_app,
    tool_app,
)

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
