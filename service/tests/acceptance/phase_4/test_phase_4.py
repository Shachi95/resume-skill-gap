"""Phase 4 acceptance tests: verified extraction pipeline.

New modules (extraction, verification) and new models are imported lazily inside
helpers so a missing implementation produces an xfail rather than a collection
error.  Phase 4 uses dependency injection via the LLMClient Protocol; tests never
patch skillgap functions or assert on SDK types.
"""

from __future__ import annotations

import json as json_mod
import logging
import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from skillgap.config import load_config
from skillgap.extractor import (
    NonRetryableExtractionError,
    RetryableExtractionError,
)
from skillgap.grounding import _is_grounded
from skillgap.models import Category, ExtractedSkill, Level
from skillgap.normalizer import build_lookup, normalize

_NOT_IMPL = "Phase 4 not implemented"
_NO_MODELS = "Phase 4 models not added"
_xfail_impl = pytest.mark.xfail(strict=True, reason=_NOT_IMPL)
_xfail_models = pytest.mark.xfail(strict=True, reason=_NO_MODELS)

_REPO_ROOT = Path(__file__).resolve().parents[4]
_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"

_ALIAS_CONFIG, _ = load_config()
_LOOKUP = build_lookup(_ALIAS_CONFIG)

_TEXT = """Senior Backend Engineer
Requirements:
- 5+ years of Python experience
- Strong knowledge of Kubernetes and Docker
- Experience with AWS cloud services
Nice to have: Terraform for infrastructure automation
"""

_LINES = [ln.strip() for ln in _TEXT.splitlines() if ln.strip()]

_GOOD_SKILLS = (
    ExtractedSkill(
        name="Python",
        category=Category.language,
        level=Level.required,
        evidence="5+ years of Python experience",
    ),
    ExtractedSkill(
        name="Kubernetes",
        category=Category.cloud_infra,
        level=Level.required,
        evidence="Strong knowledge of Kubernetes and Docker",
    ),
    ExtractedSkill(
        name="Docker",
        category=Category.cloud_infra,
        level=Level.required,
        evidence="Strong knowledge of Kubernetes and Docker",
    ),
    ExtractedSkill(
        name="AWS",
        category=Category.cloud_infra,
        level=Level.required,
        evidence="Experience with AWS cloud services",
    ),
)


# --------------------------------------------------------------------------- helpers


def _extraction() -> Any:
    import skillgap.extraction as m

    return m


def _verification() -> Any:
    import skillgap.verification as m

    return m


def _models() -> Any:
    import skillgap.models as m

    # Force AttributeError (-> xfail) when the new models are missing.
    for name in (
        "ExtractionResult",
        "AcceptedSkill",
        "VerifyError",
        "VerifyReport",
        "VerifiedExtractionResult",
    ):
        getattr(m, name)
    return m


def _result(skills: tuple[ExtractedSkill, ...] | list[ExtractedSkill]) -> Any:
    return _models().ExtractionResult(skills=tuple(skills))


def _run_verify(
    skills: tuple[ExtractedSkill, ...] | list[ExtractedSkill],
    text: str = _TEXT,
    **kwargs: Any,
) -> Any:
    return _verification().verify(text, _result(skills), _LOOKUP, _ALIAS_CONFIG, **kwargs)


def _sk(
    name: str,
    evidence: str,
    level: Level = Level.required,
    category: Category = Category.language,
) -> ExtractedSkill:
    return ExtractedSkill(name=name, category=category, level=level, evidence=evidence)


def _tool_input(skills: tuple[ExtractedSkill, ...] | list[ExtractedSkill]) -> dict[str, Any]:
    return {"skills": [s.model_dump(mode="json") for s in skills]}


_BAD_SKILLS = (
    _sk("Python", "this evidence phrase is nowhere in the posting"),
    _sk("Docker", "another invented quote about containers galore"),
    _sk("AWS", "yet another fabricated sentence for testing"),
)


class FakeLLMClient:
    """Implements LLMClient Protocol, scripted with outcomes (ExtractionResult | Exception)."""

    def __init__(self, *outcomes: Any) -> None:
        self._outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []

    def extract_skills(self, text: str, kind: str, config: Any) -> Any:
        self.calls.append({"text": text, "kind": kind, "config": config})
        outcome = self._outcomes.pop(0) if len(self._outcomes) > 1 else self._outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _fast_config(**overrides: Any) -> Any:
    values: dict[str, Any] = {"base_delay": 0.0, "max_retries": 2}
    values.update(overrides)
    return _extraction().ExtractionConfig(**values)


def _good_result() -> Any:
    return _models().ExtractionResult(skills=_GOOD_SKILLS)


def _bad_result() -> Any:
    return _models().ExtractionResult(skills=_BAD_SKILLS)


def _empty_result() -> Any:
    return _models().ExtractionResult(skills=())


def _extraction_error(status: int) -> Exception:
    """Return the right error type for an HTTP status code."""
    if status == 429 or status >= 500:
        return RetryableExtractionError(f"status {status}")
    return NonRetryableExtractionError(f"status {status}")


# --------------------------------------------------------------------------- 5.x config


