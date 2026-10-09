"""Single CLI entry point. Sub-apps from `multimodal_ai.apps` are mounted here."""

from pathlib import Path

import typer
from dotenv import load_dotenv

# Put the variables from the project root's .env (e.g. HF_TOKEN) into
# os.environ before anything reads them. parents[2]: main.py -> multimodal_ai
# -> src -> project root. Variables already set in the shell win over .env.
load_dotenv(Path(__file__).parents[2] / ".env")

from multimodal_ai.apps import hello, sound

app = typer.Typer(help="multimodal-ai command line.", no_args_is_help=True)

# Register each sub-app as a command group: `main <name> ...`
app.add_typer(hello.app, name="hello")
app.add_typer(sound.app, name="sound")


@app.command()
def version() -> None:
    """Show the package version."""
    from importlib.metadata import version as v

    typer.echo(v("multimodal-ai"))


if __name__ == "__main__":
    app()
