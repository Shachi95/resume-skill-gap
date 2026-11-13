# Phase 1 — Models, Data, Normalizer

Goal: Build the core data layer — models, skill dictionary, normalizer, category classifier, ranking, and deduplication.

Depends on: Phase 0 (repo structure, design doc, fixtures)

## Deliverables

- Pydantic models: Skill, Posting, Resume, Gap, RankedGap
- Data files: dictionary.yaml (canonical names, aliases, categories, parents), roles.yaml (role patterns, exclusions, precedence)
- Normalizer: synonym resolution via dictionary lookup, lowercasing, stripping
- Category classifier: assign category from dictionary; flag ambiguous entries
- Ranking: score gaps using required=1.0, unspecified=0.75, preferred=0.5; sort by score descending
- Deduplicate: collapse duplicate skills by canonical name, merge evidence and counts
- CLI skeleton: Typer app with `analyze` placeholder command

## Exit criteria

- `make check` passes (ruff format, ruff check, mypy strict, pytest)
- All new modules have unit tests with ≥90% line coverage
- Normalizer resolves every alias in dictionary.yaml to its canonical name
- Hypothesis property tests for model round-trips and normalizer idempotence
- No regressions in existing tests

## Note

Acceptance tests pending independent audit.

## Iteration cap: 6