@_xfail_impl
class TestExtractionConfig:
    def test_defaults(self) -> None:
        # AC-5.1
        cfg = _extraction().ExtractionConfig()
        assert cfg.model == "claude-sonnet-4-20250514"
        assert cfg.max_tokens == 4096
        assert cfg.max_retries == 3
        assert cfg.base_delay == 1.0

    def test_frozen(self) -> None:
        # AC-5.1
        cfg = _extraction().ExtractionConfig()
        with pytest.raises(ValidationError):
            cfg.max_tokens = 1

    def test_overridable(self) -> None:
        # AC-5.1
        cfg = _extraction().ExtractionConfig(
            model="m", max_tokens=10, max_retries=1, base_delay=0.0
        )
        assert (cfg.model, cfg.max_tokens) == ("m", 10)
        assert (cfg.max_retries, cfg.base_delay) == (1, 0.0)

    def test_config_passed_to_client(self) -> None:
        # AC-5.2
        client = FakeLLMClient(_good_result())
        cfg = _fast_config(model="claude-custom-model", max_tokens=777)
        _extraction().extract(_TEXT, "jd", client=client, config=cfg)
        assert client.calls[0]["config"].model == "claude-custom-model"
        assert client.calls[0]["config"].max_tokens == 777

    def test_max_retries_controls_transient_retries(self) -> None:
        # AC-5.3
        LLMExtractionError = _extraction().LLMExtractionError
        client = FakeLLMClient(_extraction_error(500))
        cfg = _fast_config(max_retries=2)
        with pytest.raises(LLMExtractionError) as exc_info:
            _extraction().extract(_TEXT, "jd", client=client, config=cfg)
        assert exc_info.value.attempts >= 2
        assert exc_info.value.__cause__ is not None
        assert 2 <= len(client.calls) <= 3

    def test_zero_retries_makes_single_call(self) -> None:
        # AC-5.3 boundary
        LLMExtractionError = _extraction().LLMExtractionError
        client = FakeLLMClient(_extraction_error(500), _good_result())
        cfg = _fast_config(max_retries=0)
        with pytest.raises(LLMExtractionError) as exc_info:
            _extraction().extract(_TEXT, "jd", client=client, config=cfg)
        assert exc_info.value.attempts == 1
        assert exc_info.value.__cause__ is not None
        assert len(client.calls) == 1


# --------------------------------------------------------------------------- models


@_xfail_models
class TestNewModels:
    def test_extraction_result_roundtrip_and_frozen(self) -> None:
        m = _models()
        r = m.ExtractionResult(skills=_GOOD_SKILLS)
        assert r.skills == _GOOD_SKILLS
        assert isinstance(r.skills, tuple)
        with pytest.raises(ValidationError):
            r.skills = ()

    def test_extraction_result_validates_from_dict(self) -> None:
        m = _models()
        r = m.ExtractionResult.model_validate(_tool_input(_GOOD_SKILLS))
        assert len(r.skills) == 4
        assert r.skills[0].level == Level.required

    def test_extraction_result_rejects_bad_skill(self) -> None:
        m = _models()
        with pytest.raises(ValidationError):
            m.ExtractionResult.model_validate({"skills": [{"name": "x"}]})

    def test_accepted_skill(self) -> None:
        m = _models()
        a = m.AcceptedSkill(
            skill=_GOOD_SKILLS[0], canonical_name="python", category=Category.language
        )
        assert a.canonical_name == "python"
        with pytest.raises(ValidationError):
            a.canonical_name = "x"
        with pytest.raises(ValidationError):
            m.AcceptedSkill(skill=_GOOD_SKILLS[0], canonical_name="python", category="bogus")

    def test_verify_error_reasons(self) -> None:
        m = _models()
        for reason in (
            "evidence_not_in_text",
            "skill_not_in_text",
            "too_few_skills",
            "too_many_skills",
        ):
            e = m.VerifyError(skill_name="x", reason=reason)
            assert e.detail == ""
        with pytest.raises(ValidationError):
            m.VerifyError(skill_name="x", reason="something_else")

    def test_verify_error_frozen(self) -> None:
        e = _models().VerifyError(skill_name="x", reason="too_few_skills", detail="d")
        with pytest.raises(ValidationError):
            e.detail = "z"

    def test_verify_report_fields(self) -> None:
        m = _models()
        rep = m.VerifyReport(ok=False, accepted=(), candidates=(), errors=())
        assert rep.ok is False
        assert rep.accepted == () and rep.candidates == () and rep.errors == ()
        with pytest.raises(ValidationError):
            rep.ok = True
        with pytest.raises(ValidationError):
            m.VerifyReport(ok=True)

    def test_verified_extraction_result_defaults(self) -> None:
        m = _models()
        r = m.VerifiedExtractionResult(skills=(), source="llm")
        assert r.candidates == ()
        assert r.errors == ()
        assert r.attempts == 1
        with pytest.raises(ValidationError):
            r.attempts = 2

    def test_verified_extraction_result_source_literal(self) -> None:
        m = _models()
        assert m.VerifiedExtractionResult(skills=(), source="fallback").source == "fallback"
        with pytest.raises(ValidationError):
            m.VerifiedExtractionResult(skills=(), source="cache")

    def test_existing_models_unchanged(self) -> None:
        # "No existing models are modified" -- guard the ExtractedSkill field set.
        assert set(ExtractedSkill.model_fields) == {"name", "category", "level", "evidence"}
        _models()  # and the new ones must exist


# --------------------------------------------------------------------------- extract


