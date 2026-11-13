# Phase 3 — AI Skill Extraction

Goal: Use an LLM to extract skills from posting text and resume text, returning schema-validated, grounded results.

Depends on: Phase 2 (posting parser, section splitter)

## Deliverables

- Anthropic SDK integration: structured output with Pydantic schema enforcement
- Posting skill extractor: extract skills from each section, tag required/preferred/unspecified
- Resume skill extractor: extract skills from resume text
- Grounding validator: every evidence phrase must exist in the source text (fuzzy match threshold)
- Recorded response fixtures: captured API responses for deterministic test replay
- Retry logic: handle rate limits and transient failures

## Exit criteria

- `make check` passes
- Extractor returns valid ExtractedSkill models for all test fixtures
- Grounding check rejects fabricated evidence (test with adversarial fixtures)
- All tests use recorded responses; no live API calls in CI
- Schema validation rejects malformed LLM output gracefully

## Iteration cap: 5
