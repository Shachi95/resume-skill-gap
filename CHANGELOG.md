# Changelog

## 6.0.0 — 2026-11-10

- **Phase 3 implemented:** AI skill extraction with schema validation and grounding.
- New modules: `skillgap.extractor` (Anthropic SDK tool_use, retry logic, error classes), `skillgap.grounding` (fuzzy evidence matching via difflib).
- Posting extractor tags skills as required/preferred/unspecified by section.
- Resume extractor extracts skills with evidence phrases.
- Grounding validator rejects fabricated evidence (case-insensitive + fuzzy threshold).
- Recorded response fixtures in `tests/fixtures/recorded_responses/` — no live API calls in CI.
- Added dependency: anthropic SDK.
- All 19 Phase 3 acceptance tests pass; 208 tests total.
- Added `.gitignore` entries for real user data (`service/data/user/`, `service/output/`).

## 5.0.0 — 2026-11-10

- **Phase 2 implemented:** posting ingestion pipeline (fetch → clean → split → parse).
- New modules: `skillgap.fetcher` (httpx, robots.txt, rate-limited), `skillgap.cleaner` (trafilatura + BS4 fallback), `skillgap.splitter` (regex-first section detection), `skillgap.parser` (orchestrator returning Posting model).
- Extended `Posting` model with `sections: dict[str, str]` field.
- Added dependencies: httpx, trafilatura, beautifulsoup4, respx (dev).
- All 19 Phase 2 acceptance tests pass; splitter finds sections in 100% of 30 fixtures.
- HTTP mocking via respx in acceptance test conftest — no live network calls.

## 4.1.0 — 2026-11-10

- Added acceptance tests for Phase 2 (Posting Fetcher & Splitter): 19 tests covering fetcher, cleaner, splitter, parser, and model extension — all xfail(strict=True).
- Added acceptance tests for Phase 3 (AI Skill Extraction): 19 tests covering posting/resume extractors, grounding validator, schema validation, retry logic, and recorded responses — 16 xfail, 3 pass (existing model validation).
- Generated acceptance locks for phases 2 and 3.
- Added coverage tables: `docs/reviews/phase-2-tests.md`, `docs/reviews/phase-3-tests.md`.

## 4.0.0 — 2026-11-09

- Restructured loop into three separate roles: test-writer, builder, reviewer.
- Moved all existing tests to `tests/unit/`; created `tests/acceptance/phase_{1..6}/` directories.
- Split conftest: root has Hypothesis profiles, `tests/unit/conftest.py` has fixtures.
- New `scripts/acceptance_lock.py`: `lock N` and `verify` commands for acceptance test integrity.
- New Makefile targets: `test-unit`, `test-acceptance PHASE=N`, `verify-acceptance`.
- `make check` now includes `verify-acceptance`.
- Three subagent definitions in `.claude/agents/`: `test-writer.md`, `builder.md`, `reviewer.md`.
- CLAUDE.md: replaced "Loop rules" with "Roles and loop" section.
- Phase specs 4–6: exit conditions now require `verify-acceptance` + `test-acceptance` + reviewer PASS.
- Phase specs 1–3: added "Acceptance tests pending independent audit" note.
- CI: added `acceptance-guard` job blocking acceptance test changes on `phase-*-build` branches.
- New `docs/workflow.md`: step-by-step guide for running each role per phase.

## 3.2.0 — 2026-11-09

- Normalizer: version stripping — `"Java 17"`, `"Python 3.12"`, `"Node 18.x"` now resolve correctly.
- Normalizer: `get_parents()` walks the parent chain (e.g., `lambda` → `aws`) for partial-match credit.
- Normalizer: unmatched terms logged at DEBUG level for dictionary maintenance.
- Classifier: `classify_role()` maps job titles to roles via `roles.yaml` patterns (exclude-first, then precedence).
- Ranking: added shuffle-invariance Hypothesis property test.
- 112 tests passing.

## 3.1.0 — 2026-11-09

- Phase 1 complete: core data layer for the skill-gap service.
- New models: `Skill`, `Resume`, `RankedGap` in `models.py`.
- Normalizer: resolves raw skill names to canonical entries via `aliases.yaml`.
- Classifier: category lookup and ambiguity checks from the skill dictionary.
- Ranking: scores gaps (required=1.0, unspecified=0.75, preferred=0.5) and sorts descending.
- Deduplication: collapses duplicate skills by canonical name, merges evidence and counts.
- CLI skeleton: `skillgap analyze` (placeholder) and `skillgap version` via Typer.
- Added `typer` and `pytest-cov` dependencies.
- 94 tests passing, 100% coverage on all new modules.

## 3.0.0 — 2026-11-09

- Loop-engineering scaffolding: `make check` and `make eval` commands.
- Phase specs for phases 1–6 in `docs/phases/`.
- CLAUDE.md: added loop rules section for agent-loop development.
- Claude Code Stop hook runs `make check` before session ends.
- Pre-commit config with ruff, mypy, and standard hooks.
- CI updated to use `make check` and `make eval`.
- Progress tracking templates in `docs/progress.md` and `docs/blocked.md`.
- Eval framework stub with `evals/golden/` directory for future golden files.

## 2.3.0 — 2026-11-09

- Added 30 real posting fixtures (10 SWE, 10 FDE, 10 AI PM) in `service/tests/fixtures/postings/`, company names stripped.
- Added anonymized resume fixture in `service/tests/fixtures/resumes/`.
- Phase 0 complete.

## 2.2.0 — 2026-11-09

- CLAUDE.md: split into repo-wide, skill, and service rule sections with full detail.
- Added docs/service-design.md: goal, scope, code-vs-AI table, data models, scoring, phases.
- Added Python defaults to .gitignore.
- No change to the skill itself.

## 2.1.0 — 2026-11-06

- Restructured repo: skill files under `skill/`, new `service/` and `docs/` top-level folders.
- Updated README to cover the full project, not just the skill.

## 2.0.0 — 2026-11-06

- Split gaps into **wording gaps** (skills you have but your resume doesn't say) and **true gaps** (skills to learn).
- Wording gaps include a suggested resume bullet rewrite; hard rule never to fabricate skills.
- True gaps include posting evidence quotes and a concrete next step (certification, project, or resume strategy).
- New **Experience & Seniority Check** section compares each posting's requirements against the resume.
- Small-sample warning when fewer than 5 postings are analyzed.
- Company names removed from all output — postings referenced by number and role title only.
- Updated all test cases and sample HTML outputs.

## 1.1.0 — 2026-11-06

- Output is now an HTML artifact instead of plain markdown tables.
- Visual improvements: color-coded priority pills, horizontal strength bars, numbered priority cards, posting chips.
- Theme-aware (light and dark), responsive layout.
- Short text summary printed in chat before the artifact.

## 1.0.0 — 2026-11-06

- Initial release.
- SKILL.md with five-step workflow: collect inputs, extract resume skills, extract posting skills, match and score, produce output.
- Scoring: required 1.0, unspecified 0.75, preferred 0.5, summed across distinct postings.
- Industry-agnostic categories: Tools/Software, Technical Skills, Certifications/Licenses, Domain Knowledge, Soft Skills.
- Three test cases: software engineer, registered nurse, marketing manager.
