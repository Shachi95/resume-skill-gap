"""Tests for gap scoring and ranking."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from skillgap.models import Category, Gap, Level
from skillgap.ranking import WEIGHTS, rank_gaps, score_gap


class TestScoreGap:
    def test_all_required(self) -> None:
        assert score_gap([Level.required, Level.required]) == 2.0

    def test_all_preferred(self) -> None:
        assert score_gap([Level.preferred, Level.preferred]) == 1.0

    def test_mixed(self) -> None:
        assert score_gap([Level.required, Level.preferred, Level.unspecified]) == 2.25

    def test_empty(self) -> None:
        assert score_gap([]) == 0.0

    def test_single_unspecified(self) -> None:
        assert score_gap([Level.unspecified]) == 0.75


class TestRankGaps:
    def test_sorted_by_score(self) -> None:
        g1 = Gap(skill="a", category=Category.language, score=1.0, posting_count=1)
        g2 = Gap(skill="b", category=Category.language, score=3.0, posting_count=1)
        g3 = Gap(skill="c", category=Category.language, score=2.0, posting_count=1)
        ranked = rank_gaps([g1, g2, g3])
        assert len(ranked) == 3
        assert ranked[0].gap.score == 3.0
        assert ranked[1].gap.score == 2.0
        assert ranked[2].gap.score == 1.0

    def test_ranks_are_sequential(self) -> None:
        g1 = Gap(skill="a", category=Category.language, score=1.0, posting_count=1)
        g2 = Gap(skill="b", category=Category.language, score=2.0, posting_count=1)
        ranked = rank_gaps([g1, g2])
        assert [rg.rank for rg in ranked] == [1, 2]

    def test_tiebreak_by_posting_count(self) -> None:
        g1 = Gap(skill="a", category=Category.language, score=2.0, posting_count=3)
        g2 = Gap(skill="b", category=Category.language, score=2.0, posting_count=5)
        ranked = rank_gaps([g1, g2])
        assert ranked[0].gap.skill == "b"
        assert ranked[1].gap.skill == "a"

    def test_tiebreak_by_name(self) -> None:
        g1 = Gap(skill="beta", category=Category.language, score=2.0, posting_count=1)
        g2 = Gap(skill="alpha", category=Category.language, score=2.0, posting_count=1)
        ranked = rank_gaps([g1, g2])
        assert ranked[0].gap.skill == "alpha"
        assert ranked[1].gap.skill == "beta"

    def test_empty(self) -> None:
        assert rank_gaps([]) == []

    def test_single(self) -> None:
        g = Gap(skill="x", category=Category.language, score=1.0, posting_count=1)
        ranked = rank_gaps([g])
        assert len(ranked) == 1
        assert ranked[0].rank == 1
        assert ranked[0].gap == g


_categories = st.sampled_from(list(Category))
_gap_strategy = st.builds(
    Gap,
    skill=st.text(min_size=1, max_size=20).filter(lambda s: s.strip()),
    category=_categories,
    score=st.floats(min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    posting_count=st.integers(min_value=1, max_value=10),
    required_count=st.just(0),
    preferred_count=st.just(0),
)


@given(gaps=st.lists(_gap_strategy, min_size=0, max_size=10))
def test_rank_gaps_sorted_and_sequential(gaps: list[Gap]) -> None:
    ranked = rank_gaps(gaps)
    assert len(ranked) == len(gaps)
    for i, rg in enumerate(ranked):
        assert rg.rank == i + 1
    scores = [rg.gap.score for rg in ranked]
    assert scores == sorted(scores, reverse=True)


@given(gaps=st.lists(_gap_strategy, min_size=1, max_size=10), data=st.data())
def test_rank_gaps_shuffle_invariant(gaps: list[Gap], data: st.DataObject) -> None:
    shuffled = data.draw(st.permutations(gaps))
    assert rank_gaps(gaps) == rank_gaps(shuffled)


class TestWeights:
    def test_weights_complete(self) -> None:
        assert set(WEIGHTS.keys()) == set(Level)

    def test_required_highest(self) -> None:
        assert WEIGHTS[Level.required] > WEIGHTS[Level.preferred]
        assert WEIGHTS[Level.required] > WEIGHTS[Level.unspecified]
