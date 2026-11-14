"""Verified skill extraction: LLM call, verification loop, dictionary fallback."""

from __future__ import annotations

import logging
import re
import time
from typing import Literal, Protocol

import anthropic
from pydantic import BaseModel, ValidationError

from skillgap.config import AliasConfig, load_config
from skillgap.extractor import (
    _EXTRACTION_SCHEMA,
    NonRetryableExtractionError,
    RetryableExtractionError,
    _build_posting_prompt,
    _build_resume_prompt,
)
from skillgap.models import (
    AcceptedSkill,
    ExtractedSkill,
    ExtractionResult,
    Level,
    VerifiedExtractionResult,
    VerifyReport,
)
from skillgap.normalizer import build_lookup, normalize
from skillgap.verification import verify

logger = logging.getLogger(__name__)

TOKEN_BUDGET: int = 4096

_TOOL_NAME = "record_skills"
_LEVEL_RANK: dict[Level, int] = {Level.required: 2, Level.unspecified: 1, Level.preferred: 0}


class ExtractionError(Exception):
    """Base class for all extraction errors."""


class LLMExtractionError(ExtractionError):
    """Raised after retry exhaustion in extract()."""

    def __init__(self, message: str, attempts: int) -> None:
        super().__init__(message)
        self.attempts = attempts


class ExtractionConfig(BaseModel, frozen=True):
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    max_retries: int = 3
    base_delay: float = 1.0


class LLMClient(Protocol):
    def extract_skills(
        self, text: str, kind: Literal["jd", "resume"], config: ExtractionConfig
    ) -> ExtractionResult: ...


