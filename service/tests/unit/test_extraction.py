"""Unit tests for AnthropicLLMClient, _merge and _split (no network)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import anthropic
import httpx
import pytest

from skillgap.config import AliasConfig
from skillgap.extraction import (
    AnthropicLLMClient,
    ExtractionConfig,
    _merge,
    _split,
)
from skillgap.extractor import NonRetryableExtractionError, RetryableExtractionError
from skillgap.models import Category, ExtractedSkill, ExtractionResult, Level
from skillgap.normalizer import build_lookup

_REQ = httpx.Request("POST", "https://example.invalid/v1/messages")


def _response(status: int) -> httpx.Response:
    return httpx.Response(status, request=_REQ)


def _tool_response(data: dict[str, Any]) -> SimpleNamespace:
    block = SimpleNamespace(type="tool_use", name="record_skills", input=data)
    return SimpleNamespace(content=[block])


def _client(create: MagicMock) -> AnthropicLLMClient:
    sdk = MagicMock()
    sdk.messages.create = create
    return AnthropicLLMClient(client=sdk)


_VALID = {
    "skills": [
        {
            "name": "Python",
            "category": "language",
            "level": "required",
            "evidence": "Python",
        }
    ]
}


def test_config_forwarded_and_tool_choice_forced() -> None:
    create = MagicMock(return_value=_tool_response(_VALID))
    cfg = ExtractionConfig(model="test-model", max_tokens=123)
    result = _client(create).extract_skills("We need Python", "jd", cfg)
    assert result.skills[0].name == "Python"
    kwargs = create.call_args.kwargs
    assert kwargs["model"] == "test-model"
    assert kwargs["max_tokens"] == 123
    assert kwargs["tool_choice"] == {"type": "tool", "name": "record_skills"}


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (
            anthropic.RateLimitError("rl", response=_response(429), body=None),
            RetryableExtractionError,
        ),
        (
            anthropic.APIStatusError("boom", response=_response(500), body=None),
            RetryableExtractionError,
        ),
        (
            anthropic.APIStatusError("bad", response=_response(400), body=None),
            NonRetryableExtractionError,
        ),
        (anthropic.APIConnectionError(request=_REQ), RetryableExtractionError),
        (anthropic.AnthropicError("base"), NonRetryableExtractionError),
    ],
)
def test_status_mapping(exc: Exception, expected: type[Exception]) -> None:
    create = MagicMock(side_effect=exc)
    with pytest.raises(expected):
        _client(create).extract_skills("text", "jd", ExtractionConfig())


def test_schema_failure_is_non_retryable() -> None:
    create = MagicMock(return_value=_tool_response({"skills": [{"name": "x"}]}))
    with pytest.raises(NonRetryableExtractionError):
        _client(create).extract_skills("text", "resume", ExtractionConfig())


def _skill(name: str, level: Level) -> ExtractedSkill:
    return ExtractedSkill(name=name, category=Category.cloud_infra, level=level, evidence=name)


def test_merge_strongest_level_wins(alias_config: AliasConfig) -> None:
    lookup = build_lookup(alias_config)
    a = ExtractionResult(skills=(_skill("kubernetes", Level.preferred),))
    b = ExtractionResult(skills=(_skill("kubernetes", Level.required),))
    merged = _merge([a, b], lookup, alias_config)
    assert len(merged.skills) == 1
    assert merged.skills[0].level == Level.required


def test_merge_dedups_by_canonical(alias_config: AliasConfig) -> None:
    lookup = build_lookup(alias_config)
    a = ExtractionResult(skills=(_skill("k8s", Level.unspecified),))
    b = ExtractionResult(skills=(_skill("kubernetes", Level.unspecified),))
    merged = _merge([a, b], lookup, alias_config)
    assert len(merged.skills) == 1


@pytest.mark.parametrize(
    "text",
    ["", "single line", "a\nb\nc\nd", "no newline " * 50, "line one\nline two is longer\nthree\n"],
)
def test_split_no_data_loss(text: str) -> None:
    first, second = _split(text)
    assert first + second == text
