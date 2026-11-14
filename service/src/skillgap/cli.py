"""CLI entry point for the skill-gap analysis pipeline."""

from __future__ import annotations

from enum import StrEnum
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Annotated

import typer

from skillgap.config import load_config
from skillgap.dedup import merge_to_gap
from skillgap.extraction import extract_dictionary
from skillgap.models import ExtractedSkill, RankedGap
from skillgap.normalizer import build_lookup
from skillgap.ranking import rank_gaps
from skillgap.report import generate_html_report, generate_json_report

app = typer.Typer(
    name="skillgap",
    help="Deterministic skill-gap analysis for tech roles.",
    no_args_is_help=True,
)


_BOTH_JSON = "skillgap-report.json"
_BOTH_HTML = "skillgap-report.html"


class OutputFormat(StrEnum):
    json = "json"
    html = "html"
    both = "both"


def _read(path: Path, label: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        typer.echo(f"Error: cannot read {label}: {exc.__class__.__name__}", err=True)
        raise typer.Exit(code=2) from exc


def compute_ranked(resume_text: str, posting_texts: list[str]) -> list[RankedGap]:
    """Dictionary-extract skills, drop those on the resume, merge and rank."""
    aliases, _ = load_config()
    lookup = build_lookup(aliases)
    have = {s.name for s in extract_dictionary(resume_text, "resume", lookup, aliases)}
    groups: dict[str, list[ExtractedSkill]] = {}
    for text in posting_texts:
        for s in extract_dictionary(text, "jd", lookup, aliases):
            if s.name not in have:
                groups.setdefault(s.name, []).append(s)
    gaps = [merge_to_gap(name, ms[0].category, ms) for name, ms in groups.items()]
    return rank_gaps(gaps)


@app.command()
def analyze(
    postings: Annotated[
        list[Path], typer.Argument(help="Paths to one or more job posting text files")
    ],
    resume: Annotated[
        Path | None,
        typer.Option("--resume", help="Path to resume text file (omit to treat resume as empty)"),
    ] = None,
    output_format: Annotated[
        OutputFormat,
        typer.Option(
            "--format",
            help=(
                "Output format: json or html (printed to stdout), or both "
                "(writes skillgap-report.json and skillgap-report.html "
                "in the current directory)."
            ),
        ),
    ] = OutputFormat.json,
) -> None:
    """Analyze skill gaps between a resume and job postings.

    Prints the report to stdout (or writes files for --format both).
    Postings are identified by number only.
    """
    resume_text = _read(resume, "resume") if resume is not None else ""
    posting_texts = [_read(p, f"posting {i}") for i, p in enumerate(postings, 1)]
    ranked = compute_ranked(resume_text, posting_texts)
    if output_format is OutputFormat.json:
        typer.echo(generate_json_report(ranked))
    elif output_format is OutputFormat.html:
        typer.echo(generate_html_report(ranked))
    else:
        Path(_BOTH_JSON).write_text(generate_json_report(ranked) + "\n", encoding="utf-8")
        Path(_BOTH_HTML).write_text(generate_html_report(ranked), encoding="utf-8")
        typer.echo(f"Wrote {_BOTH_JSON} and {_BOTH_HTML}", err=True)


@app.command()
def version() -> None:
    """Print the version."""
    typer.echo(pkg_version("skillgap"))
