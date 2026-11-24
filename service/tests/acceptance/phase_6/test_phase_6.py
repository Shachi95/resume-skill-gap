"""Phase 6 acceptance tests: FastAPI server, MCP tool, Docker files, SKILL.md.

Assumed public API (the spec leaves names open; these are the contract tested):
    skillgap.server.app            FastAPI app
        GET  /health               -> 200
        POST /analyze              JSON {"postings": [str], "resume": str}
                                   -> ranked gaps, either a JSON list of RankedGap
                                      or an object with a "gaps" list
        Auth: header ``X-API-Key`` checked against env var ``SKILLGAP_API_KEY``.
    skillgap.mcp_server.analyze_gaps(postings: list[str], resume: str)
        -> ranked gaps as a JSON string or a list/dict of RankedGap dicts.
        May be sync or async. Tool registered on a FastMCP-style object is
        optionally discovered via a module attribute ``mcp``.
Reference output is ``skillgap.cli.compute_ranked`` (the Phase 5 pipeline).
No network and no AI calls: everything is in-process.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import re
from pathlib import Path
from typing import Any

import pytest

from skillgap.cli import compute_ranked
from skillgap.models import RankedGap

_NOT_IMPL = "interface not yet implemented"
_ROOT = Path(__file__).resolve().parents[4]
_SERVICE = _ROOT / "service"
_FIX = Path(__file__).resolve().parents[1] / "phase_5" / "fixtures"
_POSTINGS = [
    (_FIX / n).read_text() for n in ("posting_one.txt", "posting_two.txt", "posting_three.txt")
]
_RESUME = (_FIX / "resume.txt").read_text()
_COMPANY = "Zorblatt"
_KEY = "test-key-fictional-123"
_SKILL = _ROOT / "skill" / "resume-skill-gap" / "SKILL.md"

try:
    from fastapi.testclient import TestClient
    from skillgap.server import app as server_app

    def _xf_server(f: Any) -> Any:
        return f

except ImportError:
    _xf_server = pytest.mark.xfail(strict=True, reason=_NOT_IMPL)

try:
    from skillgap import mcp_server

    def _xf_mcp(f: Any) -> Any:
        return f

except ImportError:
    _xf_mcp = pytest.mark.xfail(strict=True, reason=_NOT_IMPL)


def _find(*rel: str) -> Path | None:
    for base in (_SERVICE, _ROOT):
        for r in rel:
            if (base / r).is_file():
                return base / r
    return None


_DOCKERFILE = _find("Dockerfile")
_COMPOSE = _find("docker-compose.yml", "docker-compose.yaml", "compose.yaml", "compose.yml")


def _xf_if(cond: bool) -> Any:
    return (lambda f: f) if cond else pytest.mark.xfail(strict=True, reason=_NOT_IMPL)


def _skill_text() -> str:
    return _SKILL.read_text().lower() if _SKILL.is_file() else ""


def _skill_mentions_mcp() -> bool:
    return bool(re.search(r"\bmcp\b", _skill_text()))


def _skill_has_fallback() -> bool:
    t = _skill_text()
    return bool(re.search(r"fall\s*back|fallback", t)) and "in-session" in t


# ---------------------------------------------------------------- helpers


def _ranked_from(payload: Any) -> list[RankedGap]:
    if isinstance(payload, str):
        payload = json.loads(payload)
    if isinstance(payload, dict):
        payload = payload["gaps"]
    return [RankedGap.model_validate(item) for item in payload]


def _expected() -> list[RankedGap]:
    return compute_ranked(_RESUME, _POSTINGS)


def _post(body: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
    client = TestClient(server_app)
    if body is None:
        body = {"postings": _POSTINGS, "resume": _RESUME}
    return client.post("/analyze", json=body, headers=headers or {})


@pytest.fixture(autouse=True)
def _api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKILLGAP_API_KEY", _KEY)


_AUTH = {"X-API-Key": _KEY}


def _call_tool(postings: list[str], resume: str) -> list[RankedGap]:
    result = mcp_server.analyze_gaps(postings, resume)
    if inspect.isawaitable(result):
        result = asyncio.run(result)  # type: ignore[arg-type]
    return _ranked_from(result)


# ---------------------------------------------------------------- FastAPI


@_xf_server
@pytest.mark.acceptance
def test_ac_1_1_server_exposes_fastapi_app() -> None:
    from fastapi import FastAPI

    assert isinstance(server_app, FastAPI)
    paths = {getattr(r, "path", "") for r in server_app.routes}
    assert "/analyze" in paths
    assert "/health" in paths


@_xf_server
@pytest.mark.acceptance
def test_ac_1_2_analyze_returns_nonempty_json_gaps() -> None:
    resp = _post(headers=_AUTH)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    ranked = _ranked_from(resp.json())
    assert len(ranked) > 0
    assert "kubernetes" in {r.gap.skill.lower() for r in ranked}
    assert "python" not in {r.gap.skill.lower() for r in ranked}  # on the resume


@_xf_server
@pytest.mark.acceptance
def test_ac_1_3_response_roundtrips_ranked_gap_schema() -> None:
    ranked = _ranked_from(_post(headers=_AUTH).json())
    assert [r.rank for r in ranked] == list(range(1, len(ranked) + 1))
    scores = [r.gap.score for r in ranked]
    assert scores == sorted(scores, reverse=True)
    for r in ranked:
        assert RankedGap.model_validate(r.model_dump(mode="json")) == r


@_xf_server
@pytest.mark.acceptance
def test_ac_1_4_missing_api_key_rejected() -> None:
    assert _post().status_code in (401, 403)


@_xf_server
@pytest.mark.acceptance
def test_ac_1_4_wrong_api_key_rejected() -> None:
    assert _post(headers={"X-API-Key": "wrong-key"}).status_code in (401, 403)
    assert _post(headers={"X-API-Key": ""}).status_code in (401, 403)


@_xf_server
@pytest.mark.acceptance
def test_ac_1_5_valid_api_key_succeeds() -> None:
    assert _post(headers=_AUTH).status_code == 200


@_xf_server
@pytest.mark.acceptance
def test_ac_1_6_no_company_names_in_response() -> None:
    resp = _post(headers=_AUTH)
    assert resp.status_code == 200
    assert _COMPANY.lower() not in resp.text.lower()


@_xf_server
@pytest.mark.acceptance
def test_ac_1_7_matches_cli_pipeline_output() -> None:
    assert _ranked_from(_post(headers=_AUTH).json()) == _expected()


@_xf_server
@pytest.mark.acceptance
def test_ac_1_8_empty_postings_returns_empty_gaps() -> None:
    resp = _post({"postings": [], "resume": _RESUME}, _AUTH)
    assert resp.status_code == 200
    assert _ranked_from(resp.json()) == []


@_xf_server
@pytest.mark.acceptance
def test_ac_1_8_empty_resume_still_returns_gaps() -> None:
    resp = _post({"postings": _POSTINGS, "resume": ""}, _AUTH)
    assert resp.status_code == 200
    assert len(_ranked_from(resp.json())) >= len(_expected())


@_xf_server
@pytest.mark.acceptance
def test_ac_1_8_malformed_body_is_client_error() -> None:
    resp = _post({"postings": "not-a-list"}, _AUTH)
    assert 400 <= resp.status_code < 500


@_xf_server
@pytest.mark.acceptance
def test_ac_1_9_health_returns_200_without_auth() -> None:
    assert TestClient(server_app).get("/health").status_code == 200


# ---------------------------------------------------------------- MCP


@_xf_mcp
@pytest.mark.acceptance
def test_ac_2_1_mcp_server_module_importable() -> None:
    assert mcp_server is not None


@_xf_mcp
@pytest.mark.acceptance
def test_ac_2_2_analyze_gaps_tool_registered() -> None:
    assert callable(getattr(mcp_server, "analyze_gaps", None))
    mcp_obj = getattr(mcp_server, "mcp", None)
    if mcp_obj is not None and hasattr(mcp_obj, "list_tools"):
        tools = asyncio.run(mcp_obj.list_tools())
        assert "analyze_gaps" in {t.name for t in tools}


@_xf_mcp
@pytest.mark.acceptance
def test_ac_2_3_tool_returns_ranked_gaps() -> None:
    ranked = _call_tool(_POSTINGS, _RESUME)
    assert len(ranked) > 0
    assert "kubernetes" in {r.gap.skill.lower() for r in ranked}


@_xf_mcp
@pytest.mark.acceptance
def test_ac_2_3_tool_empty_postings_returns_empty() -> None:
    assert _call_tool([], _RESUME) == []


@_xf_mcp
@pytest.mark.acceptance
def test_ac_2_3_tool_has_no_company_names() -> None:
    out = mcp_server.analyze_gaps(_POSTINGS, _RESUME)
    if inspect.isawaitable(out):
        out = asyncio.run(out)  # type: ignore[arg-type]
    text = out if isinstance(out, str) else json.dumps(out, default=str)
    assert _COMPANY.lower() not in text.lower()


@_xf_mcp
@pytest.mark.acceptance
def test_ac_2_4_tool_matches_cli_pipeline() -> None:
    assert _call_tool(_POSTINGS, _RESUME) == _expected()


@_xf_mcp
@pytest.mark.acceptance
def test_ac_2_5_tool_schema_documented() -> None:
    fn = mcp_server.analyze_gaps
    assert (inspect.getdoc(fn) or "").strip()
    mcp_obj = getattr(mcp_server, "mcp", None)
    if mcp_obj is not None and hasattr(mcp_obj, "list_tools"):
        tool = next(t for t in asyncio.run(mcp_obj.list_tools()) if t.name == "analyze_gaps")
        assert (tool.description or "").strip()
        props = tool.inputSchema.get("properties", {})
        assert len(props) >= 2


# ---------------------------------------------------------------- Docker


@_xf_if(_DOCKERFILE is not None)
@pytest.mark.acceptance
def test_ac_3_1_dockerfile_exists() -> None:
    assert _DOCKERFILE is not None
    text = _DOCKERFILE.read_text()
    assert re.search(r"^FROM\s+\S+", text, re.M)
    assert re.search(r"^(CMD|ENTRYPOINT)\b", text, re.M)


@_xf_if(_COMPOSE is not None)
@pytest.mark.acceptance
def test_ac_3_2_compose_file_exists() -> None:
    assert _COMPOSE is not None
    text = _COMPOSE.read_text()
    assert "services:" in text
    assert "ports" in text or "expose" in text


@_xf_if(_DOCKERFILE is not None)
@pytest.mark.acceptance
def test_ac_3_3_dockerfile_healthcheck_or_expose() -> None:
    assert _DOCKERFILE is not None
    text = _DOCKERFILE.read_text()
    assert re.search(r"^(HEALTHCHECK|EXPOSE)\b", text, re.M)


@_xf_if(_DOCKERFILE is not None)
@pytest.mark.acceptance
def test_ac_3_3_dockerfile_has_no_baked_in_api_key() -> None:
    assert _DOCKERFILE is not None
    assert not re.search(r"SKILLGAP_API_KEY\s*=\s*\S+", _DOCKERFILE.read_text())


# ---------------------------------------------------------------- SKILL.md


@_xf_if(_skill_mentions_mcp())
@pytest.mark.acceptance
def test_ac_4_1_skill_mentions_mcp() -> None:
    assert _skill_mentions_mcp()


@_xf_if(_skill_has_fallback())
@pytest.mark.acceptance
def test_ac_4_2_skill_describes_in_session_fallback() -> None:
    t = _skill_text()
    assert "in-session" in t
    assert re.search(r"fall\s*back|fallback", t)
    assert "mcp" in t


@pytest.mark.acceptance
def test_ac_4_skill_frontmatter_description_under_200_chars() -> None:
    m = re.search(r"^description:\s*(.+)$", _SKILL.read_text(), re.M)
    assert m is not None
    assert len(m.group(1).strip().strip("\"'")) < 200


# ---------------------------------------------------------------- Consistency


@_xf_server
@pytest.mark.acceptance
def test_ac_5_1_server_and_cli_identical() -> None:
    a = _ranked_from(_post(headers=_AUTH).json())
    b = compute_ranked(_RESUME, _POSTINGS)
    assert [r.model_dump(mode="json") for r in a] == [r.model_dump(mode="json") for r in b]


@_xf_server
@_xf_mcp
@pytest.mark.acceptance
def test_ac_5_1_server_and_mcp_identical() -> None:
    assert _ranked_from(_post(headers=_AUTH).json()) == _call_tool(_POSTINGS, _RESUME)


@_xf_server
@pytest.mark.acceptance
def test_ac_5_2_server_is_deterministic() -> None:
    first = _post(headers=_AUTH).json()
    for _ in range(3):
        assert _post(headers=_AUTH).json() == first


@_xf_mcp
@pytest.mark.acceptance
def test_ac_5_2_mcp_tool_is_deterministic() -> None:
    first = _call_tool(_POSTINGS, _RESUME)
    for _ in range(3):
        assert _call_tool(_POSTINGS, _RESUME) == first


@_xf_server
@pytest.mark.acceptance
def test_ac_5_2_posting_order_does_not_change_set_of_gaps() -> None:
    fwd = _ranked_from(_post(headers=_AUTH).json())
    rev = _ranked_from(
        _post({"postings": list(reversed(_POSTINGS)), "resume": _RESUME}, _AUTH).json()
    )
    assert {r.gap.skill for r in fwd} == {r.gap.skill for r in rev}