@_xfail_impl
class TestExtract:
    def test_returns_extraction_result(self) -> None:
        # AC-1.5
        client = FakeLLMClient(_good_result())
        res = _extraction().extract(_TEXT, "jd", client=client)
        assert isinstance(res, _models().ExtractionResult)
        assert res.skills == _GOOD_SKILLS

    def test_jd_kind_routing(self) -> None:
        # AC-1.1
        client = FakeLLMClient(_good_result())
        _extraction().extract(_TEXT, "jd", client=client)
        assert client.calls[0]["kind"] == "jd"
        assert client.calls[0]["text"] == _TEXT

    def test_resume_kind_routing(self) -> None:
        # AC-1.1
        client = FakeLLMClient(_good_result())
        _extraction().extract(_TEXT, "resume", client=client)
        assert client.calls[0]["kind"] == "resume"
        assert client.calls[0]["text"] == _TEXT

    def test_returns_client_result(self) -> None:
        # AC-1.2: extract() returns the validated ExtractionResult from the client
        client = FakeLLMClient(_good_result())
        res = _extraction().extract(_TEXT, "jd", client=client)
        assert res.skills == _GOOD_SKILLS

    def test_default_config_used(self) -> None:
        # AC-1.3: config defaults applied when none provided
        client = FakeLLMClient(_good_result())
        _extraction().extract(_TEXT, "jd", client=client)
        cfg = client.calls[0]["config"]
        defaults = _extraction().ExtractionConfig()
        assert cfg.model == defaults.model
        assert cfg.max_tokens == defaults.max_tokens

    def test_client_none_constructs_default_llm_client(self) -> None:
        # AC-1.4: when client is None, constructs AnthropicLLMClient()
        from unittest import mock

        fake = FakeLLMClient(_good_result())
        with mock.patch("skillgap.extraction.AnthropicLLMClient", return_value=fake) as ctor:
            _extraction().extract(_TEXT, "jd")
        ctor.assert_called()
        assert len(fake.calls) == 1

    @pytest.mark.parametrize("status", [429, 500, 502, 503])
    def test_retries_transient_errors(self, status: int) -> None:
        # AC-1.6
        client = FakeLLMClient(_extraction_error(status), _good_result())
        res = _extraction().extract(_TEXT, "jd", client=client, config=_fast_config())
        assert res.skills == _GOOD_SKILLS
        assert len(client.calls) == 2

    def test_exhausted_retries_raise(self) -> None:
        # AC-1.6: raises LLMExtractionError after max retries
        LLMExtractionError = _extraction().LLMExtractionError
        client = FakeLLMClient(_extraction_error(429))
        with pytest.raises(LLMExtractionError) as exc_info:
            _extraction().extract(_TEXT, "jd", client=client, config=_fast_config(max_retries=2))
        assert exc_info.value.attempts >= 2
        assert exc_info.value.__cause__ is not None
        assert len(client.calls) >= 2

    @pytest.mark.parametrize("status", [400, 401, 403, 404])
    def test_non_retryable_status_raises_without_retry(self, status: int) -> None:
        # AC-1.7
        client = FakeLLMClient(_extraction_error(status), _good_result())
        with pytest.raises(NonRetryableExtractionError):
            _extraction().extract(_TEXT, "jd", client=client, config=_fast_config())
        assert len(client.calls) == 1

    def test_non_retryable_schema_error_propagates(self) -> None:
        # AC-1.7: NonRetryableExtractionError from client propagates
        client = FakeLLMClient(NonRetryableExtractionError("schema validation failed"))
        with pytest.raises(NonRetryableExtractionError):
            _extraction().extract(_TEXT, "jd", client=client, config=_fast_config())
        assert len(client.calls) == 1

    def test_empty_skills_list_is_valid(self) -> None:
        # AC-1.5 edge
        client = FakeLLMClient(_empty_result())
        res = _extraction().extract(_TEXT, "jd", client=client)
        assert res.skills == ()

    def test_unicode_text_passed_through(self) -> None:
        # AC-1.1 edge
        text = "Ingénieur logiciel — Python ✓ 日本語"
        client = FakeLLMClient(_empty_result())
        _extraction().extract(text, "jd", client=client)
        assert client.calls[0]["text"] == text

    def test_short_text_makes_one_call(self) -> None:
        # AC-1.8: len(text) // 4 <= TOKEN_BUDGET -> exactly 1 call
        token_budget = _extraction().TOKEN_BUDGET
        short_text = "x" * (token_budget * 4)
        client = FakeLLMClient(_good_result())
        _extraction().extract(short_text, "jd", client=client, config=_fast_config())
        assert len(client.calls) == 1

    def test_long_text_splits_into_two_calls(self) -> None:
        # AC-1.8: len(text) // 4 > TOKEN_BUDGET -> exactly 2 calls, results merged
        token_budget = _extraction().TOKEN_BUDGET
        long_text = "x" * (token_budget * 4 + 4)
        client = FakeLLMClient(_good_result(), _good_result())
        res = _extraction().extract(long_text, "jd", client=client, config=_fast_config())
        assert len(client.calls) == 2
        assert isinstance(res, _models().ExtractionResult)


# --------------------------------------------------------------------------- verify


