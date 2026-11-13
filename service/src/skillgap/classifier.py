"""Assign or verify categories for skills and classify job titles into roles."""

from __future__ import annotations

import re

from skillgap.config import AliasConfig, RolesConfig
from skillgap.models import Category, Role


def classify(canonical_name: str, config: AliasConfig) -> Category | None:
    """Return the category for a canonical skill name, or None if not in dictionary."""
    entry = config.skills.get(canonical_name)
    if entry is None:
        return None
    return entry.category


def is_ambiguous(canonical_name: str, config: AliasConfig) -> bool:
    """Return True if the skill is marked ambiguous in the dictionary."""
    entry = config.skills.get(canonical_name)
    if entry is None:
        return False
    return entry.ambiguous


def validate_category(
    canonical_name: str,
    claimed: Category,
    config: AliasConfig,
) -> bool:
    """Check whether a claimed category matches the dictionary's category.

    Returns True if they match, or if the skill is not in the dictionary.
    """
    entry = config.skills.get(canonical_name)
    if entry is None:
        return True
    return entry.category == claimed


def classify_role(title: str, config: RolesConfig) -> Role:
    """Classify a job title into a Role using roles.yaml patterns.

    Checks exclude patterns first, then include patterns in precedence order.
    """
    lower = title.strip().lower()
    for pattern in config.exclude:
        if re.search(pattern, lower, re.IGNORECASE):
            return Role.excluded
    for role in config.precedence:
        for pattern in config.roles[role].include:
            if re.search(pattern, lower, re.IGNORECASE):
                return role
    return Role.excluded
