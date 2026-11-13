"""Tests for the CLI skeleton."""

from __future__ import annotations

from typer.testing import CliRunner

from skillgap.cli import app

runner = CliRunner()


class TestCli:
    def test_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "analyze" in result.output
        assert "version" in result.output

    def test_version(self) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert result.output.strip()

    def test_analyze_placeholder(self) -> None:
        result = runner.invoke(app, ["analyze", "posting.txt", "--resume", "resume.txt"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.output.lower()

    def test_no_args_shows_help(self) -> None:
        result = runner.invoke(app, [])
        assert "analyze" in result.output
