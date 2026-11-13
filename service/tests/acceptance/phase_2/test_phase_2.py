"""Independent acceptance tests for Phase 2: fetcher, cleaner, splitter, parser."""

from __future__ import annotations

import html as html_lib
import time
from pathlib import Path

import httpx
import pytest
import respx

from skillgap.cleaner import clean
from skillgap.fetcher import RobotsDisallowedError, fetch
from skillgap.models import Posting
from skillgap.parser import parse_posting
from skillgap.splitter import split_sections

_FIXTURES = Path(__file__).parent.parent.parent / "fixtures"
_POSTING_FILES = sorted((_FIXTURES / "postings").glob("*/*.txt"))
_HTML_FILES = sorted((_FIXTURES / "postings_html").glob("*.html"))

_BOILERPLATE = [
    "Cookie Policy",
    "Privacy Policy",
    "All rights reserved",
    "analytics loaded",
    "console.log",
]

_STANDARD_TEXT = """Senior Backend Engineer

About the role:
We build payment systems.

Requirements:
- 5+ years of Python
- Experience with Kubernetes

Preferred:
- Experience with Rust

Responsibilities:
- Design and operate services
"""


def _wrap_in_html(text: str) -> str:
    """Wrap plain-text posting in an HTML page with boilerplate."""
    body: list[str] = []
    in_list = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        esc = html_lib.escape(line)
        if line.startswith("- "):
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{html_lib.escape(line[2:])}</li>")
            continue
        if in_list:
            body.append("</ul>")
            in_list = False
        if line.endswith(":") and len(line) < 40:
            body.append(f"<h2>{esc[:-1]}</h2>")
        else:
            body.append(f"<p>{esc}</p>")
    if in_list:
        body.append("</ul>")
    return (
        "<html><head><title>Job</title><style>body{color:red}</style></head><body>"
        '<nav><a href="/">Home</a> | <a href="/jobs">Jobs</a></nav>'
        "<header><div>Careers Portal</div></header>"
        "<main>" + "\n".join(body) + "</main>"
        "<footer><p>Copyright 2024. All rights reserved.</p>"
        "<p>Cookie Policy | Privacy Policy</p></footer>"
        '<script>console.log("analytics loaded");</script>'
        "</body></html>"
    )


# ---------------------------------------------------------------- fixtures sanity


def test_fixture_corpus_has_thirty_postings() -> None:
    assert len(_POSTING_FILES) == 30


# ---------------------------------------------------------------- fetcher


def test_fetch_returns_raw_html_for_mocked_url() -> None:
    result = fetch("https://example.com/job-posting", rate_limit=100.0)
    assert isinstance(result, str)
    assert "<html>" in result
    assert "<h1>Senior Software Engineer</h1>" in result
    assert "Kubernetes" in result


def test_fetch_second_mocked_url() -> None:
    result = fetch("https://example.com/job", rate_limit=100.0)
    assert "Senior Software Engineer" in result


def test_fetch_checks_robots_txt() -> None:
    fetch("https://example.com/job-posting", rate_limit=100.0)
    called = [str(c.request.url) for c in respx.calls]
    assert "https://example.com/robots.txt" in called


def test_fetch_raises_when_robots_disallows() -> None:
    with pytest.raises(RobotsDisallowedError):
        fetch("https://example.com/blocked-by-robots", rate_limit=100.0)


def test_robots_disallowed_does_not_fetch_page() -> None:
    with pytest.raises(RobotsDisallowedError):
        fetch("https://example.com/blocked-by-robots", rate_limit=100.0)
    called = [str(c.request.url) for c in respx.calls]
    assert "https://example.com/blocked-by-robots" not in called


def test_robots_disallowed_error_is_exception() -> None:
    assert issubclass(RobotsDisallowedError, Exception)


def test_fetch_http_error_status_raises() -> None:
    respx.get("https://example.com/missing").mock(return_value=httpx.Response(404, text="nope"))
    with pytest.raises(httpx.HTTPError):
        fetch("https://example.com/missing", rate_limit=100.0)


def test_fetch_sends_user_agent_header() -> None:
    fetch("https://example.com/job-posting", rate_limit=100.0)
    page_calls = [c for c in respx.calls if c.request.url.path == "/job-posting"]
    assert page_calls
    ua = page_calls[0].request.headers.get("user-agent", "")
    assert ua
    assert "python-httpx" not in ua.lower()


def test_fetch_is_rate_limited() -> None:
    start = time.monotonic()
    for _ in range(3):
        fetch("https://example.com/job-posting", rate_limit=5.0)
    elapsed = time.monotonic() - start
    # 3 calls at 5 req/s need at least two 0.2s gaps (allow slack).
    assert elapsed >= 0.3


def test_fetch_high_rate_limit_is_fast() -> None:
    start = time.monotonic()
    for _ in range(3):
        fetch("https://example.com/job-posting", rate_limit=1000.0)
    assert time.monotonic() - start < 2.0


def test_no_unmocked_network_calls() -> None:
    fetch("https://example.com/job", rate_limit=100.0)
    for call in respx.calls:
        assert call.request.url.host == "example.com"


