"""Load and validate aliases.yaml and roles.yaml."""

from __future__ import annotations

import functools
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_validator, model_validator

from skillgap.models import Category, Role

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "tech"

_VALID_ROLES = frozenset({Role.software_engineer, Role.ai_engineer, Role.fde})


class SkillEntry(BaseModel, frozen=True):
    category: Category
    aliases: list[str] = []
    parent: str | None = None
    ambiguous: bool = False

    @field_validator("aliases", mode="before")
    @classmethod
    def _lowercase_aliases(cls, v: list[str]) -> list[str]:
        return [a.strip().lower() for a in v]


class AliasConfig(BaseModel, frozen=True):
    skills: dict[str, SkillEntry]

    @field_validator("skills", mode="before")
    @classmethod
    def _lowercase_keys(cls, v: dict[str, Any]) -> dict[str, Any]:
        return {k.strip().lower(): val for k, val in v.items()}

    @model_validator(mode="after")
    def _check_aliases(self) -> AliasConfig:
        seen: dict[str, str] = {}
        canonical_names = set(self.skills.keys())

        for skill_name, entry in self.skills.items():
            for alias in entry.aliases:
                if alias in canonical_names and alias != skill_name:
                    raise ValueError(
                        f"alias '{alias}' of '{skill_name}' conflicts with canonical name '{alias}'"
                    )
                if alias in seen:
                    raise ValueError(
                        f"alias '{alias}' appears under both '{seen[alias]}' and '{skill_name}'"
                    )
                seen[alias] = skill_name

        return self

    @model_validator(mode="after")
    def _check_parents(self) -> AliasConfig:
        for skill_name, entry in self.skills.items():
            if entry.parent is not None and entry.parent not in self.skills:
                raise ValueError(f"parent '{entry.parent}' of '{skill_name}' does not exist")

        visited: set[str] = set()
        path: set[str] = set()

        def _visit(name: str) -> None:
            if name in path:
                raise ValueError(f"parent cycle detected involving '{name}'")
            if name in visited:
                return
            path.add(name)
            parent = self.skills[name].parent
            if parent is not None:
                _visit(parent)
            path.discard(name)
            visited.add(name)

        for name in self.skills:
            _visit(name)

        return self


class RolePattern(BaseModel, frozen=True):
    include: list[str]

    @field_validator("include", mode="after")
    @classmethod
    def _compile_patterns(cls, v: list[str]) -> list[str]:
        for pattern in v:
            try:
                re.compile(pattern, re.IGNORECASE)
            except re.error as exc:
                raise ValueError(f"invalid regex '{pattern}': {exc}") from exc
        return v


class RolesConfig(BaseModel, frozen=True):
    roles: dict[Role, RolePattern]
    exclude: list[str]
    precedence: list[Role]

    @field_validator("exclude", mode="after")
    @classmethod
    def _compile_exclude(cls, v: list[str]) -> list[str]:
        for pattern in v:
            try:
                re.compile(pattern, re.IGNORECASE)
            except re.error as exc:
                raise ValueError(f"invalid exclude regex '{pattern}': {exc}") from exc
        return v

    @model_validator(mode="after")
    def _check_precedence(self) -> RolesConfig:
        if set(self.precedence) != _VALID_ROLES:
            raise ValueError(
                f"precedence must list exactly {sorted(r.value for r in _VALID_ROLES)}, "
                f"got {[r.value for r in self.precedence]}"
            )
        if len(self.precedence) != len(_VALID_ROLES):
            raise ValueError("precedence must not contain duplicates")
        return self


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"data file not found: {path}")
    with path.open() as f:
        return yaml.safe_load(f)


@functools.cache
def load_config(
    data_dir: Path = _DATA_DIR,
) -> tuple[AliasConfig, RolesConfig]:
    """Load and validate aliases.yaml and roles.yaml from *data_dir*."""
    aliases_raw = _load_yaml(data_dir / "aliases.yaml")
    roles_raw = _load_yaml(data_dir / "roles.yaml")

    aliases = AliasConfig(skills=aliases_raw)
    roles = RolesConfig(**roles_raw)

    return aliases, roles
