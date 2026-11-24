"""MCP server exposing the skill-gap pipeline as a tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from skillgap.cli import compute_ranked
from skillgap.report import generate_json_report

mcp = FastMCP("skillgap")


@mcp.tool()
def analyze_gaps(postings: list[str], resume: str) -> str:
    """Rank the skills that job postings ask for and the resume does not show.

    Args:
        postings: Full text of each job posting.
        resume: Full text of the resume.

    Returns:
        JSON list of ranked gaps (rank, skill, score, evidence).
    """
    return generate_json_report(compute_ranked(resume, postings))


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
