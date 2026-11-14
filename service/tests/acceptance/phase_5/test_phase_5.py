"""Phase 5 acceptance tests: JSON/HTML report generation and the analyze CLI.

The report module (skillgap.report) is imported lazily so a missing
implementation yields strict xfails rather than collection errors.

Assumed public API:
    generate_json_report(ranked: Sequence[RankedGap]) -> str
    generate_html_report(ranked: Sequence[RankedGap]) -> str
CLI: ``skillgap analyze POSTING... --resume PATH [--format json|html|both]``.
json and html write to stdout; ``both`` may write files and/or stdout.
"""

from __future__ import annotations

import html.parser
import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from typer.testing import CliRunner

from skillgap.cli import app
from skillgap.config import load_config
from skillgap.dedup import merge_to_gap
from skillgap.extraction import extract_dictionary
from skillgap.models import Category, Gap, RankedGap
from skillgap.normalizer import build_lookup
from skillgap.ranking import rank_gaps

_NOT_IMPL = "interface not yet implemented"

try:
    from skillgap import report as _report  # noqa: F401

    def _xfail_report(f: Any) -> Any:
        return f

except ImportError:
    _xfail_report = pytest.mark.xfail(strict=True, reason=_NOT_IMPL)

_FIX = Path(__file__).parent / "fixtures"
_POSTINGS = [_FIX / "posting_one.txt", _FIX / "posting_two.txt", _FIX / "posting_three.txt"]
_RESUME = _FIX / "resume.txt"
_COMPANY = "Zorblatt"

runner = CliRunner()


def _json_report(ranked: Sequence[RankedGap]) -> str:
    from skillgap.report import generate_json_report

    return generate_json_report(ranked)  # type: ignore[no-any-return]


def _html_report(ranked: Sequence[RankedGap]) -> str:
    from skillgap.report import generate_html_report

    return generate_html_report(ranked)  # type: ignore[no-any-return]


def _gap(
    skill: str,
    score: float,
    category: Category = Category.language,
    posting_count: int = 1,
    required: int = 0,
    preferred: int = 0,
) -> Gap:
    return Gap(
        skill=skill,
        category=category,
        score=score,
        posting_count=posting_count,
        required_count=required,
        preferred_count=preferred,
    )


def _sample() -> list[RankedGap]:
    return rank_gaps(
        [
            _gap("kubernetes", 2.5, Category.cloud_infra, 3, 2, 1),
            _gap("terraform", 0.5, Category.cloud_infra, 1, 0, 1),
            _gap("python", 1.0, Category.language, 1, 1, 0),
            _gap("pytorch", 0.75, Category.ai_ml, 1, 0, 0),
        ]
    )


def _cli(*args: str) -> Any:
    return runner.invoke(app, ["analyze", *[str(p) for p in _POSTINGS], *args])


def _cli_args(fmt: str) -> Any:
    return _cli("--resume", str(_RESUME), "--format", fmt)


def _expected_ranked() -> list[RankedGap]:
    """Rank what dictionary extraction yields for the fixtures minus resume skills."""
    aliases, _ = load_config()
    lookup = build_lookup(aliases)
    have = {s.name for s in extract_dictionary(_RESUME.read_text(), "resume", lookup, aliases)}
    groups: dict[str, list[Any]] = {}
    for p in _POSTINGS:
        for s in extract_dictionary(p.read_text(), "jd", lookup, aliases):
            if s.name not in have:
                groups.setdefault(s.name, []).append(s)
    gaps = [merge_to_gap(name, ms[0].category, ms) for name, ms in groups.items()]
    return rank_gaps(gaps)


def _parse_ranked(text: str) -> list[RankedGap]:
    data = json.loads(text)
    assert isinstance(data, list)
    return [RankedGap.model_validate(d) for d in data]


def _extract_json(output: str) -> str:
    start = output.index("[")
    return output[start : output.rindex("]") + 1]


