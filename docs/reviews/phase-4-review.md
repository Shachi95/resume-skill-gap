# Phase 4 Review

## 1. Criteria Lacking Meaningful Tests

- AC-1.3 / 5.2 (AnthropicLLMClient uses config.model and max_tokens), AC-1.7 and the status mapping (429/5xx retryable, other 4xx non-retryable), the forced `record_skills` tool_choice, and schema-failure handling: no test touches `AnthropicLLMClient`. The spec forbids SDK assertions in Phase 4 tests, so the whole SDK boundary is untested. A unit test with a stub SDK is needed (builder added none).
- AC-1.8 merge semantics ("dedup by canonical name, strongest level wins"): the long-text test only checks `len(calls) == 2` and the return type. Nothing checks that the halves are distinct, that they cover the whole text, or that merge dedups or keeps the strongest level. `_merge` is unverified.
- AC-3.3 (retry prompt includes the previous extraction): the test only checks that `evidence_not_in_text` appears in the second call's text. The "previous extraction" part is unchecked.
- AC-3.6 (logging attempt number, error count, accepted count): the test asserts at least 3 records and that the characters "1", "2", "3" appear anywhere in the joined messages. Any log line containing digits passes.
- AC-7.2 / 7.3 (eval metrics): the tests check only key presence and `isinstance(float)`. The LLM path is not exercised with recorded responses, and nothing checks that the numbers are correct or non-degenerate. The build's llm path is hard-wired to 0.0 and the test still passes.
- AC-7.6: the exit-1 test is fine. There is no positive test that the exit code is 0 when F1 is at or above the threshold, other than the `EVAL_MIN_F1=0.0` case.
- AC-4.1: the spec says `\b`. The implementation uses `(?<!\w)...(?!\w)`. This is arguably better for "c++" and "c#", but no test covers symbol-terminated skills.
- Exit criterion "make eval passes with F1 >= 0.80": no test covers it, and it currently fails (see section 4).

## 2. Tests That Would Pass Against a Broken Implementation

- `test_client_none_constructs_default_llm_client` uses `mock.patch`. This sidesteps the `monkeypatch.setattr` regex guard (AC-6.2 spirit). It passes if `extract()` calls the constructor and never uses the SDK client.
- `test_long_text_splits_into_two_calls`: an implementation that sends the full text twice, or splits at an arbitrary point and drops the middle, passes. A merge that simply concatenates passes too.
- `test_run_py_reports_all_three_paths_and_metrics`: any JSON with the right keys and floats passes. The shipped llm=0.0 stub passes.
- `test_logs_each_attempt`: see section 1.
- `test_p10` idempotence: the assertion `... or not first` plus `>=` is nearly vacuous. The second half is a tautology (`_dict(x) == _dict(x)`).
- `test_p5`: skills dropped for any reason pass as long as the name resolves to an accepted canonical, so a silent drop of an unresolved skill that shares an error name is tolerated.
- `test_max_retries_controls_transient_retries` and `test_exhausted_retries_raise` accept `attempts >= 2` and `2 <= calls <= 3`. An off-by-one in retry count (max_retries vs max_retries+1) passes. Only the `max_retries=0` boundary is exact.
- `test_dedup_strongest_level_wins`: ties (equal level) are not tested. Keep-first vs keep-last is unconstrained.
- `test_fallback_after_all_attempts_fail` uses `>=` on skills. Extra false positives pass.
- Phase-3 "unchanged" test (`TestPhase3Unchanged`) only greps conftest for a string.

## 3. Scope Creep

- `ExtractionConfig`, error classes, and models match the spec. No baseline or regression logic was added (AC-7.4/7.5 respected).
- The Makefile `eval` target was changed to `cd service && uv run ...`. This is reasonable, but it is outside the spec text.
- `_retry_text` embeds error feedback inside the "text" argument passed to the client. This is a design choice. It means the posting prompt builder wraps feedback as if it were posting text, and the token-budget check counts feedback.
- `extract_dictionary` accepts `kind` but never uses it.
- `docs/progress.md` was updated, which is expected.
- The most significant out-of-scope change is the modification of locked acceptance tests (section 4).

## 4. Risks for a Human

