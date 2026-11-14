# Phase 4 acceptance test coverage

File: `service/tests/acceptance/phase_4/test_phase_4.py`. Classes are `xfail(strict=True)` because `skillgap.extraction`, `skillgap.verification`, and the new models do not exist yet. Only `TestPhase3Unchanged` and the golden/Makefile tests in `TestEvals` run for real today. Imports of new modules are lazy, so collection never errors. The Anthropic SDK is behind a `LLMClient` Protocol; tests use `FakeLLMClient` (scripted with `ExtractionResult | Exception` outcomes). `time.sleep` is avoided with `base_delay=0.0`.

| Criterion | Test function(s) | Status |
|---|---|---|
| AC-1.1 kind routing | TestExtract::test_jd_routes_kind_jd, test_resume_routes_kind_resume, test_unicode_text_passed_through | covered |
| AC-1.2 client call | TestExtract::test_extract_returns_client_result | covered |
| AC-1.3 config passed to client | TestExtract::test_default_config_used; TestExtractionConfig::test_config_passed_to_client | covered |
| AC-1.4 client None builds AnthropicLLMClient | TestExtract::test_client_none_constructs_anthropic_from_env | covered (patches `AnthropicLLMClient`, not `anthropic.Anthropic`) |
| AC-1.5 validated ExtractionResult | TestExtract::test_returns_extraction_result, test_empty_skills_list_is_valid | covered |
| AC-1.6 transient retry + LLMExtractionError | TestExtract::test_retries_transient_errors (429/500/502/503), test_exhausted_retries_raise | covered (asserts `LLMExtractionError` with `.attempts` and `.__cause__`) |
| AC-1.7 non-retryable / schema failure | TestExtract::test_non_retryable_status_raises_without_retry, test_non_retryable_schema_error_propagates | covered |
| AC-1.8 token budget | TestExtract::test_short_text_makes_one_call, test_long_text_splits_into_two_calls | covered (checks `len(client.calls)` against `TOKEN_BUDGET`) |
| AC-2.1 evidence grounding | TestVerify::test_evidence_not_in_text, test_evidence_case_insensitive, test_evidence_fuzzy_match_above_threshold, test_evidence_fuzzy_respects_threshold_parameter | covered |
| AC-2.2 skill in text | TestVerify::test_skill_not_in_text, test_skill_in_text_via_alias, test_evidence_failure_reported_once_not_also_skill_not_in_text | covered |
| AC-2.3 normalization | TestVerify::test_normalization_sets_canonical_and_dictionary_category, test_unresolved_goes_to_candidates | covered |
| AC-2.4 dedup strongest level | TestVerify::test_dedup_strongest_level_wins (6 orderings), test_dedup_keeps_other_skills, test_dedup_counts_toward_too_few | covered |
| AC-2.5 count bounds | TestVerify::test_too_few_skills, test_empty_result_too_few, test_exactly_three_is_ok, test_forty_skills_ok, test_forty_one_skills_too_many | covered |
| AC-2.6 ok flag | TestVerify::test_good_skills_accepted_ok, test_ok_false_when_errors_even_with_enough_accepted; Hypothesis P6 | covered |
| AC-3.1 loads lookup/alias_config | TestExtractVerified::test_loads_config_by_default, test_explicit_lookup_and_alias_config_accepted | covered |
| AC-3.2 success returns source=llm | TestExtractVerified::test_returns_llm_on_first_success, test_retry_after_failed_verification_succeeds | covered |
| AC-3.3 retry prompt with errors | TestExtractVerified::test_retry_prompt_includes_errors_and_previous_extraction | covered |
| AC-3.4 fallback after last attempt | TestExtractVerified::test_fallback_after_all_attempts_fail, test_max_attempts_one | covered |
| AC-3.5 never raises | TestExtractVerified::test_api_errors_never_raise, test_schema_invalid_output_never_raises, test_error_then_success_recovers, fixture tests; Hypothesis P7 | covered |
| AC-3.6 logging | TestExtractVerified::test_logs_each_attempt | partially covered: log wording is not specified, so the test checks logger name `skillgap.extraction`, at least N records, and the attempt numbers appearing |
| AC-4.1 word-boundary scan | TestExtractDictionary::test_finds_known_skills, test_case_insensitive, test_alias_resolves_to_canonical, test_word_boundary_respected | covered |
| AC-4.2 skill construction | TestExtractDictionary::test_skill_fields, test_evidence_is_single_line_from_text, test_evidence_grounded | covered |
| AC-4.3 first match wins | TestExtractDictionary::test_first_match_wins_dedup, test_alias_and_canonical_dedup_to_one | covered |
| AC-4.4 ambiguous skills | TestExtractDictionary::test_ambiguous_skipped_in_prose, test_ambiguous_kept_in_comma_list, test_ambiguous_kept_in_bullet_list | covered |
| AC-4.5 only present skills | TestExtractDictionary::test_empty_text, test_no_skills_in_text; Hypothesis P9 | covered |
| AC-5.1 frozen defaults | TestExtractionConfig::test_defaults, test_frozen, test_overridable | covered |
| AC-5.2 config passed to client | TestExtractionConfig::test_config_passed_to_client | covered |
| AC-5.3 max_retries/base_delay | TestExtractionConfig::test_max_retries_controls_transient_retries, test_zero_retries_makes_single_call | covered for max_retries. `base_delay` timing is not asserted (no sleeping or clock mocking in tests), so it is only partially covered |
| AC-6.1 client param | TestDI::test_extract_accepts_client, test_extract_verified_accepts_client, test_verify_signature | covered |
| AC-6.2 DI, no monkeypatch | TestDI::test_injected_client_is_the_one_used, test_extract_verified_uses_injected_client, test_no_monkeypatch_setattr_in_phase_4_tests | covered |
| AC-6.3 Phase 3 unchanged | TestPhase3Unchanged::test_phase_3_still_uses_monkeypatch_of_call_llm | covered (runs now) |
| AC-7.1 loads reviewed goldens | TestEvals::test_golden_files_present_and_reviewed, test_golden_skills_are_canonical | partially covered: validates the golden inputs only (15 files, `reviewed: true`, fixture exists, skills canonical). Runs now |
| AC-7.2 three paths | TestEvals::test_run_py_reports_all_three_paths_and_metrics | covered: passes `--format json`, parses stdout as JSON, asserts `llm`, `dictionary`, `combined` keys |
| AC-7.3 P/R/F1 + --format json | TestEvals::test_run_py_reports_all_three_paths_and_metrics | covered: asserts each path contains `precision`, `recall`, `f1` as floats |
| AC-7.4 baseline.json | TestEvals::test_baseline_written_on_first_run | DEFERRED: placeholder `@pytest.mark.skip` test |
| AC-7.5 regression reporting | TestEvals::test_regression_detected_on_second_run | DEFERRED: placeholder `@pytest.mark.skip` test |
| AC-7.6 exit 1 below EVAL_MIN_F1 | TestEvals::test_run_py_exits_1_below_min_f1 (EVAL_MIN_F1=1.01) | covered |
| AC-7.7 make eval | TestEvals::test_make_eval_invokes_run_py | covered (runs now) |