class _Tags(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.text: list[str] = []
        self.in_style = False

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        self.tags.append(tag)
        self.in_style = tag == "style"

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self.in_style = False

    def handle_data(self, data: str) -> None:
        if not self.in_style:
            self.text.append(data)


def _visible_text(doc: str) -> str:
    p = _Tags()
    p.feed(doc)
    return " ".join(p.text)


# --------------------------------------------------------------------------
# AC-1: JSON report
# --------------------------------------------------------------------------


@_xfail_report
@pytest.mark.acceptance
def test_ac_1_1_json_report_returns_valid_json_string() -> None:
    out = _json_report(_sample())
    assert isinstance(out, str)
    json.loads(out)


@_xfail_report
@pytest.mark.acceptance
def test_ac_1_2_json_round_trips_to_ranked_gaps() -> None:
    ranked = _sample()
    parsed = _parse_ranked(_json_report(ranked))
    assert parsed == ranked
    raw = json.loads(_json_report(ranked))
    assert set(raw[0]) == {"rank", "gap"}
    assert set(raw[0]["gap"]) == {
        "skill",
        "category",
        "score",
        "posting_count",
        "required_count",
        "preferred_count",
    }
    assert raw[0]["gap"]["category"] == "cloud_infra"
    assert [r["rank"] for r in raw] == [1, 2, 3, 4]


@_xfail_report
@pytest.mark.acceptance
def test_ac_1_3_empty_gaps_gives_empty_json_array() -> None:
    assert json.loads(_json_report([])) == []


@_xfail_report
@pytest.mark.acceptance
def test_ac_1_4_json_has_no_company_names() -> None:
    out = _json_report(_sample())
    assert _COMPANY.lower() not in out.lower()


@_xfail_report
@pytest.mark.acceptance
def test_ac_1_5_json_is_deterministic_example() -> None:
    assert _json_report(_sample()) == _json_report(_sample())


_gap_strategy = st.builds(
    lambda s, c, req, pref, extra: _gap(
        s, req * 1.0 + pref * 0.5 + extra * 0.75, c, req + pref + extra, req, pref
    ),
    st.text(alphabet=st.characters(categories=("L", "N")), min_size=1, max_size=12),
    st.sampled_from(list(Category)),
    st.integers(0, 4),
    st.integers(0, 4),
    st.integers(1, 4),
)


@_xfail_report
@pytest.mark.acceptance
@settings(max_examples=40, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(st.lists(_gap_strategy, max_size=8, unique_by=lambda g: g.skill))
def test_ac_1_5_json_deterministic_and_round_trips_property(gaps: list[Gap]) -> None:
    ranked = rank_gaps(gaps)
    first = _json_report(ranked)
    assert first == _json_report(ranked)
    assert _parse_ranked(first) == ranked


@_xfail_report
@pytest.mark.acceptance
def test_ac_1_unicode_skill_survives_json() -> None:
    ranked = rank_gaps([_gap("café-ünïcode", 1.0)])
    assert _parse_ranked(_json_report(ranked))[0].gap.skill == "café-ünïcode"


# --------------------------------------------------------------------------
# AC-2: HTML report
# --------------------------------------------------------------------------


@_xfail_report
@pytest.mark.acceptance
def test_ac_2_1_html_report_returns_string() -> None:
    out = _html_report(_sample())
    assert isinstance(out, str)
    assert out.strip()


@_xfail_report
@pytest.mark.acceptance
def test_ac_2_2_html_contains_all_skills() -> None:
    ranked = _sample()
    text = _visible_text(_html_report(ranked)).lower()
    for r in ranked:
        assert r.gap.skill.lower() in text


@_xfail_report
@pytest.mark.acceptance
def test_ac_2_2_html_escapes_markup_in_skill_names() -> None:
    ranked = rank_gaps([_gap("<script>alert(1)</script>", 1.0)])
    out = _html_report(ranked)
    assert "<script>alert(1)</script>" not in out
    assert "&lt;script&gt;" in out


@_xfail_report
@pytest.mark.acceptance
def test_ac_2_3_html_document_structure() -> None:
    out = _html_report(_sample())
    assert out.lstrip().lower().startswith("<!doctype html")
    p = _Tags()
    p.feed(out)
    for tag in ("html", "head", "body", "title", "meta"):
        assert tag in p.tags, f"missing <{tag}>"
    assert p.tags.index("head") < p.tags.index("body")
    assert re.search(r"<meta[^>]+viewport", out, re.I), "responsive viewport meta missing"
    assert re.search(r"<html[^>]+lang=", out, re.I)


@_xfail_report
@pytest.mark.acceptance
def test_ac_2_4_html_has_no_company_names() -> None:
    assert _COMPANY.lower() not in _html_report(_sample()).lower()


@_xfail_report
@pytest.mark.acceptance
def test_ac_2_5_html_is_styled() -> None:
    out = _html_report(_sample())
    m = re.search(r"<style[^>]*>(.+?)</style>", out, re.S | re.I)
    assert m is not None
    assert len(m.group(1).strip()) > 20


@_xfail_report
@pytest.mark.acceptance
def test_ac_2_5_html_is_theme_aware_and_responsive() -> None:
    css = "".join(re.findall(r"<style[^>]*>(.+?)</style>", _html_report(_sample()), re.S | re.I))
    assert "prefers-color-scheme" in css or "color-scheme" in css
    assert "@media" in css


@_xfail_report
@pytest.mark.acceptance
def test_ac_2_6_html_orders_by_score_descending() -> None:
    ranked = _sample()
    text = _visible_text(_html_report(ranked)).lower()
    positions = [text.index(r.gap.skill.lower()) for r in ranked]
    assert positions == sorted(positions)
    assert ranked[0].gap.skill == "kubernetes"


@_xfail_report
@pytest.mark.acceptance
def test_ac_2_7_html_shows_category_counts_and_score() -> None:
    ranked = rank_gaps([_gap("kubernetes", 21.5, Category.cloud_infra, 29, 17, 12)])
    text = _visible_text(_html_report(ranked)).lower()
    assert any(f in text for f in ("cloud_infra", "cloud infra", "cloud & infra", "cloud"))
    assert "21.5" in text or "21.50" in text
    assert "17" in text, "required count missing"
    assert "12" in text, "preferred count missing"
    assert "29" in text, "posting count missing"
    assert "required" in text
    assert "preferred" in text


@_xfail_report
@pytest.mark.acceptance
def test_ac_2_empty_gaps_still_valid_document() -> None:
    out = _html_report([])
    assert out.lstrip().lower().startswith("<!doctype html")
    assert "</html>" in out.lower()


@_xfail_report
@pytest.mark.acceptance
def test_ac_2_html_deterministic() -> None:
    assert _html_report(_sample()) == _html_report(_sample())


# --------------------------------------------------------------------------
# AC-3: CLI
# --------------------------------------------------------------------------


@_xfail_report
@pytest.mark.acceptance
def test_ac_3_1_analyze_help() -> None:
    result = runner.invoke(app, ["analyze", "--help"])
    assert result.exit_code == 0
    assert "--resume" in result.output
    assert "--format" in result.output


@_xfail_report
@pytest.mark.acceptance
def test_ac_3_8_help_mentions_all_options_and_arguments() -> None:
    result = runner.invoke(app, ["analyze", "--help"])
    out = result.output.lower()
    assert result.exit_code == 0
    assert "--resume" in out
    assert "--format" in out
    for fmt in ("json", "html", "both"):
        assert fmt in out
    assert "posting" in out
    assert "not yet implemented" not in out


@_xfail_report
@pytest.mark.acceptance
def test_ac_3_2_format_json_prints_json_to_stdout() -> None:
    result = _cli_args("json")
    assert result.exit_code == 0, result.output
    ranked = _parse_ranked(result.stdout)
    assert ranked, "expected at least one gap"


@_xfail_report
@pytest.mark.acceptance
def test_ac_3_3_format_html_prints_html_to_stdout() -> None:
    result = _cli_args("html")
    assert result.exit_code == 0, result.output
    assert result.stdout.lstrip().lower().startswith("<!doctype html")
    assert "</html>" in result.stdout.lower()


@_xfail_report
@pytest.mark.acceptance
def test_ac_3_4_format_both_produces_both_formats(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = _cli_args("both")
    assert result.exit_code == 0, result.output
    blobs = [result.stdout, *(f.read_text() for f in tmp_path.rglob("*") if f.is_file())]
    combined = "\n".join(blobs)
    assert "<!doctype html" in combined.lower()
    json_part = combined.split("<!", 1)[0] if combined.lstrip().startswith("[") else combined
    candidates = [b for b in blobs if b.lstrip().startswith("[")] or [_extract_json(json_part)]
    assert _parse_ranked(candidates[0]), "no JSON gap report found"


@_xfail_report
@pytest.mark.acceptance
def test_ac_3_5_accepts_resume_and_positional_postings() -> None:
    result = _cli_args("json")
    assert result.exit_code == 0, result.output
    skills = {r.gap.skill for r in _parse_ranked(result.stdout)}
    assert "kubernetes" in skills


@_xfail_report
@pytest.mark.acceptance
def test_ac_3_5_default_format_is_valid_output() -> None:
    result = _cli("--resume", str(_RESUME))
    assert result.exit_code == 0, result.output
    assert "not yet implemented" not in result.output.lower()
    assert result.stdout.strip()


@_xfail_report
@pytest.mark.acceptance
def test_ac_3_6_exit_zero_on_success() -> None:
    for fmt in ("json", "html"):
        assert _cli_args(fmt).exit_code == 0


@_xfail_report
@pytest.mark.acceptance
def test_ac_3_7_nonexistent_posting_exits_nonzero(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["analyze", str(tmp_path / "missing.txt"), "--resume", str(_RESUME)],
    )
    assert result.exit_code != 0
    assert "not yet implemented" not in result.output.lower()


@_xfail_report
@pytest.mark.acceptance
def test_ac_3_7_nonexistent_resume_exits_nonzero(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "analyze",
            str(_POSTINGS[0]),
            "--resume",
            str(tmp_path / "missing.txt"),
        ],
    )
    assert result.exit_code != 0


@_xfail_report
@pytest.mark.acceptance
def test_ac_3_invalid_format_value_rejected() -> None:
    assert _cli_args("json").exit_code == 0  # the option itself must exist
    result = _cli("--resume", str(_RESUME), "--format", "xml")
    assert result.exit_code != 0


# --------------------------------------------------------------------------
# AC-4: integration
# --------------------------------------------------------------------------


@_xfail_report
@pytest.mark.acceptance
def test_ac_4_1_end_to_end_json_report() -> None:
    result = _cli_args("json")
    assert result.exit_code == 0, result.output
    ranked = _parse_ranked(result.stdout)
    assert [r.rank for r in ranked] == list(range(1, len(ranked) + 1))
    scores = [r.gap.score for r in ranked]
    assert scores == sorted(scores, reverse=True)
    by_skill = {r.gap.skill: r.gap for r in ranked}
    assert by_skill["kubernetes"].posting_count == 3
    assert by_skill["kubernetes"].score == pytest.approx(2.25)
    assert by_skill["docker"].posting_count == 2
    assert by_skill["terraform"].posting_count == 1
    assert ranked[0].gap.skill == "kubernetes"


@_xfail_report
@pytest.mark.acceptance
def test_ac_4_1_skills_on_resume_are_not_gaps() -> None:
    skills = {r.gap.skill for r in _parse_ranked(_cli_args("json").stdout)}
    assert "python" not in skills
    assert "aws" not in skills


@_xfail_report
@pytest.mark.acceptance
def test_ac_4_2_end_to_end_html_report() -> None:
    result = _cli_args("html")
    assert result.exit_code == 0, result.output
    text = _visible_text(result.stdout).lower()
    for skill in ("kubernetes", "docker", "terraform"):
        assert skill in text
    assert text.index("kubernetes") < text.index("terraform")


@_xfail_report
@pytest.mark.acceptance
def test_ac_4_3_cli_gaps_match_rank_gaps() -> None:
    expected = _expected_ranked()
    assert expected, "fixture sanity: expected gaps must be non-empty"
    actual = _parse_ranked(_cli_args("json").stdout)
    assert actual == expected


@_xfail_report
@pytest.mark.acceptance
def test_ac_4_cli_json_is_deterministic() -> None:
    first = _cli_args("json").stdout
    assert _parse_ranked(first)
    assert first == _cli_args("json").stdout


@_xfail_report
@pytest.mark.acceptance
def test_ac_4_cli_posting_order_does_not_change_gaps() -> None:
    fwd = _parse_ranked(_cli_args("json").stdout)
    rev = runner.invoke(
        app,
        [
            "analyze",
            *[str(p) for p in reversed(_POSTINGS)],
            "--resume",
            str(_RESUME),
            "--format",
            "json",
        ],
    )
    assert rev.exit_code == 0
    assert _parse_ranked(rev.stdout) == fwd


# --------------------------------------------------------------------------
# AC-5: no company names
# --------------------------------------------------------------------------


def _all_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    monkeypatch.chdir(tmp_path)
    outs: list[tuple[str, str]] = []
    for fmt in ("json", "html"):
        outs.append((fmt, _cli_args(fmt).stdout))
    res = _cli_args("both")
    blobs = [res.stdout, *(f.read_text() for f in tmp_path.rglob("*") if f.is_file())]
    outs.append(("both", "\n".join(blobs)))
    return outs


@_xfail_report
@pytest.mark.acceptance
def test_ac_5_1_company_name_never_appears_in_any_format(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _COMPANY in _POSTINGS[0].read_text()  # fixture sanity
    for fmt, out in _all_outputs(tmp_path, monkeypatch):
        assert out.strip(), f"{fmt}: empty output"
        assert _COMPANY.lower() not in out.lower(), f"{fmt} leaked company name"


@_xfail_report
@pytest.mark.acceptance
def test_ac_5_1_evidence_lines_are_not_emitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Evidence lines in the fixtures carry the company name; they must not be echoed."""
    for fmt, out in _all_outputs(tmp_path, monkeypatch):
        assert out.strip(), f"{fmt}: empty output"
        assert "dynamics" not in out.lower(), f"{fmt} leaked evidence text"


@_xfail_report
@pytest.mark.acceptance
def test_ac_5_2_postings_referenced_by_number_not_path() -> None:
    for fmt in ("json", "html"):
        out = _cli_args(fmt).stdout
        assert out.strip(), f"{fmt}: empty output"
        for p in _POSTINGS:
            assert p.name not in out, f"{fmt}: posting file name leaked"
            assert str(p) not in out
        assert _RESUME.name not in out