# ---------------------------------------------------------------- cleaner


def test_clean_strips_tags() -> None:
    out = clean(
        "<html><body><main><h1>Title Here</h1><p>Some <b>bold</b> text.</p></main></body></html>"
    )
    assert "<" not in out
    assert ">" not in out
    assert "Title Here" in out
    assert "bold" in out


def test_clean_strips_nav_footer_script_style() -> None:
    page = (
        "<html><head><style>.x{color:red}</style></head><body>"
        "<nav><a href='/'>NAVLINK</a></nav>"
        "<main><h1>Engineer</h1><p>Build distributed systems with Python and Go "
        "for a large production platform serving millions of users.</p></main>"
        "<footer>FOOTERTEXT Cookie Policy</footer>"
        "<script>var SCRIPTVAR = 1;</script></body></html>"
    )
    out = clean(page)
    assert "Build distributed systems" in out
    for junk in ("NAVLINK", "FOOTERTEXT", "SCRIPTVAR", "color:red"):
        assert junk not in out


def test_clean_fallback_for_minimal_html() -> None:
    out = clean(
        "<html><body><nav>MENU</nav><p>Short posting text</p><script>x=1</script></body></html>"
    )
    assert "Short posting text" in out
    assert "MENU" not in out
    assert "x=1" not in out


def test_clean_fallback_on_bare_fragment() -> None:
    out = clean("<div><p>Fragment only</p></div>")
    assert "Fragment only" in out


def test_clean_empty_input_returns_blank() -> None:
    assert clean("").strip() == ""


def test_clean_malformed_html_does_not_raise() -> None:
    out = clean("<html><body><p>Unclosed <b>tag <div>Requirements: Python")
    assert "Python" in out
    assert "<" not in out


def test_clean_returns_str() -> None:
    assert isinstance(clean("<p>hi</p>"), str)


@pytest.mark.parametrize("path", _HTML_FILES, ids=lambda p: p.name)
def test_clean_html_fixture_strips_boilerplate(path: Path) -> None:
    out = clean(path.read_text())
    assert out.strip()
    for junk in [*_BOILERPLATE, "Careers Portal", "<nav", "<script", "<li>", "<h2>"]:
        assert junk not in out
    assert "Requirements" in out


@pytest.mark.parametrize("path", _POSTING_FILES, ids=lambda p: f"{p.parent.name}-{p.name}")
def test_clean_strips_boilerplate_from_all_posting_fixtures(path: Path) -> None:
    text = path.read_text()
    out = clean(_wrap_in_html(text))
    assert out.strip()
    for junk in [*_BOILERPLATE, "Careers Portal", "<nav", "<footer", "<script", "<li>", "<p>"]:
        assert junk not in out
    # Real content must survive: the first bullet of the posting.
    bullets = [ln[2:].strip() for ln in text.splitlines() if ln.startswith("- ")]
    assert bullets
    probe = bullets[0].split()[0:3]
    assert " ".join(probe) in out


# ---------------------------------------------------------------- splitter


def test_split_returns_dict_with_lowercase_keys() -> None:
    result = split_sections(_STANDARD_TEXT)
    assert isinstance(result, dict)
    assert result
    for key in result:
        assert key == key.lower()


def test_split_identifies_standard_sections() -> None:
    result = split_sections(_STANDARD_TEXT)
    assert "requirements" in result
    assert "preferred" in result
    assert "responsibilities" in result
    assert "Kubernetes" in result["requirements"]
    assert "Rust" in result["preferred"]
    assert "Design and operate" in result["responsibilities"]


def test_split_section_bodies_do_not_leak() -> None:
    result = split_sections(_STANDARD_TEXT)
    assert "Rust" not in result["requirements"]
    assert "Kubernetes" not in result["preferred"]
    assert "Python" not in result["responsibilities"]


def test_split_is_case_insensitive() -> None:
    result = split_sections("Intro\n\nREQUIREMENTS\n- Python\n\nResponsibilities:\n- Code\n")
    assert "Python" in result["requirements"]
    assert "Code" in result["responsibilities"]


@pytest.mark.parametrize(
    ("heading", "key"),
    [
        ("Qualifications", "requirements"),
        ("Minimum Qualifications", "requirements"),
        ("Who you are", "requirements"),
        ("Preferred Qualifications", "preferred"),
        ("Nice to have", "preferred"),
        ("Key Responsibilities", "responsibilities"),
        ("What you'll do", "responsibilities"),
        ("About the role", "description"),
    ],
)
def test_split_heading_aliases_normalize(heading: str, key: str) -> None:
    result = split_sections(f"Title\n\n{heading}:\n- UNIQUEBODY item\n")
    assert key in result
    assert "UNIQUEBODY" in result[key]


def test_split_empty_input() -> None:
    assert split_sections("") == {}


def test_split_no_headings_returns_empty() -> None:
    assert split_sections("Just a paragraph with no structure at all.") == {}