@_xfail_impl
class TestVerify:
    def test_good_skills_accepted_ok(self) -> None:
        # AC-2.6 happy path
        rep = _run_verify(_GOOD_SKILLS)
        assert rep.ok is True
        assert rep.errors == ()
        assert {a.canonical_name for a in rep.accepted} == {"python", "kubernetes", "docker", "aws"}

    def test_evidence_not_in_text(self) -> None:
        # AC-2.1
        bad = _sk("Python", "this phrase never appears in the posting at all")
        rep = _run_verify([bad, *_GOOD_SKILLS[1:]])
        errs = [e for e in rep.errors if e.reason == "evidence_not_in_text"]
        assert len(errs) == 1
        assert errs[0].skill_name == "Python"
        assert "python" not in {a.canonical_name for a in rep.accepted}
        assert rep.ok is False

    def test_evidence_case_insensitive(self) -> None:
        # AC-2.1
        s = _sk("Python", "5+ YEARS OF PYTHON EXPERIENCE")
        rep = _run_verify([s, *_GOOD_SKILLS[1:]])
        assert "python" in {a.canonical_name for a in rep.accepted}

    def test_evidence_fuzzy_match_above_threshold(self) -> None:
        # AC-2.1: one-character typo in a long line stays above 0.85
        s = _sk("Python", "5+ years of Pythom experience")
        rep = _run_verify([s, *_GOOD_SKILLS[1:]])
        assert "python" in {a.canonical_name for a in rep.accepted}

    def test_evidence_fuzzy_respects_threshold_parameter(self) -> None:
        # AC-2.1: threshold 1.0 disallows the fuzzy match
        s = _sk("Python", "5+ years of Pythom experience")
        rep = _run_verify([s, *_GOOD_SKILLS[1:]], grounding_threshold=1.0)
        assert any(
            e.reason == "evidence_not_in_text" and e.skill_name == "Python" for e in rep.errors
        )

    def test_skill_not_in_text(self) -> None:
        # AC-2.2: evidence is grounded but the skill name/aliases are absent
        s = _sk("Terraform", "5+ years of Python experience")
        # Use a text without any terraform mention.
        text = "\n".join(_LINES[:4])
        rep = _run_verify([s, *_GOOD_SKILLS[:3]], text=text)
        errs = [e for e in rep.errors if e.reason == "skill_not_in_text"]
        assert [e.skill_name for e in errs] == ["Terraform"]
        assert rep.ok is False

    def test_skill_in_text_via_alias(self) -> None:
        # AC-2.2: only the alias "k8s" appears in the text
        text = _TEXT + "Operate k8s clusters in production\n"
        text = text.replace("Kubernetes", "orchestration platform")
        s = _sk("Kubernetes", "Operate k8s clusters in production", category=Category.cloud_infra)
        rep = _run_verify([s, _GOOD_SKILLS[0], _GOOD_SKILLS[2], _GOOD_SKILLS[3]], text=text)
        assert not [e for e in rep.errors if e.skill_name == "Kubernetes"]
        assert "kubernetes" in {a.canonical_name for a in rep.accepted}

    def test_evidence_failure_reported_once_not_also_skill_not_in_text(self) -> None:
        # AC-2.2 ordering: skills that fail check 1 are not re-checked
        s = _sk("Frobnicator", "nothing like this exists in the text")
        rep = _run_verify([s, *_GOOD_SKILLS])
        reasons = [e.reason for e in rep.errors if e.skill_name == "Frobnicator"]
        assert reasons == ["evidence_not_in_text"]

    def test_normalization_sets_canonical_and_dictionary_category(self) -> None:
        # AC-2.3
        text = _TEXT + "Operate k8s clusters\n"
        s = _sk("K8s", "Operate k8s clusters", category=Category.soft_skill)
        rep = _run_verify([s, *_GOOD_SKILLS[:1], *_GOOD_SKILLS[2:]], text=text)
        acc = {a.canonical_name: a for a in rep.accepted}
        assert acc["kubernetes"].category == Category.cloud_infra
        assert acc["kubernetes"].skill == s

    def test_unresolved_goes_to_candidates(self) -> None:
        # AC-2.3
        text = _TEXT + "Hands-on with Frobnicator tooling\n"
        s = _sk("Frobnicator", "Hands-on with Frobnicator tooling", category=Category.framework)
        rep = _run_verify([s, *_GOOD_SKILLS], text=text)
        assert s in rep.candidates
        assert "frobnicator" not in {a.canonical_name.lower() for a in rep.accepted}
        assert not [e for e in rep.errors if e.skill_name == "Frobnicator"]
        assert rep.ok is True

    @pytest.mark.parametrize(
        ("levels", "expected"),
        [
            ((Level.preferred, Level.required), Level.required),
            ((Level.required, Level.preferred), Level.required),
            ((Level.preferred, Level.unspecified), Level.unspecified),
            ((Level.unspecified, Level.preferred), Level.unspecified),
            ((Level.unspecified, Level.required), Level.required),
            ((Level.required, Level.unspecified, Level.preferred), Level.required),
        ],
    )
    def test_dedup_strongest_level_wins(self, levels: tuple[Level, ...], expected: Level) -> None:
        # AC-2.4
        text = _TEXT + "Python3 is also used\n"
        dupes = [
            _sk("Python" if i % 2 == 0 else "python3", "5+ years of Python experience", level=lv)
            for i, lv in enumerate(levels)
        ]
        rep = _run_verify([*dupes, *_GOOD_SKILLS[1:]], text=text)
        py = [a for a in rep.accepted if a.canonical_name == "python"]
        assert len(py) == 1
        assert py[0].skill.level == expected

    def test_dedup_keeps_other_skills(self) -> None:
        # AC-2.4
        dupes = [
            _sk("Python", "5+ years of Python experience", Level.preferred),
            _sk("Python", "5+ years of Python experience", Level.required),
        ]
        rep = _run_verify([*dupes, *_GOOD_SKILLS[1:]])
        assert len(rep.accepted) == 4

    def test_too_few_skills(self) -> None:
        # AC-2.5
        rep = _run_verify(_GOOD_SKILLS[:2])
        assert any(e.reason == "too_few_skills" for e in rep.errors)
        assert rep.ok is False

    def test_empty_result_too_few(self) -> None:
        # AC-2.5 boundary
        rep = _run_verify([])
        assert rep.accepted == ()
        assert any(e.reason == "too_few_skills" for e in rep.errors)
        assert rep.ok is False

    def test_exactly_three_is_ok(self) -> None:
        # AC-2.5 / 2.6 boundary
        rep = _run_verify(_GOOD_SKILLS[:3])
        assert len(rep.accepted) == 3
        assert not any(e.reason == "too_few_skills" for e in rep.errors)
        assert rep.ok is True

    def test_dedup_counts_toward_too_few(self) -> None:
        # AC-2.4 + 2.5: dupes collapse before counting
        dupes = [
            _sk("Python", "5+ years of Python experience", Level.preferred),
            _sk("python3", "5+ years of Python experience", Level.required),
            _sk("Docker", "Strong knowledge of Kubernetes and Docker"),
        ]
        text = _TEXT + "python3 scripting\n"
        rep = _run_verify(dupes, text=text)
        assert len(rep.accepted) == 2
        assert any(e.reason == "too_few_skills" for e in rep.errors)

    @staticmethod
    def _many(n: int) -> tuple[str, list[ExtractedSkill]]:
        keys = sorted(k for k, v in _LOOKUP.items() if k == v and re.fullmatch(r"[a-z]+", k))
        assert len(keys) >= n
        keys = keys[:n]
        text = "\n".join(f"- Experience with {k} in production" for k in keys)
        skills = [_sk(k, f"Experience with {k} in production") for k in keys]
        return text, skills

    def test_forty_skills_ok(self) -> None:
        # AC-2.5 upper boundary
        text, skills = self._many(40)
        rep = _run_verify(skills, text=text)
        assert len(rep.accepted) == 40
        assert not any(e.reason == "too_many_skills" for e in rep.errors)
        assert rep.ok is True

    def test_forty_one_skills_too_many(self) -> None:
        # AC-2.5 upper boundary
        text, skills = self._many(41)
        rep = _run_verify(skills, text=text)
        assert any(e.reason == "too_many_skills" for e in rep.errors)
        assert rep.ok is False

    def test_ok_false_when_errors_even_with_enough_accepted(self) -> None:
        # AC-2.6
        bad = _sk("Frobnicator", "not found anywhere in this text")
        rep = _run_verify([*_GOOD_SKILLS, bad])
        assert len(rep.accepted) >= 3
        assert rep.errors
        assert rep.ok is False

    def test_deterministic(self) -> None:
        # purity
        a = _run_verify(_GOOD_SKILLS)
        b = _run_verify(_GOOD_SKILLS)
        assert a == b

    def test_report_type(self) -> None:
        assert isinstance(_run_verify(_GOOD_SKILLS), _models().VerifyReport)

    def test_unicode_text_and_evidence(self) -> None:
        # edge: non-ASCII
        text = _TEXT + "Expérience avec Python — très apprécié ✓\n"
        s = _sk("Python", "Expérience avec Python — très apprécié ✓")
        rep = _run_verify([s, *_GOOD_SKILLS[1:]], text=text)
        assert "python" in {a.canonical_name for a in rep.accepted}

    def test_long_text(self) -> None:
        # edge: very long input
        text = ("filler line without skills\n" * 5000) + _TEXT
        rep = _run_verify(_GOOD_SKILLS, text=text)
        assert rep.ok is True


