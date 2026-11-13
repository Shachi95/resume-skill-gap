# Phase 3 acceptance test coverage

Tests: `service/tests/acceptance/phase_3/test_phase_3.py` (independent audit rewrite).

| Criterion | Test function(s) | Status |
|---|---|---|
| Posting extractor returns ExtractedSkill list | test_extract_posting_skills_returns_extracted_skill_list, test_posting_extraction_matches_recorded_response, test_posting_extraction_contains_expected_skills, test_posting_prompt_routes_to_posting_response | covered |
| Resume extractor returns ExtractedSkill list | test_extract_resume_skills_returns_extracted_skill_list, test_resume_extraction_matches_recorded_response | covered |
| Empty skills list handled | test_extraction_empty_skills_returns_empty_list, test_parse_empty_skills_list | covered |
| Required/preferred/unspecified tagging (posting) | test_posting_levels_are_level_members_and_mixed, test_level_enum_values | covered |
| Resume skills unspecified | test_resume_levels_are_unspecified | covered (against recorded fixture; extractor-forced behavior not distinguishable from mock) |
| Category enum use | test_extracted_categories_are_category_enum_members, test_posting_categories_mapped_as_recorded, test_category_enum_values | covered |
| Schema validation rejects malformed output (bad enum, missing/blank fields, bad envelope) | test_parse_rejects_malformed_skill, test_parse_rejects_malformed_envelope, test_one_bad_skill_is_not_silently_accepted, test_extract_raises_on_malformed_llm_output | covered |
| parse_extraction_response converts dicts | test_parse_valid_response, test_parse_recorded_responses, test_parse_coerces_enum_types | covered |
| Model immutability | test_extracted_skill_is_frozen | covered |
| Grounding accepts real evidence | test_grounding_accepts_exact_evidence, test_grounding_accepts_all_recorded_*, test_grounding_is_case_insensitive, test_grounding_against_posting_fixtures | covered |
| Grounding rejects fabricated evidence (adversarial) | test_grounding_rejects_fabricated_evidence, test_grounding_filters_only_ungrounded, test_grounding_rejects_unrelated_evidence_even_with_shared_words, test_adversarial_llm_output_is_filtered_end_to_end | covered |
| Fuzzy threshold | test_grounding_fuzzy_accepts_minor_variation, test_grounding_threshold_is_configurable | covered |
| Grounding order/purity/empty | test_grounding_preserves_order, test_grounding_empty_inputs, test_grounding_does_not_mutate_input | covered |
| Retry on rate limits/transient failures | test_retry_recovers_from_transient_failure, test_retry_gives_up_after_persistent_failure, test_retry_uses_backoff_delays | covered (patches time.sleep globally) |
| Non-retryable errors not retried | test_non_retryable_error_is_not_retried, test_exception_classes_are_distinct_exceptions | covered |
| Anthropic SDK structured output integration | none | not testable (network-only `_call_llm`; no live calls allowed) |
| Recorded fixtures exist and replay | test_*_matches_recorded_response, test_parse_recorded_responses | covered |
| No live API calls | test_llm_call_is_mocked_in_acceptance_tests, test_no_network_when_llm_mocked | covered |
| `make check` passes | none | not testable in pytest (run `make check`) |
| Extractor valid for "all test fixtures" (30 postings) | test_grounding_against_posting_fixtures (one file only) | partially covered (mock returns one canned response regardless of posting) |