class AnthropicLLMClient:
    """LLMClient backed by the Anthropic SDK (the only network boundary)."""

    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        self._client = client

    def _sdk(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic()
        return self._client

    def extract_skills(
        self, text: str, kind: Literal["jd", "resume"], config: ExtractionConfig
    ) -> ExtractionResult:
        prompt = _build_posting_prompt(text) if kind == "jd" else _build_resume_prompt(text)
        try:
            response = self._sdk().messages.create(
                model=config.model,
                max_tokens=config.max_tokens,
                tools=[
                    {
                        "name": _TOOL_NAME,
                        "description": "Record the skills found in the text",
                        "input_schema": _EXTRACTION_SCHEMA,
                    }
                ],
                tool_choice={"type": "tool", "name": _TOOL_NAME},
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.RateLimitError as e:
            raise RetryableExtractionError(str(e)) from e
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                raise RetryableExtractionError(str(e)) from e
            raise NonRetryableExtractionError(str(e)) from e
        except anthropic.APIConnectionError as e:
            raise RetryableExtractionError(str(e)) from e
        except anthropic.AnthropicError as e:
            raise NonRetryableExtractionError(str(e)) from e

        for block in response.content:
            if block.type == "tool_use" and block.name == _TOOL_NAME:
                try:
                    return ExtractionResult.model_validate(block.input)
                except ValidationError as e:
                    raise NonRetryableExtractionError(f"schema validation failed: {e}") from e
        raise NonRetryableExtractionError(f"No {_TOOL_NAME} tool_use block in response")


def _call_with_retry(
    client: LLMClient, text: str, kind: Literal["jd", "resume"], config: ExtractionConfig
) -> ExtractionResult:
    total = config.max_retries + 1
    last_exc: RetryableExtractionError | None = None
    for attempt in range(total):
        try:
            return client.extract_skills(text, kind, config)
        except RetryableExtractionError as e:
            last_exc = e
            if attempt < total - 1:
                time.sleep(config.base_delay * (2**attempt))
    assert last_exc is not None
    raise LLMExtractionError(
        f"LLM extraction failed after {total} attempts", attempts=total
    ) from last_exc


def _split(text: str) -> tuple[str, str]:
    mid = len(text) // 2
    nl = text.find("\n", mid)
    prev = text.rfind("\n", 0, mid)
    candidates = [i for i in (prev, nl) if i > 0]
    if candidates:
        mid = min(candidates, key=lambda i: abs(i - len(text) // 2)) + 1
    return text[:mid], text[mid:]


def _merge(
    results: list[ExtractionResult], lookup: dict[str, str], alias_config: AliasConfig
) -> ExtractionResult:
    merged: dict[str, ExtractedSkill] = {}
    for result in results:
        for skill in result.skills:
            resolved = normalize(skill.name, lookup, alias_config)
            key = resolved.canonical_name if resolved else skill.name.strip().lower()
            existing = merged.get(key)
            if existing is None or _LEVEL_RANK[skill.level] > _LEVEL_RANK[existing.level]:
                merged[key] = skill
    return ExtractionResult(skills=tuple(merged.values()))


def extract(
    text: str,
    kind: Literal["jd", "resume"],
    *,
    client: LLMClient | None = None,
    config: ExtractionConfig | None = None,
    lookup: dict[str, str] | None = None,
    alias_config: AliasConfig | None = None,
) -> ExtractionResult:
    """Extract skills with the LLM, splitting oversized text into two calls."""
    cfg = config or ExtractionConfig()
    llm = client if client is not None else AnthropicLLMClient()
    if len(text) // 4 <= TOKEN_BUDGET:
        return _call_with_retry(llm, text, kind, cfg)
    first, second = _split(text)
    if alias_config is None:
        alias_config, _ = load_config()
    if lookup is None:
        lookup = build_lookup(alias_config)
    parts = [_call_with_retry(llm, part, kind, cfg) for part in (first, second)]
    return _merge(parts, lookup, alias_config)


_BULLET = re.compile(r"^\s*[-*•]\s")


def _in_list_context(text: str, start: int, end: int, line_start: int, line_end: int) -> bool:
    line = text[line_start:line_end]
    if _BULLET.match(line):
        return True
    before = text[line_start:start].rstrip()
    after = text[end:line_end].lstrip()
    return before.endswith(",") or after.startswith(",")


def extract_dictionary(
    text: str,
    kind: Literal["jd", "resume"],
    lookup: dict[str, str],
    config: AliasConfig,
) -> list[ExtractedSkill]:
    """Scan text for known skill names and aliases (deterministic fallback)."""
    if not text or not lookup:
        return []
    keys = sorted((k for k in lookup if k), key=lambda k: (-len(k), k))
    pattern = re.compile(
        r"(?<!\w)(?:" + "|".join(re.escape(k) for k in keys) + r")(?!\w)", re.IGNORECASE
    )
    found: dict[str, ExtractedSkill] = {}
    for m in pattern.finditer(text):
        canonical = lookup.get(m.group(0).lower())
        if canonical is None or canonical in found:
            continue
        entry = config.skills[canonical]
        line_start = text.rfind("\n", 0, m.start()) + 1
        line_end = text.find("\n", m.end())
        if line_end == -1:
            line_end = len(text)
        if entry.ambiguous and not _in_list_context(text, m.start(), m.end(), line_start, line_end):
            continue
        evidence = text[line_start:line_end].strip()
        found[canonical] = ExtractedSkill(
            name=canonical,
            category=entry.category,
            level=Level.unspecified,
            evidence=evidence,
        )
    return list(found.values())


def _retry_text(text: str, previous: ExtractionResult | None, report: VerifyReport | None) -> str:
    if report is None:
        return text
    lines = [text, "", "Your previous extraction failed verification. Fix these errors:"]
    for err in report.errors:
        lines.append(f"- {err.reason}: {err.skill_name} {err.detail}".rstrip())
    if previous is not None:
        lines.append("Previous extraction:")
        for s in previous.skills:
            lines.append(f"- {s.name} (evidence: {s.evidence})")
    lines.append("Only report skills whose evidence is quoted exactly from the text above.")
    return "\n".join(lines)


def extract_verified(
    text: str,
    kind: Literal["jd", "resume"],
    *,
    client: LLMClient | None = None,
    config: ExtractionConfig | None = None,
    lookup: dict[str, str] | None = None,
    alias_config: AliasConfig | None = None,
    max_attempts: int = 3,
) -> VerifiedExtractionResult:
    """Extract, verify and retry; fall back to the dictionary scan. Never raises."""
    if alias_config is None:
        alias_config, _ = load_config()
    if lookup is None:
        lookup = build_lookup(alias_config)
    cfg = config or ExtractionConfig()

    last_report: VerifyReport | None = None
    previous: ExtractionResult | None = None
    attempts = 0
    for attempt in range(1, max_attempts + 1):
        attempts = attempt
        try:
            result = extract(
                _retry_text(text, previous, last_report),
                kind,
                client=client,
                config=cfg,
                lookup=lookup,
                alias_config=alias_config,
            )
        except (LLMExtractionError, NonRetryableExtractionError) as e:
            logger.info("attempt %d: extraction failed: %s", attempt, e)
            continue
        report = verify(text, result, lookup, alias_config)
        logger.info(
            "attempt %d: %d errors, %d accepted", attempt, len(report.errors), len(report.accepted)
        )
        if report.ok:
            return VerifiedExtractionResult(
                skills=report.accepted,
                source="llm",
                candidates=report.candidates,
                attempts=attempt,
            )
        last_report, previous = report, result

    fallback = extract_dictionary(text, kind, lookup, alias_config)
    return VerifiedExtractionResult(
        skills=tuple(
            AcceptedSkill(skill=s, canonical_name=s.name, category=s.category) for s in fallback
        ),
        source="fallback",
        errors=last_report.errors if last_report else (),
        attempts=attempts,
    )


__all__ = [
    "TOKEN_BUDGET",
    "AnthropicLLMClient",
    "ExtractionConfig",
    "ExtractionError",
    "LLMClient",
    "LLMExtractionError",
    "extract",
    "extract_dictionary",
    "extract_verified",
]