# --------------------------------------------------------------------------- extract_verified


@_xfail_impl
class TestExtractVerified:
    def test_returns_llm_on_first_success(self) -> None:
        # AC-3.2
        client = FakeLLMClient(_good_result())
        res = _extraction().extract_verified(_TEXT, "jd", client=client, config=_fast_config())
        assert isinstance(res, _models().VerifiedExtractionResult)
        assert res.source == "llm"
        assert res.attempts == 1
        assert len(client.calls) == 1
        assert {a.canonical_name for a in res.skills} == {"python", "kubernetes", "docker", "aws"}

    def test_loads_config_by_default(self) -> None:
        # AC-3.1: no lookup/alias_config supplied
        client = FakeLLMClient(_good_result())
        res = _extraction().extract_verified(_TEXT, "jd", client=client, config=_fast_config())
        assert res.source == "llm"
        assert all(a.canonical_name in _LOOKUP.values() for a in res.skills)

    def test_explicit_lookup_and_alias_config_accepted(self) -> None:
        # AC-3.1
        client = FakeLLMClient(_good_result())
        res = _extraction().extract_verified(
            _TEXT,
            "jd",
            client=client,
            config=_fast_config(),
            lookup=_LOOKUP,
            alias_config=_ALIAS_CONFIG,
        )
        assert res.source == "llm"

    def test_retry_after_failed_verification_succeeds(self) -> None:
        # AC-3.2 / 3.3
        client = FakeLLMClient(_bad_result(), _good_result())
        res = _extraction().extract_verified(_TEXT, "jd", client=client, config=_fast_config())
        assert res.source == "llm"
        assert res.attempts == 2
        assert len(client.calls) == 2

    def test_retry_prompt_includes_errors(self) -> None:
        # AC-3.3: second call's text includes error feedback from first attempt
        client = FakeLLMClient(_bad_result(), _good_result())
        _extraction().extract_verified(_TEXT, "jd", client=client, config=_fast_config())
        retry_text = client.calls[1]["text"]
        assert "evidence_not_in_text" in retry_text
        first_text = client.calls[0]["text"]
        assert "evidence_not_in_text" not in first_text

    def test_fallback_after_all_attempts_fail(self) -> None:
        # AC-3.4
        client = FakeLLMClient(_bad_result())
        res = _extraction().extract_verified(
            _TEXT, "jd", client=client, config=_fast_config(), max_attempts=3
        )
        assert res.source == "fallback"
        assert len(client.calls) == 3
        assert res.attempts == 3
        assert res.errors
        assert any(e.reason == "evidence_not_in_text" for e in res.errors)
        assert {a.canonical_name for a in res.skills} >= {"python", "kubernetes", "docker", "aws"}

    def test_max_attempts_one(self) -> None:
        # AC-3.4 boundary
        client = FakeLLMClient(_bad_result(), _good_result())
        res = _extraction().extract_verified(
            _TEXT, "jd", client=client, config=_fast_config(), max_attempts=1
        )
        assert res.source == "fallback"
        assert len(client.calls) == 1

    @pytest.mark.parametrize("status", [400, 401, 429, 500])
    def test_api_errors_never_raise(self, status: int) -> None:
        # AC-3.5
        client = FakeLLMClient(_extraction_error(status))
        res = _extraction().extract_verified(_TEXT, "jd", client=client, config=_fast_config())
        assert res.source == "fallback"
        assert res.attempts >= 1

    def test_non_retryable_error_never_raises(self) -> None:
        # AC-3.5
        client = FakeLLMClient(NonRetryableExtractionError("schema failure"))
        res = _extraction().extract_verified(_TEXT, "jd", client=client, config=_fast_config())
        assert res.source == "fallback"

    def test_error_then_success_recovers(self) -> None:
        # AC-3.5: a failed attempt does not abort the loop
        client = FakeLLMClient(_extraction_error(400), _good_result())
        res = _extraction().extract_verified(_TEXT, "jd", client=client, config=_fast_config())
        assert res.source == "llm"
        assert res.attempts == 2

    def test_logs_each_attempt(self, caplog: pytest.LogCaptureFixture) -> None:
        # AC-3.6
        caplog.set_level(logging.DEBUG, logger="skillgap.extraction")
        client = FakeLLMClient(_bad_result(), _bad_result(), _good_result())
        _extraction().extract_verified(
            _TEXT, "jd", client=client, config=_fast_config(), max_attempts=3
        )
        records = [r for r in caplog.records if r.name == "skillgap.extraction"]
        assert len(records) >= 3
        messages = " ".join(r.getMessage() for r in records)
        for n in ("1", "2", "3"):
            assert n in messages

    def test_resume_kind(self) -> None:
        client = FakeLLMClient(_good_result())
        res = _extraction().extract_verified(_TEXT, "resume", client=client, config=_fast_config())
        assert res.source == "llm"
        assert client.calls[0]["kind"] == "resume"

    def test_recorded_fixture_posting_never_raises(self) -> None:
        # Exit criterion: never raises for any fixture. Garbage LLM, real posting text.
        paths = sorted((_FIXTURES / "postings").rglob("*.txt"))
        assert len(paths) >= 30
        for p in paths:
            client = FakeLLMClient(_empty_result())
            res = _extraction().extract_verified(
                p.read_text(), "jd", client=client, config=_fast_config(), max_attempts=2
            )
            assert res.source in ("llm", "fallback")

    def test_recorded_fixture_resume_never_raises(self) -> None:
        text = (_FIXTURES / "resumes" / "fictional-senior-swe.txt").read_text()
        client = FakeLLMClient(_extraction_error(500))
        res = _extraction().extract_verified(text, "resume", client=client, config=_fast_config())
        assert res.source == "fallback"
        assert len(res.skills) >= 3

    def test_empty_text_never_raises(self) -> None:
        client = FakeLLMClient(_empty_result())
        res = _extraction().extract_verified("", "jd", client=client, config=_fast_config())
        assert res.source == "fallback"
        assert res.skills == ()


