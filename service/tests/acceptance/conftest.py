"""Auto-apply the acceptance marker and provide shared fixtures for acceptance tests."""

from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
import respx
from httpx import Response

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "/acceptance/" in str(item.fspath):
            item.add_marker(pytest.mark.acceptance)


_ROBOTS_TXT = """\
User-agent: *
Disallow: /blocked-by-robots
"""

_FAKE_HTML = """\
<html><body>
<h1>Senior Software Engineer</h1>
<p>Requirements: Python, Java, Kubernetes</p>
</body></html>
"""


@pytest.fixture(autouse=True)
def _mock_http(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Mock HTTP for fetcher acceptance tests so no live network calls are made."""
    test_module = request.node.module.__name__ if request.node.module else ""
    if "phase_2" not in test_module:
        yield
        return

    with respx.mock:
        respx.get("https://example.com/robots.txt").mock(
            return_value=Response(200, text=_ROBOTS_TXT)
        )
        respx.get("https://example.com/job-posting").mock(
            return_value=Response(200, text=_FAKE_HTML)
        )
        respx.get("https://example.com/blocked-by-robots").mock(
            return_value=Response(200, text=_FAKE_HTML)
        )
        respx.get("https://example.com/job").mock(return_value=Response(200, text=_FAKE_HTML))
        yield


def _load_recorded_response(name: str) -> dict[str, Any]:
    path = _FIXTURES_DIR / "recorded_responses" / name
    return json.loads(path.read_text())  # type: ignore[no-any-return]


def _fake_call_llm(prompt: str) -> dict[str, Any]:
    if "job posting" in prompt.lower():
        return _load_recorded_response("posting_extraction.json")
    return _load_recorded_response("resume_extraction.json")


@pytest.fixture(autouse=True)
def _mock_llm(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock LLM calls for Phase 3 tests so no live Anthropic API calls are made."""
    test_module = request.node.module.__name__ if request.node.module else ""
    if "phase_3" not in test_module:
        return
    monkeypatch.setattr("skillgap.extractor._call_llm", _fake_call_llm)
