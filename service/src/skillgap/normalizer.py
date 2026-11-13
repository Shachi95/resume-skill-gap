"""Resolve raw skill names to canonical entries via aliases.yaml lookup."""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence

from skillgap.config import AliasConfig
from skillgap.models import Skill

logger = logging.getLogger(__name__)

_VERSION_SUFFIX = re.compile(r"\s+\d[\d.x+]*$")


def build_lookup(config: AliasConfig) -> dict[str, str]:
    """Build a lowercased alias-to-canonical-name mapping.

    Includes both canonical names and their aliases as keys.
    """
    lookup: dict[str, str] = {}
    for canonical, entry in config.skills.items():
        lookup[canonical] = canonical
        for alias in entry.aliases:
            lookup[alias] = canonical
    return lookup


def normalize(
    raw_name: str,
    lookup: dict[str, str],
    config: AliasConfig,
) -> Skill | None:
    """Resolve a raw skill name to a canonical Skill, or None if unknown."""
    key = raw_name.strip().lower()
    canonical = lookup.get(key)
    if canonical is None:
        stripped = _VERSION_SUFFIX.sub("", key)
        if stripped != key:
            canonical = lookup.get(stripped)
    if canonical is None:
        logger.debug("unmatched skill term: %r", raw_name)
        return None
    entry = config.skills[canonical]
    return Skill(
        canonical_name=canonical,
        category=entry.category,
        ambiguous=entry.ambiguous,
    )


def normalize_batch(
    raw_names: Sequence[str],
    lookup: dict[str, str],
    config: AliasConfig,
) -> list[Skill | None]:
    """Normalize a sequence of raw skill names."""
    return [normalize(name, lookup, config) for name in raw_names]


def get_parents(canonical_name: str, config: AliasConfig) -> list[Skill]:
    """Return the parent chain for a skill (nearest parent first)."""
    parents: list[Skill] = []
    current = canonical_name
    while True:
        entry = config.skills.get(current)
        if entry is None or entry.parent is None:
            break
        current = entry.parent
        parent_entry = config.skills[current]
        parents.append(
            Skill(
                canonical_name=current,
                category=parent_entry.category,
                ambiguous=parent_entry.ambiguous,
            )
        )
    return parents