# --------------------------------------------------------------------------- extract_dictionary


def _dict(text: str, kind: str = "jd") -> list[ExtractedSkill]:
    result: list[ExtractedSkill] = _extraction().extract_dictionary(
        text, kind, _LOOKUP, _ALIAS_CONFIG
    )
    return result


@_xfail_impl
class TestExtractDictionary:
    def test_finds_known_skills(self) -> None:
        # AC-4.1
        names = {s.name for s in _dict(_TEXT)}
        assert {"python", "kubernetes", "docker", "aws", "terraform"} <= names

    def test_case_insensitive(self) -> None:
        # AC-4.1
        names = {s.name for s in _dict("We use PYTHON and DoCkEr daily")}
        assert {"python", "docker"} <= names

    def test_alias_resolves_to_canonical(self) -> None:
        # AC-4.1 / 4.2
        out = _dict("Operate K8s clusters and write Golang services, Amazon Web Services")
        names = {s.name for s in out}
        assert "kubernetes" in names
        assert "aws" in names
        assert "k8s" not in names

    def test_word_boundary_respected(self) -> None:
        # AC-4.1: "java" must not match inside "javascript"; "pythonic" is not python
        out = _dict("Strong javascript skills and a pythonic style")
        names = {s.name for s in out}
        assert "javascript" in names
        assert "java" not in names
        assert "python" not in names

    def test_skill_fields(self) -> None:
        # AC-4.2
        out = _dict("intro\nExperience with Docker in production\noutro")
        docker = next(s for s in out if s.name == "docker")
        assert docker.category == _ALIAS_CONFIG.skills["docker"].category
        assert docker.level == Level.unspecified
        assert docker.evidence == "Experience with Docker in production"

    def test_evidence_is_single_line_from_text(self) -> None:
        # AC-4.2
        for s in _dict(_TEXT):
            assert "\n" not in s.evidence
            assert s.evidence.strip() in _TEXT

    def test_evidence_grounded(self) -> None:
        for s in _dict(_TEXT):
            assert _is_grounded(s.evidence, _TEXT, 0.85)

    def test_first_match_wins_dedup(self) -> None:
        # AC-4.3
        text = "First: Python is great\nSecond: python3 is used\nThird: PYTHON again"
        out = [s for s in _dict(text) if s.name == "python"]
        assert len(out) == 1
        assert out[0].evidence == "First: Python is great"

    def test_alias_and_canonical_dedup_to_one(self) -> None:
        # AC-4.3
        out = _dict("Kubernetes cluster work\nlots of k8s")
        assert [s.name for s in out].count("kubernetes") == 1

    def test_ambiguous_skipped_in_prose(self) -> None:
        # AC-4.4
        assert _ALIAS_CONFIG.skills["go"].ambiguous
        out = _dict("We want you to go above and beyond and go home happy.")
        assert "go" not in {s.name for s in out}

    def test_ambiguous_kept_in_comma_list(self) -> None:
        # AC-4.4
        out = _dict("Languages: Python, Go, Rust")
        names = {s.name for s in out}
        assert {"python", "go"} <= names

    def test_ambiguous_kept_in_bullet_list(self) -> None:
        # AC-4.4
        out = _dict("Requirements:\n- Go\n- Python\n- Docker")
        assert "go" in {s.name for s in out}

    def test_empty_text(self) -> None:
        # AC-4.5
        assert _dict("") == []

    def test_no_skills_in_text(self) -> None:
        # AC-4.5
        assert _dict("The quick brown fox jumps over the lazy dog.") == []

    def test_returns_list_of_extracted_skills(self) -> None:
        out = _dict(_TEXT)
        assert isinstance(out, list)
        assert all(isinstance(s, ExtractedSkill) for s in out)

    def test_kind_resume_works(self) -> None:
        text = (_FIXTURES / "resumes" / "fictional-senior-swe.txt").read_text()
        out = _dict(text, "resume")
        assert len(out) >= 3
        assert len({s.name for s in out}) == len(out)

    def test_unicode_text(self) -> None:
        out = _dict("Ingénieur — expérience : Python ✓, Docker 日本語")
        assert {"python", "docker"} <= {s.name for s in out}

    def test_long_text_deterministic(self) -> None:
        text = ("lorem ipsum dolor sit amet\n" * 3000) + _TEXT
        assert _dict(text) == _dict(text)
        assert "python" in {s.name for s in _dict(text)}