def test_split_missing_sections_only_returns_present() -> None:
    result = split_sections("Title\n\nRequirements:\n- Python\n")
    assert "requirements" in result
    assert "preferred" not in result
    assert "responsibilities" not in result


def test_split_ignores_heading_words_inside_sentences() -> None:
    result = split_sections("We list requirements and responsibilities in this sentence only.")
    assert result == {}


def test_split_section_values_are_stripped_strings() -> None:
    for body in split_sections(_STANDARD_TEXT).values():
        assert isinstance(body, str)
        assert body == body.strip()


def _fixture_sections() -> list[dict[str, str]]:
    return [split_sections(p.read_text()) for p in _POSTING_FILES]


def test_split_finds_requirements_in_at_least_80_percent_of_fixtures() -> None:
    results = _fixture_sections()
    hits = sum(1 for r in results if r.get("requirements", "").strip())
    assert hits / len(results) >= 0.8, f"{hits}/{len(results)}"


def test_split_finds_target_sections_in_at_least_80_percent_of_fixtures() -> None:
    results = _fixture_sections()
    targets = {"requirements", "preferred", "responsibilities"}
    hits = sum(1 for r in results if targets & {k for k, v in r.items() if v.strip()})
    assert hits / len(results) >= 0.8, f"{hits}/{len(results)}"


def test_split_finds_responsibilities_in_majority_of_fixtures() -> None:
    results = _fixture_sections()
    hits = sum(1 for r in results if r.get("responsibilities", "").strip())
    assert hits / len(results) >= 0.5, f"{hits}/{len(results)}"


def test_split_sections_come_from_source_text() -> None:
    for path in _POSTING_FILES:
        text = path.read_text()
        for body in split_sections(text).values():
            if body:
                assert body.splitlines()[0].strip() in text


# ---------------------------------------------------------------- parser


_PAGE = _wrap_in_html(_STANDARD_TEXT)


def test_parse_posting_returns_valid_posting() -> None:
    posting = parse_posting(url="https://example.com/job-posting", html=_PAGE)
    assert isinstance(posting, Posting)
    assert posting.title.strip()
    assert posting.text.strip()
    assert posting.url == "https://example.com/job-posting"
    assert posting.id.strip()


def test_parse_posting_has_sections() -> None:
    posting = parse_posting(url="https://example.com/job-posting", html=_PAGE)
    assert "requirements" in posting.sections
    assert "Kubernetes" in posting.sections["requirements"]
    assert "preferred" in posting.sections
    assert "responsibilities" in posting.sections


def test_parse_posting_text_is_cleaned() -> None:
    posting = parse_posting(url="https://example.com/job-posting", html=_PAGE)
    for junk in ["Cookie Policy", "analytics loaded", "<nav", "<script", "Careers Portal"]:
        assert junk not in posting.text


def test_parse_posting_id_is_deterministic_and_url_specific() -> None:
    a1 = parse_posting(url="https://example.com/a", html=_PAGE)
    a2 = parse_posting(url="https://example.com/a", html=_PAGE)
    b = parse_posting(url="https://example.com/b", html=_PAGE)
    assert a1.id == a2.id
    assert a1.id != b.id


def test_parse_posting_title_from_content() -> None:
    posting = parse_posting(url="https://example.com/job", html=_PAGE)
    assert "Backend Engineer" in posting.title


def test_parse_posting_without_sections_has_empty_sections() -> None:
    posting = parse_posting(
        url="https://example.com/job",
        html=(
            "<html><body><main><h1>Plain Role</h1>"
            "<p>We need someone great.</p></main></body></html>"
        ),
    )
    assert posting.sections == {}
    assert posting.title.strip()


def test_parse_posting_empty_html_raises() -> None:
    with pytest.raises(ValueError):
        parse_posting(url="https://example.com/job", html="")


def test_parse_posting_blank_body_raises() -> None:
    with pytest.raises(ValueError):
        parse_posting(url="https://example.com/job", html="<html><body></body></html>")


def test_parse_posting_malformed_html() -> None:
    posting = parse_posting(
        url="https://example.com/job",
        html="<html><body><h1>Broken Role<p>Requirements:<ul><li>Python",
    )
    assert isinstance(posting, Posting)
    assert "Python" in posting.text


@pytest.mark.parametrize("path", _HTML_FILES, ids=lambda p: p.name)
def test_parse_posting_html_fixtures(path: Path) -> None:
    posting = parse_posting(url=f"https://example.com/{path.stem}", html=path.read_text())
    assert posting.title.strip()
    assert "Cookie Policy" not in posting.text
    assert posting.sections


def test_fetch_then_parse_end_to_end() -> None:
    html = fetch("https://example.com/job-posting", rate_limit=100.0)
    posting = parse_posting(url="https://example.com/job-posting", html=html)
    assert "Senior Software Engineer" in posting.title
    assert "Kubernetes" in posting.text


def test_posting_model_rejects_blank_title_and_text() -> None:
    with pytest.raises(ValueError):
        Posting(id="x", title="  ", text="body")
    with pytest.raises(ValueError):
        Posting(id="x", title="t", text=" ")
