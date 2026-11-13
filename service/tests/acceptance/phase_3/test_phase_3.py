"""Phase 3 acceptance tests: AI skill extraction, schema validation, grounding, retry."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from skillgap import extractor
from skillgap.extractor import (
    NonRetryableExtractionError,
    RetryableExtractionError,
    extract_posting_skills,
    extract_resume_skills,
    parse_extraction_response,
)
from skillgap.grounding import validate_grounding
from skillgap.models import Category, ExtractedSkill, Level

_FIXTURES = Path(__file__).parent.parent.parent / "fixtures"
_RECORDED = _FIXTURES / "recorded_responses"

POSTING_TEXT = """\
Senior Backend Engineer

Requirements:
- 5+ years of Python experience
- Strong knowledge of Kubernetes and Docker
- Experience with AWS services

Nice to have:
- Familiarity with Terraform
- Experience with CI/CD pipelines
"""

RESUME_TEXT = """\
Jane Doe
Languages: Java, Python, JavaScript, TypeScript, SQL
Cloud: AWS (S3, Lambda, ECS), Docker, Kubernetes
Built distributed systems and REST APIs.
"""


def _recorded(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((_RECORDED / name).read_text())
    return data


def _skill(
    name: str = "Python",
    category: Category = Category.language,
    level: Level = Level.required,
    evidence: str = "5+ years of Python experience",
) -> ExtractedSkill:
    return ExtractedSkill(name=name, category=category, level=level, evidence=evidence)


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, "sleep", lambda _s: None)


# --------------------------------------------------------------------------
# Extraction entry points
# --------------------------------------------------------------------------


def test_extract_posting_skills_returns_extracted_skill_list() -> None:
    result = extract_posting_skills(POSTING_TEXT)
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(s, ExtractedSkill) for s in result)


def test_extract_resume_skills_returns_extracted_skill_list() -> None:
    result = extract_resume_skills(RESUME_TEXT)
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(s, ExtractedSkill) for s in result)


def test_posting_extraction_matches_recorded_response() -> None:
    recorded = _recorded("posting_extraction.json")["skills"]
    result = extract_posting_skills(POSTING_TEXT)
    assert [s.name for s in result] == [r["name"] for r in recorded]
    assert [s.evidence for s in result] == [r["evidence"] for r in recorded]


def test_resume_extraction_matches_recorded_response() -> None:
    recorded = _recorded("resume_extraction.json")["skills"]
    result = extract_resume_skills(RESUME_TEXT)
    assert [s.name for s in result] == [r["name"] for r in recorded]


def test_posting_extraction_contains_expected_skills() -> None:
    names = {s.name for s in extract_posting_skills(POSTING_TEXT)}
    assert {"Python", "Kubernetes", "Docker", "AWS", "Terraform", "CI/CD"} <= names


def test_posting_prompt_routes_to_posting_response(monkeypatch: pytest.MonkeyPatch) -> None:
    prompts: list[str] = []

    def spy(prompt: str) -> dict[str, Any]:
        prompts.append(prompt)
        return {"skills": []}

    monkeypatch.setattr("skillgap.extractor._call_llm", spy)
    extract_posting_skills(POSTING_TEXT)
    extract_resume_skills(RESUME_TEXT)
    assert len(prompts) == 2
    assert "job posting" in prompts[0].lower()
    assert POSTING_TEXT.strip() in prompts[0]
    assert RESUME_TEXT.strip() in prompts[1]


def test_extraction_empty_skills_returns_empty_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("skillgap.extractor._call_llm", lambda _p: {"skills": []})
    assert extract_posting_skills(POSTING_TEXT) == []
    assert extract_resume_skills(RESUME_TEXT) == []


# --------------------------------------------------------------------------
# Schema validation
# --------------------------------------------------------------------------


def test_parse_valid_response() -> None:
    data = {
        "skills": [
            {"name": "Go", "category": "language", "level": "required", "evidence": "Go"},
            {"name": "Teamwork", "category": "soft_skill", "level": "preferred", "evidence": "x"},
        ]
    }
    result = parse_extraction_response(data)
    assert result == [
        ExtractedSkill(name="Go", category=Category.language, level=Level.required, evidence="Go"),
        ExtractedSkill(
            name="Teamwork",
            category=Category.soft_skill,
            level=Level.preferred,
            evidence="x",
        ),
    ]


def test_parse_empty_skills_list() -> None:
    assert parse_extraction_response({"skills": []}) == []


def test_parse_recorded_responses() -> None:
    for name in ("posting_extraction.json", "resume_extraction.json"):
        result = parse_extraction_response(_recorded(name))
        assert result
        assert all(isinstance(s, ExtractedSkill) for s in result)


def test_parse_coerces_enum_types() -> None:
    result = parse_extraction_response(
        {"skills": [{"name": "A", "category": "data", "level": "unspecified", "evidence": "A"}]}
    )
    assert result[0].category is Category.data
    assert result[0].level is Level.unspecified


@pytest.mark.parametrize(
    "bad",
    [
        {"name": "X", "category": "not_a_category", "level": "required", "evidence": "X"},
        {"name": "X", "category": "language", "level": "mandatory", "evidence": "X"},
        {"category": "language", "level": "required", "evidence": "X"},
        {"name": "X", "level": "required", "evidence": "X"},
        {"name": "X", "category": "language", "evidence": "X"},
        {"name": "X", "category": "language", "level": "required"},
        {"name": "", "category": "language", "level": "required", "evidence": "X"},
        {"name": "X", "category": "language", "level": "required", "evidence": ""},
        {"name": "   ", "category": "language", "level": "required", "evidence": "X"},
        {"name": "X", "category": "language", "level": "required", "evidence": "  "},
    ],
)
def test_parse_rejects_malformed_skill(bad: dict[str, Any]) -> None:
    with pytest.raises((ValidationError, ValueError)):
        parse_extraction_response({"skills": [bad]})


@pytest.mark.parametrize(
    "bad",
    [{}, {"skills": "Python"}, {"skills": None}, {"results": []}, {"skills": [42]}],
)
def test_parse_rejects_malformed_envelope(bad: dict[str, Any]) -> None:
    with pytest.raises(Exception) as exc:
        parse_extraction_response(bad)
    assert not isinstance(exc.value, (SystemExit, KeyboardInterrupt))


def test_one_bad_skill_is_not_silently_accepted() -> None:
    data = {
        "skills": [
            {"name": "Go", "category": "language", "level": "required", "evidence": "Go"},
            {"name": "X", "category": "bogus", "level": "required", "evidence": "X"},
        ]
    }
    with pytest.raises((ValidationError, ValueError)):
        parse_extraction_response(data)


def test_extract_raises_on_malformed_llm_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "skillgap.extractor._call_llm",
        lambda _p: {"skills": [{"name": "X", "category": "nope", "level": "required"}]},
    )
    with pytest.raises((ValidationError, ValueError, NonRetryableExtractionError)):
        extract_posting_skills(POSTING_TEXT)
    with pytest.raises((ValidationError, ValueError, NonRetryableExtractionError)):
        extract_resume_skills(RESUME_TEXT)


def test_extracted_skill_is_frozen() -> None:
    s = _skill()
    with pytest.raises((ValidationError, TypeError, AttributeError)):
        s.name = "Other"  # type: ignore[misc]


def test_category_enum_values() -> None:
    assert {c.value for c in Category} == {
        "language",
        "framework",
        "cloud_infra",
        "data",
        "ai_ml",
        "practice",
        "customer_facing",
        "soft_skill",
    }


def test_level_enum_values() -> None:
    assert {lv.value for lv in Level} == {"required", "preferred", "unspecified"}


# --------------------------------------------------------------------------
# Categories and levels in extraction output
# --------------------------------------------------------------------------


def test_extracted_categories_are_category_enum_members() -> None:
    for s in extract_posting_skills(POSTING_TEXT) + extract_resume_skills(RESUME_TEXT):
        assert isinstance(s.category, Category)
        assert s.category in set(Category)


def test_posting_levels_are_level_members_and_mixed() -> None:
    result = extract_posting_skills(POSTING_TEXT)
    assert all(isinstance(s.level, Level) for s in result)
    by_name = {s.name: s.level for s in result}
    assert by_name["Python"] is Level.required
    assert by_name["Kubernetes"] is Level.required
    assert by_name["Terraform"] is Level.preferred
    assert by_name["CI/CD"] is Level.preferred


def test_resume_levels_are_unspecified() -> None:
    result = extract_resume_skills(RESUME_TEXT)
    assert result
    assert all(s.level is Level.unspecified for s in result)


def test_posting_categories_mapped_as_recorded() -> None:
    by_name = {s.name: s.category for s in extract_posting_skills(POSTING_TEXT)}
    assert by_name["Python"] is Category.language
    assert by_name["Kubernetes"] is Category.cloud_infra
    assert by_name["CI/CD"] is Category.practice


# --------------------------------------------------------------------------
# Grounding
# --------------------------------------------------------------------------


def test_grounding_accepts_exact_evidence() -> None:
    skills = [_skill()]
    assert validate_grounding(skills, POSTING_TEXT) == skills


def test_grounding_accepts_all_recorded_posting_skills() -> None:
    skills = extract_posting_skills(POSTING_TEXT)
    assert validate_grounding(skills, POSTING_TEXT) == skills


def test_grounding_accepts_all_recorded_resume_skills() -> None:
    skills = extract_resume_skills(RESUME_TEXT)
    assert validate_grounding(skills, RESUME_TEXT) == skills


def test_grounding_is_case_insensitive() -> None:
    skills = [_skill(evidence="5+ YEARS OF PYTHON EXPERIENCE")]
    assert validate_grounding(skills, POSTING_TEXT) == skills


def test_grounding_rejects_fabricated_evidence() -> None:
    fake = _skill(
        name="Rust",
        evidence="Deep expertise in Rust systems programming and kernel development",
    )
    assert validate_grounding([fake], POSTING_TEXT) == []


def test_grounding_filters_only_ungrounded() -> None:
    good = _skill()
    bad = _skill(name="Haskell", evidence="Must have published papers on monad transformers")
    assert validate_grounding([bad, good], POSTING_TEXT) == [good]


def test_grounding_preserves_order() -> None:
    a = _skill(name="Python", evidence="5+ years of Python experience")
    b = _skill(name="AWS", category=Category.cloud_infra, evidence="Experience with AWS services")
    c = _skill(name="Terraform", evidence="Familiarity with Terraform")
    assert validate_grounding([a, b, c], POSTING_TEXT) == [a, b, c]
    assert validate_grounding([c, a, b], POSTING_TEXT) == [c, a, b]


def test_grounding_empty_inputs() -> None:
    assert validate_grounding([], POSTING_TEXT) == []
    assert validate_grounding([_skill()], "") == []


def test_grounding_fuzzy_accepts_minor_variation() -> None:
    # One-character typo should still match under the fuzzy threshold.
    skills = [_skill(evidence="5+ years of Pyhton experience")]
    assert validate_grounding(skills, POSTING_TEXT) == skills


def test_grounding_rejects_unrelated_evidence_even_with_shared_words() -> None:
    skills = [_skill(name="Java", evidence="10 years of Java experience leading teams")]
    assert validate_grounding(skills, POSTING_TEXT) == []


def test_grounding_threshold_is_configurable() -> None:
    skills = [_skill(evidence="5+ years of Pyhton experience")]
    assert validate_grounding(skills, POSTING_TEXT, threshold=0.5) == skills
    assert validate_grounding(skills, POSTING_TEXT, threshold=1.0) == []


def test_grounding_does_not_mutate_input() -> None:
    skills = [_skill(), _skill(name="Fake", evidence="entirely fabricated sentence here")]
    snapshot = list(skills)
    validate_grounding(skills, POSTING_TEXT)
    assert skills == snapshot


def test_adversarial_llm_output_is_filtered_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    adversarial = {
        "skills": [
            {
                "name": "Python",
                "category": "language",
                "level": "required",
                "evidence": "5+ years of Python experience",
            },
            {
                "name": "Quantum Computing",
                "category": "ai_ml",
                "level": "required",
                "evidence": "PhD in quantum error correction required",
            },
        ]
    }
    monkeypatch.setattr("skillgap.extractor._call_llm", lambda _p: adversarial)
    skills = extract_posting_skills(POSTING_TEXT)
    grounded = validate_grounding(skills, POSTING_TEXT)
    assert [s.name for s in grounded] == ["Python"]


def test_grounding_against_posting_fixtures() -> None:
    files = sorted((_FIXTURES / "postings").rglob("*.txt"))
    assert files
    text = files[0].read_text()
    fake = _skill(name="Fake", evidence="zzz qqq nonexistent fabricated requirement xyzzy")
    assert validate_grounding([fake], text) == []
    first_line = next(ln.strip() for ln in text.splitlines() if len(ln.strip()) > 15)
    real = _skill(name="Real", evidence=first_line)
    assert validate_grounding([real], text) == [real]


# --------------------------------------------------------------------------
# Retry logic and exceptions
# --------------------------------------------------------------------------


def test_exception_classes_are_distinct_exceptions() -> None:
    assert issubclass(RetryableExtractionError, Exception)
    assert issubclass(NonRetryableExtractionError, Exception)
    assert not issubclass(RetryableExtractionError, NonRetryableExtractionError)
    assert not issubclass(NonRetryableExtractionError, RetryableExtractionError)
    assert "rate" in (RetryableExtractionError.__doc__ or "").lower()
    with pytest.raises(RetryableExtractionError, match="boom"):
        raise RetryableExtractionError("boom")


def test_retry_recovers_from_transient_failure(
    monkeypatch: pytest.MonkeyPatch, no_sleep: None
) -> None:
    calls = {"n": 0}

    def flaky(_p: str) -> dict[str, Any]:
        calls["n"] += 1
        if calls["n"] < 2:
            raise RetryableExtractionError("rate limited")
        return _recorded("posting_extraction.json")

    monkeypatch.setattr("skillgap.extractor._call_llm", flaky)
    result = extract_posting_skills(POSTING_TEXT)
    assert calls["n"] == 2
    assert len(result) == len(_recorded("posting_extraction.json")["skills"])


def test_retry_gives_up_after_persistent_failure(
    monkeypatch: pytest.MonkeyPatch, no_sleep: None
) -> None:
    calls = {"n": 0}

    def always(_p: str) -> dict[str, Any]:
        calls["n"] += 1
        raise RetryableExtractionError("rate limited")

    monkeypatch.setattr("skillgap.extractor._call_llm", always)
    with pytest.raises(RetryableExtractionError):
        extract_resume_skills(RESUME_TEXT)
    assert 2 <= calls["n"] <= 10


def test_non_retryable_error_is_not_retried(
    monkeypatch: pytest.MonkeyPatch, no_sleep: None
) -> None:
    calls = {"n": 0}

    def bad(_p: str) -> dict[str, Any]:
        calls["n"] += 1
        raise NonRetryableExtractionError("bad request")

    monkeypatch.setattr("skillgap.extractor._call_llm", bad)
    with pytest.raises(NonRetryableExtractionError):
        extract_posting_skills(POSTING_TEXT)
    assert calls["n"] == 1


def test_retry_uses_backoff_delays(monkeypatch: pytest.MonkeyPatch) -> None:
    delays: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda s: delays.append(s))

    def always(_p: str) -> dict[str, Any]:
        raise RetryableExtractionError("transient")

    monkeypatch.setattr("skillgap.extractor._call_llm", always)
    with pytest.raises(RetryableExtractionError):
        extract_posting_skills(POSTING_TEXT)
    assert delays
    assert all(d > 0 for d in delays)
    assert delays == sorted(delays)


# --------------------------------------------------------------------------
# No live calls
# --------------------------------------------------------------------------


def test_llm_call_is_mocked_in_acceptance_tests() -> None:
    assert extractor._call_llm is not None
    assert extractor._call_llm.__module__ != "skillgap.extractor"


def test_no_network_when_llm_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    def deny(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket.socket, "connect", deny)
    assert extract_posting_skills(POSTING_TEXT)
    assert extract_resume_skills(RESUME_TEXT)