# --------------------------------------------------------------------------- DI


@_xfail_impl
class TestDI:
    def test_extract_accepts_client(self) -> None:
        # AC-6.1
        import inspect

        sig = inspect.signature(_extraction().extract)
        assert "client" in sig.parameters
        assert sig.parameters["client"].kind is inspect.Parameter.KEYWORD_ONLY
        assert sig.parameters["client"].default is None

    def test_extract_verified_accepts_client(self) -> None:
        # AC-6.1
        import inspect

        sig = inspect.signature(_extraction().extract_verified)
        for p in ("client", "config", "lookup", "alias_config", "max_attempts"):
            assert p in sig.parameters
        assert sig.parameters["max_attempts"].default == 3

    def test_injected_client_is_the_one_used(self) -> None:
        # AC-6.2
        client = FakeLLMClient(_good_result())
        _extraction().extract(_TEXT, "jd", client=client)
        assert len(client.calls) == 1

    def test_extract_verified_uses_injected_client(self) -> None:
        # AC-6.2
        client = FakeLLMClient(_good_result())
        _extraction().extract_verified(_TEXT, "jd", client=client, config=_fast_config())
        assert len(client.calls) == 1

    def test_no_monkeypatch_setattr_in_phase_4_tests(self) -> None:
        # AC-6.2 -- also runs without Phase 4 code, so not an xfail target.
        src = Path(__file__).read_text()
        assert not re.search(r"monkeypatch\s*\.\s*setattr\(", src)
        _extraction()  # require the implementation to exist

    def test_verify_signature(self) -> None:
        import inspect

        sig = inspect.signature(_verification().verify)
        assert list(sig.parameters)[:4] == ["text", "result", "lookup", "config"]
        assert sig.parameters["grounding_threshold"].default == 0.85


class TestPhase3Unchanged:
    def test_phase_3_still_uses_monkeypatch_of_call_llm(self) -> None:
        # AC-6.3
        p3 = Path(__file__).resolve().parents[1] / "phase_3"
        conftest = (p3.parent / "conftest.py").read_text()
        assert "skillgap.extractor._call_llm" in conftest
        assert any(p3.glob("test_*.py"))


# --------------------------------------------------------------------------- evals


