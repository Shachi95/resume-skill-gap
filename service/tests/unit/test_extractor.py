"""Unit tests for the AI skill extractor."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from skillgap.extractor import (
    NonRetryableExtractionError,
    RetryableExtractionError,
    extract_posting_skills,
    extract_resume_skills,
    parse_extraction_response,
)
from skillgap.models import ExtractedSkill

_VALID_RESPONSE: dict[str, Any] = {
    "skills": [
        {
            "name": "Python",
            "category": "language",
            "level": "required",
            "evidence": "5+ years of Python experience",
        },
        {
            "name": "Docker",
            "category": "cloud_infra",
            "level": "preferred",
            "evidence": "Familiarity with Docker",
        },
    ]
}


def _mock_call_llm(response: dict[str, Any]) -> Any:
    return patch("skillgap.extractor._call_llm", return_value=response)


class TestParseExtractionResponse:
    def test_valid_response(self) -> None:
        result = parse_extraction_response(_VALID_RESPONSE)
        assert len(result) == 2
        assert all(isinstance(s, ExtractedSkill) for s in result)
        assert result[0].name == "Python"

    def test_empty_skills_list(self) -> None:
        result = parse_extraction_response({"skills": []})
        assert result == []

    def test_malformed_missing_fields(self) -> None:
        with pytest.raises((ValidationError, KeyError, TypeError)):
            parse_extraction_response({"skills": [{"name": "Python"}]})

    def test_missing_skills_key(self) -> None:
        with pytest.raises(KeyError):
            parse_extraction_response({})


class TestExtractPostingSkills:
    def test_returns_skills(self) -> None:
        with _mock_call_llm(_VALID_RESPONSE):
            result = extract_posting_skills("Requirements:\n- Python")
        assert len(result) == 2
        assert all(isinstance(s, ExtractedSkill) for s in result)

    def test_calls_llm_with_posting_prompt(self) -> None:
        with patch("skillgap.extractor._call_llm", return_value=_VALID_RESPONSE) as mock:
            extract_posting_skills("Some posting text")
        prompt = mock.call_args[0][0]
        assert "job posting" in prompt.lower()


class TestExtractResumeSkills:
    def test_returns_skills(self) -> None:
        with _mock_call_llm(_VALID_RESPONSE):
            result = extract_resume_skills("Languages: Python, Java")
        assert len(result) == 2

    def test_calls_llm_with_resume_prompt(self) -> None:
        with patch("skillgap.extractor._call_llm", return_value=_VALID_RESPONSE) as mock:
            extract_resume_skills("Some resume text")
        prompt = mock.call_args[0][0]
        assert "resume" in prompt.lower()


class TestErrorClasses:
    def test_retryable_is_exception(self) -> None:
        assert issubclass(RetryableExtractionError, Exception)

    def test_non_retryable_is_exception(self) -> None:
        assert issubclass(NonRetryableExtractionError, Exception)

    def test_retryable_error_raised(self) -> None:
        with pytest.raises(RetryableExtractionError):
            raise RetryableExtractionError("rate limited")

    def test_non_retryable_error_raised(self) -> None:
        with pytest.raises(NonRetryableExtractionError):
            raise NonRetryableExtractionError("bad request")
