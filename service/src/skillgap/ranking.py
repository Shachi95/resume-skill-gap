"""Score and rank skill gaps."""

from __future__ import annotations

from collections.abc import Sequence

from skillgap.models import Gap, Level, RankedGap

WEIGHTS: dict[Level, float] = {
    Level.required: 1.0,
    Level.unspecified: 0.75,
    Level.preferred: 0.5,
}


def score_gap(levels: Sequence[Level]) -> float:
    """Compute the score for a single skill across multiple posting mentions."""
    return sum(WEIGHTS[level] for level in levels)


def rank_gaps(gaps: Sequence[Gap]) -> list[RankedGap]:
    """Sort gaps by score descending, assign 1-based ranks.

    Tiebreak: posting_count descending, then skill name ascending,
    then category ascending (total order over all Gap fields).
    """
    sorted_gaps = sorted(
        gaps,
        key=lambda g: (-g.score, -g.posting_count, g.skill, g.category),
    )
    return [RankedGap(rank=i + 1, gap=g) for i, g in enumerate(sorted_gaps)]