1. **Locked acceptance tests were modified and the lock regenerated.** The diff changes `service/tests/acceptance/phase_4/test_phase_4.py` (strict `xfail` markers replaced by import-conditional markers) and rewrites the hash in `LOCK.json`. CLAUDE.md says the builder may never modify acceptance tests, and the lock exists to enforce that. The change is likely benign and was arguably forced: the strict xfail would XPASS-fail once the implementation exists, which is a test-writer design flaw. But it defeats the lock and was done unilaterally. A human must decide whether to accept it. It should have gone to `docs/blocked.md` or the test writer. The new conditional also means that a broken import of `skillgap.extraction` silently turns xfails back on instead of failing.
2. **`make eval` fails against the spec exit criterion.** I ran it: combined F1 = 0.7455 < 0.80, exit code 1, and the Makefile reports an error. The exit criteria require "`make eval` passes with F1 >= 0.80". The builder's summary reports dictionary F1=0.75 and calls the eval "working", but the gate is not met.
3. **The eval is not a real three-path evaluation.** The LLM path uses a stub client returning an empty result, so llm P/R/F1 is always 0. The combined path is therefore just the dictionary fallback (identical numbers). AC-7.2 calls for recorded responses, but none exist. The gate F1 is on "combined", which is really dictionary-only. Spec AC-7.6 says "aggregate F1" without saying which path, and this ambiguity should be resolved. Aggregates are also macro averages across files, which hides per-file results (the spec asks for per-file metrics too, and none are reported).
4. **"Never raises" gap.** `extract_verified` catches only `LLMExtractionError` and `NonRetryableExtractionError`. With `client=None` and no API key, `anthropic.Anthropic()` raises `AnthropicError` inside `_sdk()`. That is not mapped by `AnthropicLLMClient` (only `APIStatusError`/`RateLimitError`/`APIConnectionError` are), so it escapes `extract_verified`, violating AC-3.5 and hypothesis property 7 for the real client. Likewise a generic `ValidationError` or unexpected block shape in `extract` is only partly covered.
5. **Failed-attempt state.** When an attempt raises, `last_report` is not cleared or updated. If every attempt raises, the fallback result has `errors=()` and no indication of why. Acceptable per tests, but downstream consumers cannot tell a clean fallback from an error fallback except by `source`.
6. **`_merge` reloads config.** It calls `load_config()` on every oversized extract and ignores any injected lookup or alias_config. That is a hidden file read, and normalization can diverge from what `verify` uses.
7. **`verify` skill-in-text is a raw substring check.** Short names ("go", "r", "c") match inside any word, so the check is weak for ambiguous skills. This follows the spec literally. Evidence grounding with a fuzzy 0.85 threshold on long lines can accept altered evidence.
8. **Hard-coded retry counts.** `max_retries` gives `max_retries + 1` calls and real `time.sleep` backoff. In `extract_verified` this compounds: up to 3 attempts x 4 calls with exponential sleeps (1+2+4 s each, about 21 s of sleeping) before fallback.
9. **Style and lint.** `evals/run.py` carries the `# type: ignore[no-any-return]` and a broad `except Exception: pass` that silently drops a malformed golden file, so a broken golden file would shrink the eval set without any warning.

## Verdict

**CHANGES NEEDED**

1. Resolve the locked-test modification. Revert the edits to `test_phase_4.py` and `LOCK.json`, or get explicit human or test-writer approval and record it. Do not leave it as an unflagged builder edit.
2. Make `make eval` meet the exit criterion (F1 >= 0.80), or get an explicit human decision to change the threshold or scope. Currently combined F1 = 0.7455 and the command exits 1. Improve dictionary recall or golden coverage rather than weakening the gate.
3. Make the eval honest. Either add recorded LLM responses (fixtures) so the llm and combined paths are real, or document that the llm path is a stub and clarify which F1 is gated. Report per-file metrics (AC-7.3) and warn on unparseable golden files instead of silently skipping them.
4. Fix AC-3.5. Make `AnthropicLLMClient` map `anthropic.AnthropicError` (e.g. missing API key) to `NonRetryableExtractionError`, or have `extract_verified` catch `ExtractionError` and `RetryableExtractionError` too. Add a unit test.
5. Add unit tests (in `tests/unit/`) for `AnthropicLLMClient` (model/max_tokens passed, forced `record_skills` tool, status mapping, schema failure) and for `_merge` / split behaviour (strongest level wins, halves cover the full text).
6. Make `_merge` use the same lookup and alias_config as the caller instead of calling `load_config()` itself, or document why not.
