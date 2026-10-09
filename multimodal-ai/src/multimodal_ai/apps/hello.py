"""Example sub-app. Copy this module to start a new one."""

import typer

app = typer.Typer(help="Example sub-app.", no_args_is_help=True)


@app.command()
def greet(name: str, shout: bool = typer.Option(False, "--shout", "-s")) -> None:
    """Greet NAME."""
    msg = f"Hello, {name}!"
    typer.echo(msg.upper() if shout else msg)
