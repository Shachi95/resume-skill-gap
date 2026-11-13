"""Unit tests for the grounding validator."""

from __future__ import annotations

from skillgap.grounding import validate_grounding
from skillgap.models import Category, ExtractedSkill, Level


def _skill(name: str, evidence: str) -> ExtractedSkill:
    return ExtractedSkill(
        name=name,
        category=Category.language,
        level=Level.required,
        evidence=evidence,
    )


_SOURCE = (
    "Requirements:\n"
    "- 5+ years of Python experience\n"
    "- Strong knowledge of Kubernetes and Docker\n"
    "- Experience with AWS services"
)


class TestValidateGrounding:
    def test_exact_match_passes(self) -> None:
        s = _skill("Python", "5+ years of Python experience")
        assert len(validate_grounding([s], _SOURCE)) == 1

    def test_case_insensitive_match_passes(self) -> None:
        s = _skill("Python", "5+ years of python experience")
        assert len(validate_grounding([s], _SOURCE)) == 1

    def test_fabricated_evidence_rejected(self) -> None:
        s = _skill("Rust", "10 years of Rust systems programming")
        assert len(validate_grounding([s], _SOURCE)) == 0

    def test_empty_result_on_all_fabricated(self) -> None:
        skills = [
            _skill("Rust", "deep Rust expertise"),
            _skill("Haskell", "functional programming in Haskell"),
        ]
        assert validate_grounding(skills, _SOURCE) == []

    def test_mixed_valid_and_fabricated(self) -> None:
        skills = [
            _skill("Python", "5+ years of Python experience"),
            _skill("AWS", "Experience with AWS services"),
            _skill("Rust", "10 years of Rust"),
        ]
        result = validate_grounding(skills, _SOURCE)
        assert len(result) == 2
        assert {s.name for s in result} == {"Python", "AWS"}

    def test_fuzzy_near_match_passes(self) -> None:
        s = _skill("Kubernetes", "Strong knowledge of Kubernetes & Docker")
        result = validate_grounding([s], _SOURCE, threshold=0.80)
        assert len(result) == 1
