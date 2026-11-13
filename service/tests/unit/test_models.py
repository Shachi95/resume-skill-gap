"""Tests for Pydantic models."""

from __future__ import annotations

from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from skillgap.models import (
    Category,
    ExtractedSkill,
    Gap,
    Level,
    Posting,
    RankedGap,
    Resume,
    Role,
    Skill,
)


class TestPosting:
    def test_valid(self) -> None:
        p = Posting(id="p1", title="Sr SWE", text="Requirements: Python")
        assert p.id == "p1"
        assert p.role is None
        assert p.url is None
        assert p.posted_date is None

    def test_with_all_fields(self) -> None:
        p = Posting(
            id="p2",
            role=Role.software_engineer,
            title="Backend Eng",
            url="https://example.com/job",
            posted_date=date(2026, 1, 15),
            text="Some text",
        )
        assert p.role == Role.software_engineer
        assert p.posted_date == date(2026, 1, 15)

    def test_empty_title_rejected(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            Posting(id="p1", title="", text="Some text")

    def test_blank_title_rejected(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            Posting(id="p1", title="   ", text="Some text")

    def test_empty_text_rejected(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            Posting(id="p1", title="SWE", text="")

    def test_frozen(self) -> None:
        p = Posting(id="p1", title="SWE", text="text")
        with pytest.raises(ValidationError):
            p.title = "new"  # type: ignore[misc]


class TestExtractedSkill:
    def test_valid(self) -> None:
        s = ExtractedSkill(
            name="python",
            category=Category.language,
            level=Level.required,
            evidence="5+ years Python",
        )
        assert s.name == "python"

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            ExtractedSkill(
                name="", category=Category.language, level=Level.required, evidence="text"
            )

    def test_empty_evidence_rejected(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            ExtractedSkill(
                name="python", category=Category.language, level=Level.required, evidence=""
            )

    def test_invalid_category(self) -> None:
        with pytest.raises(ValueError):
            ExtractedSkill(
                name="python",
                category="bogus",
                level=Level.required,
                evidence="text",  # type: ignore[arg-type]
            )

    def test_invalid_level(self) -> None:
        with pytest.raises(ValueError):
            ExtractedSkill(
                name="python",
                category=Category.language,
                level="bogus",
                evidence="text",  # type: ignore[arg-type]
            )


class TestGap:
    def test_valid(self) -> None:
        g = Gap(
            skill="kubernetes",
            category=Category.cloud_infra,
            score=3.5,
            posting_count=4,
            required_count=2,
            preferred_count=1,
        )
        assert g.score == 3.5
        assert g.posting_count == 4

    def test_negative_score_rejected(self) -> None:
        with pytest.raises(ValueError, match="score"):
            Gap(skill="k8s", category=Category.cloud_infra, score=-1.0, posting_count=1)

    def test_zero_posting_count_rejected(self) -> None:
        with pytest.raises(ValueError, match="posting_count"):
            Gap(skill="k8s", category=Category.cloud_infra, score=1.0, posting_count=0)

    def test_negative_required_count_rejected(self) -> None:
        with pytest.raises(ValueError, match="count"):
            Gap(
                skill="k8s",
                category=Category.cloud_infra,
                score=1.0,
                posting_count=1,
                required_count=-1,
            )

    def test_counts_exceed_posting_count(self) -> None:
        with pytest.raises(ValueError, match=r"required_count.*preferred_count.*posting_count"):
            Gap(
                skill="k8s",
                category=Category.cloud_infra,
                score=1.0,
                posting_count=3,
                required_count=2,
                preferred_count=2,
            )

    def test_counts_equal_posting_count(self) -> None:
        g = Gap(
            skill="k8s",
            category=Category.cloud_infra,
            score=2.5,
            posting_count=3,
            required_count=2,
            preferred_count=1,
        )
        assert g.required_count + g.preferred_count == g.posting_count

    def test_empty_skill_rejected(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            Gap(skill="", category=Category.cloud_infra, score=1.0, posting_count=1)


class TestSkill:
    def test_valid(self) -> None:
        s = Skill(canonical_name="python", category=Category.language)
        assert s.canonical_name == "python"
        assert s.ambiguous is False

    def test_ambiguous(self) -> None:
        s = Skill(canonical_name="go", category=Category.language, ambiguous=True)
        assert s.ambiguous is True

    def test_empty_canonical_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            Skill(canonical_name="", category=Category.language)

    def test_blank_canonical_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            Skill(canonical_name="   ", category=Category.language)

    def test_frozen(self) -> None:
        s = Skill(canonical_name="python", category=Category.language)
        with pytest.raises(ValidationError):
            s.canonical_name = "java"  # type: ignore[misc]


class TestResume:
    def test_valid(self) -> None:
        r = Resume(id="r1", text="Experienced engineer with Python expertise.")
        assert r.id == "r1"
        assert r.skills == ()

    def test_with_skills(self) -> None:
        skill = ExtractedSkill(
            name="python",
            category=Category.language,
            level=Level.required,
            evidence="5+ years Python",
        )
        r = Resume(id="r1", text="Some resume text", skills=(skill,))
        assert len(r.skills) == 1

    def test_empty_text_rejected(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            Resume(id="r1", text="")

    def test_frozen(self) -> None:
        r = Resume(id="r1", text="Some text")
        with pytest.raises(ValidationError):
            r.text = "new"  # type: ignore[misc]


class TestRankedGap:
    def test_valid(self) -> None:
        g = Gap(skill="k8s", category=Category.cloud_infra, score=2.0, posting_count=2)
        rg = RankedGap(rank=1, gap=g)
        assert rg.rank == 1
        assert rg.gap.skill == "k8s"

    def test_zero_rank_rejected(self) -> None:
        g = Gap(skill="k8s", category=Category.cloud_infra, score=1.0, posting_count=1)
        with pytest.raises(ValueError, match="rank"):
            RankedGap(rank=0, gap=g)

    def test_negative_rank_rejected(self) -> None:
        g = Gap(skill="k8s", category=Category.cloud_infra, score=1.0, posting_count=1)
        with pytest.raises(ValueError, match="rank"):
            RankedGap(rank=-1, gap=g)

    def test_frozen(self) -> None:
        g = Gap(skill="k8s", category=Category.cloud_infra, score=1.0, posting_count=1)
        rg = RankedGap(rank=1, gap=g)
        with pytest.raises(ValidationError):
            rg.rank = 2  # type: ignore[misc]


_categories = st.sampled_from(list(Category))
_gap_strategy = (
    st.builds(
        Gap,
        skill=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        category=_categories,
        score=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        posting_count=st.integers(min_value=1, max_value=30),
        required_count=st.just(0),
        preferred_count=st.just(0),
    )
    .flatmap(
        lambda g: st.builds(
            Gap,
            skill=st.just(g.skill),
            category=st.just(g.category),
            score=st.just(g.score),
            posting_count=st.just(g.posting_count),
            required_count=st.integers(min_value=0, max_value=g.posting_count),
            preferred_count=st.just(0),
        )
    )
    .flatmap(
        lambda g: st.builds(
            Gap,
            skill=st.just(g.skill),
            category=st.just(g.category),
            score=st.just(g.score),
            posting_count=st.just(g.posting_count),
            required_count=st.just(g.required_count),
            preferred_count=st.integers(min_value=0, max_value=g.posting_count - g.required_count),
        )
    )
)


@given(gap=_gap_strategy)
def test_gap_roundtrip(gap: Gap) -> None:
    """Any valid Gap round-trips through model_dump / model_validate."""
    dumped = gap.model_dump()
    restored = Gap.model_validate(dumped)
    assert restored == gap


_skill_strategy = st.builds(
    Skill,
    canonical_name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
    category=_categories,
    ambiguous=st.booleans(),
)


@given(skill=_skill_strategy)
def test_skill_roundtrip(skill: Skill) -> None:
    dumped = skill.model_dump()
    restored = Skill.model_validate(dumped)
    assert restored == skill


_levels = st.sampled_from(list(Level))
_extracted_skill_strategy = st.builds(
    ExtractedSkill,
    name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
    category=_categories,
    level=_levels,
    evidence=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
)

_resume_strategy = st.builds(
    Resume,
    id=st.text(min_size=1, max_size=20),
    text=st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
    skills=st.lists(_extracted_skill_strategy, min_size=0, max_size=3).map(tuple),
)


@given(resume=_resume_strategy)
def test_resume_roundtrip(resume: Resume) -> None:
    dumped = resume.model_dump()
    restored = Resume.model_validate(dumped)
    assert restored == resume


_ranked_gap_strategy = _gap_strategy.flatmap(
    lambda g: st.builds(
        RankedGap,
        rank=st.integers(min_value=1, max_value=1000),
        gap=st.just(g),
    )
)


@given(rg=_ranked_gap_strategy)
def test_ranked_gap_roundtrip(rg: RankedGap) -> None:
    dumped = rg.model_dump()
    restored = RankedGap.model_validate(dumped)
    assert restored == rg