class TestEvals:
    def test_golden_files_present_and_reviewed(self) -> None:
        # AC-7.1 precondition
        files = sorted((_REPO_ROOT / "evals" / "golden").glob("*.yaml"))
        assert len(files) == 15
        for f in files:
            data = yaml.safe_load(f.read_text())
            assert data["reviewed"] is True, f.name
            assert data["kind"] in ("jd", "resume")
            assert (_FIXTURES / data["fixture"]).is_file(), f.name
            assert data["expected"], f.name

    def test_golden_skills_are_canonical(self) -> None:
        for f in sorted((_REPO_ROOT / "evals" / "golden").glob("*.yaml")):
            data = yaml.safe_load(f.read_text())
            for item in data["expected"]:
                assert item["skill"] in _ALIAS_CONFIG.skills, (f.name, item["skill"])

    def test_make_eval_invokes_run_py(self) -> None:
        # AC-7.7
        makefile = (_REPO_ROOT / "Makefile").read_text()
        m = re.search(r"^eval:\s*\n((?:\t.*\n?)+)", makefile, re.M)
        assert m is not None
        assert "evals/run.py" in m.group(1)

    @_xfail_impl
    def test_run_py_reports_all_three_paths_and_metrics(self) -> None:
        # AC-7.2 / 7.3: --format json outputs structured results
        env = {**os.environ, "EVAL_MIN_F1": "0.0"}
        proc = subprocess.run(
            [sys.executable, str(_REPO_ROOT / "evals" / "run.py"), "--format", "json"],
            cwd=_REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert proc.returncode == 0
        data = json_mod.loads(proc.stdout)
        for path in ("llm", "dictionary", "combined"):
            assert path in data
            for metric in ("precision", "recall", "f1"):
                assert metric in data[path]
                assert isinstance(data[path][metric], float)

    @_xfail_impl
    def test_run_py_exits_1_below_min_f1(self) -> None:
        # AC-7.6: impossible threshold must fail
        env = {**os.environ, "EVAL_MIN_F1": "1.01"}
        proc = subprocess.run(
            [sys.executable, str(_REPO_ROOT / "evals" / "run.py"), "--format", "json"],
            cwd=_REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert proc.returncode == 1
        data = json_mod.loads(proc.stdout)
        assert "combined" in data

    @pytest.mark.skip(reason="AC-7.4 deferred: needs --baseline flag + recorded responses")
    def test_baseline_written_on_first_run(self) -> None:
        pass

    @pytest.mark.skip(reason="AC-7.5 deferred: needs --baseline flag + recorded responses")
    def test_regression_detected_on_second_run(self) -> None:
        pass


# --------------------------------------------------------------------------- hypothesis

_POOL_NAMES = [
    "Python",
    "python3",
    "Kubernetes",
    "K8s",
    "Docker",
    "AWS",
    "Terraform",
    "Java",
    "Frobnicator",
]
_EVIDENCE = [*_LINES, "completely absent phrase zq", "5+ years of Pythom experience"]


@st.composite
def _skills(draw: st.DrawFn) -> list[ExtractedSkill]:
    n = draw(st.integers(min_value=0, max_value=10))
    out = []
    for _ in range(n):
        out.append(
            ExtractedSkill(
                name=draw(st.sampled_from(_POOL_NAMES)),
                category=draw(st.sampled_from(list(Category))),
                level=draw(st.sampled_from(list(Level))),
                evidence=draw(st.sampled_from(_EVIDENCE)),
            )
        )
    return out


_HSETTINGS = settings(
    max_examples=60, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)


@_xfail_impl
class TestHypothesis:
    @_HSETTINGS
    @given(skills=_skills())
    def test_p1_never_accepts_ungrounded_evidence(self, skills: list[ExtractedSkill]) -> None:
        rep = _run_verify(skills)
        for a in rep.accepted:
            assert _is_grounded(a.skill.evidence, _TEXT, 0.85)

    @_HSETTINGS
    @given(skills=_skills())
    def test_p2_verify_deterministic(self, skills: list[ExtractedSkill]) -> None:
        assert _run_verify(skills) == _run_verify(skills)

    @_HSETTINGS
    @given(skills=_skills())
    def test_p3_accepted_subset_of_input(self, skills: list[ExtractedSkill]) -> None:
        rep = _run_verify(skills)
        assert {a.skill for a in rep.accepted} <= set(skills)

    @_HSETTINGS
    @given(skills=_skills())
    def test_p4_no_duplicate_canonical_names(self, skills: list[ExtractedSkill]) -> None:
        rep = _run_verify(skills)
        names = [a.canonical_name for a in rep.accepted]
        assert len(names) == len(set(names))

    @_HSETTINGS
    @given(skills=_skills())
    def test_p5_every_input_accounted_for(self, skills: list[ExtractedSkill]) -> None:
        rep = _run_verify(skills)
        accepted_skills = {a.skill for a in rep.accepted}
        accepted_canon = {a.canonical_name for a in rep.accepted}
        error_names = {e.skill_name for e in rep.errors}
        for s in skills:
            if s in accepted_skills or s in rep.candidates or s.name in error_names:
                continue
            # Dropped as a lower-level duplicate of an accepted canonical name.
            resolved = normalize(s.name, _LOOKUP, _ALIAS_CONFIG)
            assert resolved is not None
            assert resolved.canonical_name in accepted_canon

    @_HSETTINGS
    @given(skills=_skills())
    def test_p6_ok_flag_consistent(self, skills: list[ExtractedSkill]) -> None:
        rep = _run_verify(skills)
        assert rep.ok == (len(rep.errors) == 0 and 3 <= len(rep.accepted) <= 40)

    @_HSETTINGS
    @given(
        outcomes=st.lists(
            st.sampled_from(["good", "bad", "empty", "invalid", "429", "400", "500"]),
            min_size=1,
            max_size=4,
        ),
        kind=st.sampled_from(["jd", "resume"]),
        text=st.sampled_from([_TEXT, "", "no skills here", "Python, Go, Rust"]),
    )
    def test_p7_extract_verified_never_raises(
        self, outcomes: list[str], kind: str, text: str
    ) -> None:
        makers: dict[str, Callable[[], Any]] = {
            "good": _good_result,
            "bad": _bad_result,
            "empty": _empty_result,
            "invalid": lambda: NonRetryableExtractionError("invalid schema"),
            "429": lambda: _extraction_error(429),
            "400": lambda: _extraction_error(400),
            "500": lambda: _extraction_error(500),
        }
        client = FakeLLMClient(*[makers[o]() for o in outcomes])
        res = _extraction().extract_verified(
            text, kind, client=client, config=_fast_config(max_retries=1), max_attempts=3
        )
        assert isinstance(res, _models().VerifiedExtractionResult)
        assert res.source in ("llm", "fallback")

    @_HSETTINGS
    @given(
        outcomes=st.lists(st.sampled_from(["bad", "empty", "429", "400"]), min_size=1, max_size=3),
        text=st.sampled_from([_TEXT, "Python, Go, Rust, Docker", "nothing"]),
    )
    def test_p8_fallback_skills_in_lookup(self, outcomes: list[str], text: str) -> None:
        makers: dict[str, Callable[[], Any]] = {
            "bad": _bad_result,
            "empty": _empty_result,
            "429": lambda: _extraction_error(429),
            "400": lambda: _extraction_error(400),
        }
        client = FakeLLMClient(*[makers[o]() for o in outcomes])
        res = _extraction().extract_verified(
            text, "jd", client=client, config=_fast_config(max_retries=1), max_attempts=2
        )
        assert res.source == "fallback"
        for a in res.skills:
            assert a.canonical_name in _LOOKUP.values()

    @_HSETTINGS
    @given(
        parts=st.lists(
            st.sampled_from(
                [
                    *list(_LOOKUP)[:60],
                    "lorem",
                    "ipsum",
                    "the",
                    "and",
                    "Python",
                    "K8S",
                    "\n",
                    ", ",
                    "- ",
                ]
            ),
            max_size=25,
        )
    )
    def test_p9_dictionary_only_returns_present_skills(self, parts: list[str]) -> None:
        text = " ".join(parts)
        lowered = text.lower()
        for s in _dict(text):
            candidates = {s.name, *_ALIAS_CONFIG.skills[s.name].aliases}
            assert any(c in lowered for c in candidates)

    @_HSETTINGS
    @given(
        parts=st.lists(
            st.sampled_from([*list(_LOOKUP)[:60], "lorem", "ipsum", "\n", ", ", "- "]), max_size=25
        )
    )
    def test_p10_dictionary_deterministic_and_idempotent(self, parts: list[str]) -> None:
        text = " ".join(parts)
        first = _dict(text)
        assert first == _dict(text)
        # Idempotent: re-scanning the evidence lines yields the same canonical set.
        rejoined = "\n".join(s.evidence for s in first)
        assert {s.name for s in _dict(rejoined)} >= {s.name for s in first} or not first
        assert _dict(rejoined) == _dict(rejoined)
