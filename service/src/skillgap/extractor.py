"""AI skill extraction from posting and resume text via Anthropic API."""

from __future__ import annotations

import time
from typing import Any

import anthropic

from skillgap.models import Category, ExtractedSkill, Level

_MODEL = "claude-sonnet-4-20250514"
_MAX_TOKENS = 4096
_MAX_RETRIES = 3
_BASE_DELAY = 1.0


class RetryableExtractionError(Exception):
    """Raised for rate limits and transient failures that can be retried."""


class NonRetryableExtractionError(Exception):
    """Raised for client errors that should not be retried."""


_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Skill name as written in the text"},
                    "category": {
                        "type": "string",
                        "enum": [c.value for c in Category],
                    },
                    "level": {
                        "type": "string",
                        "enum": [lv.value for lv in Level],
                    },
                    "evidence": {
                        "type": "string",
                        "description": "Exact phrase from the source text",
                    },
                },
                "required": ["name", "category", "level", "evidence"],
            },
        }
    },
    "required": ["skills"],
}


def _build_posting_prompt(text: str) -> str:
    categories = ", ".join(c.value for c in Category)
    return (
        "Extract all technical skills from this job posting text. "
        "For each skill provide:\n"
        f"- name: the skill as written\n"
        f"- category: one of {categories}\n"
        "- level: 'required' if from a Requirements section, "
        "'preferred' if from a Preferred section, 'unspecified' otherwise\n"
        "- evidence: the exact phrase from the text mentioning this skill\n\n"
        f"Job posting:\n{text}"
    )


def _build_resume_prompt(text: str) -> str:
    categories = ", ".join(c.value for c in Category)
    return (
        "Extract all technical skills from this resume text. "
        "For each skill provide:\n"
        f"- name: the skill as written\n"
        f"- category: one of {categories}\n"
        "- level: always 'unspecified'\n"
        "- evidence: the exact phrase from the text mentioning this skill\n\n"
        f"Resume:\n{text}"
    )


def _call_llm(prompt: str) -> dict[str, Any]:
    """Call the Anthropic API and return the tool_use input dict.

    This is the only function that touches the network.
    Monkeypatched in tests to return recorded fixtures.
    """
    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            tools=[
                {
                    "name": "extract_skills",
                    "description": "Extract skills from text",
                    "input_schema": _EXTRACTION_SCHEMA,
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.RateLimitError as e:
        raise RetryableExtractionError(str(e)) from e
    except anthropic.APIStatusError as e:
        if e.status_code >= 500:
            raise RetryableExtractionError(str(e)) from e
        raise NonRetryableExtractionError(str(e)) from e

    for block in response.content:
        if block.type == "tool_use" and block.name == "extract_skills":
            return block.input
    raise NonRetryableExtractionError("No extract_skills tool_use block in response")


def _call_with_retry(prompt: str) -> dict[str, Any]:
    """Wrap _call_llm with exponential backoff for retryable errors."""
    last_err: RetryableExtractionError | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return _call_llm(prompt)
        except RetryableExtractionError as e:
            last_err = e
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_BASE_DELAY * (2**attempt))
    raise last_err  # type: ignore[misc]


def parse_extraction_response(data: dict[str, Any]) -> list[ExtractedSkill]:
    """Parse a raw extraction response dict into validated ExtractedSkill models.

    Accepts the format: {"skills": [{"name": ..., "category": ..., "level": ..., "evidence": ...}]}
    """
    skills_raw = data["skills"]
    if not isinstance(skills_raw, list):
        raise TypeError("Expected 'skills' to be a list")

    return [ExtractedSkill(**item) for item in skills_raw]


def extract_posting_skills(text: str) -> list[ExtractedSkill]:
    """Extract skills from posting text using the LLM."""
    prompt = _build_posting_prompt(text)
    raw = _call_with_retry(prompt)
    return parse_extraction_response(raw)


def extract_resume_skills(text: str) -> list[ExtractedSkill]:
    """Extract skills from resume text using the LLM."""
    prompt = _build_resume_prompt(text)
    raw = _call_with_retry(prompt)
    return parse_extraction_response(raw)
