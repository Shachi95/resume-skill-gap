"""CLI entry point for the skill-gap analysis pipeline."""

from __future__ import annotations

from importlib.metadata import version as pkg_version
from typing import Annotated

import typer

app = typer.Typer(
    name="skillgap",
    help="Deterministic skill-gap analysis for tech roles.",
    no_args_is_help=True,
)


@app.command()
def analyze(
    postings: Annotated[list[str], typer.Argument(help="Paths to posting text files")],
    resume: Annotated[str, typer.Option(help="Path to resume text file")] = "",
) -> None:
    """Analyze skill gaps between a resume and job postings."""
    typer.echo("Not yet implemented. See docs/phases/ for roadmap.")


@app.command()
def version() -> None:
    """Print the version."""
    typer.echo(pkg_version("skillgap"))
