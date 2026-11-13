# Phase 3 Audit Review

## Verdict: PASS

Full suite: 358 passed. `mypy --strict src` and `ruff check .` are clean. No code or tests were modified by this review.

## Test coverage assessment

All testable spec criteria are covered by the 56 acceptance tests, and the coverage table in `docs/reviews/phase-3-tests.md` is accurate and honest about its gaps.

- Posting and resume extractors return valid `ExtractedSkill` lists, including the empty list.
- Level tagging and category enums are checked.
- Malformed output is rejected: bad enum, missing or blank fields, bad envelope, and one bad skill among good ones.
- Grounding: exact, case-insensitive, fuzzy, configurable threshold, adversarial fabricated evidence, order, purity.
- Retry: recovery, exhaustion, backoff delays, non-retryable errors not retried.
- No live API calls.

Gaps, none blocking:
- Anthropic SDK wiring in `_call_llm` is untested. This is inherent, since no network is allowed in tests. A unit test with a fake client would help (builder or later phase).
- "All test fixtures" is only partly covered. The mock returns one canned response, and only one posting is run through grounding.
- Several malformed-envelope assertions are loose (`pytest.raises(Exception)`). They are weak but acceptable.
- The resume "always unspecified" behavior is verified only against the fixture, because the extractor does not enforce it.

## Implementation assessment

`extractor.py` and `grounding.py` are small, typed, and clean. `_call_llm` is the only network boundary and is easy to monkeypatch. Retry uses exponential backoff, retries only on 429 and 5xx, and does not retry other errors. The schema is derived from the `Category` and `Level` enums, so it cannot drift from the models. Grounding checks substring first, then fuzzy line-level matching.

## Risks and concerns (non-blocking)

1. Malformed output is not handled "gracefully". `parse_extraction_response` raises `KeyError` for a missing `skills` key, `TypeError` for a non-list, and pydantic `ValidationError` for bad items. There is no single domain error, and one bad skill rejects the whole batch. Consider a unified `ExtractionError` and per-item drop in a later phase.
2. Grounding is not wired into the extractors. Callers must remember to call `validate_grounding`. That is fine per the spec, but the pipeline phase must do it. The CLAUDE.md rule says every AI output is "schema-validated, grounded, and normalized", and normalization is not present here.
3. Fuzzy matching is line-level against the whole line. Long lines can reject a legitimately short, slightly altered evidence phrase, and short lines can match loosely. Acceptable at 0.85.
4. Resume-level "always unspecified" is enforced only by the prompt, not in code. Level control flow is left to the LLM. Consider forcing it in code for determinism.
5. `_MODEL` is hardcoded. It should move to config or a data file eventually.
6. `_call_with_retry` ends with `raise last_err  # type: ignore[misc]`. This is harmless.
7. The Phase 3 spec still says "Acceptance tests pending independent audit". Update it after merge.

## Required changes

None.