## Models

All of these are in TestNewModels: ExtractionResult (round trip, frozen, dict validation, bad skill), AcceptedSkill, VerifyError (the 4 reasons, a bad reason, default detail), VerifyReport, and VerifiedExtractionResult (defaults, `source` literal, frozen). `test_existing_models_unchanged` guards the ExtractedSkill field set.

## Hypothesis properties

| # | Test |
|---|---|
| 1 | TestHypothesis::test_p1_never_accepts_ungrounded_evidence |
| 2 | test_p2_verify_deterministic |
| 3 | test_p3_accepted_subset_of_input |
| 4 | test_p4_no_duplicate_canonical_names |
| 5 | test_p5_every_input_accounted_for (a dedup-dropped skill counts as accounted for if its canonical name was accepted) |
| 6 | test_p6_ok_flag_consistent |
| 7 | test_p7_extract_verified_never_raises (scripted outcomes: good, bad, empty, invalid, 429, 400, 500) |
| 8 | test_p8_fallback_skills_in_lookup |
| 9 | test_p9_dictionary_only_returns_present_skills |
| 10 | test_p10_dictionary_deterministic_and_idempotent |

## Exit criteria

- "`extract_verified()` never raises for any fixture": `test_recorded_fixture_posting_never_raises` runs all 30 posting fixtures plus the resume fixture.
- "`verify()` is deterministic": Hypothesis P2.
- "No monkeypatch.setattr in Phase 4 tests": `test_no_monkeypatch_setattr_in_phase_4_tests`.
