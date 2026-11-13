# Phase 1 acceptance test coverage

File: `service/tests/acceptance/phase_1/test_phase_1.py` (85 tests, all passing at time of writing).

| Criterion | Test function(s) | Status |
|---|---|---|
| Models: Skill, Posting, Resume, Gap, RankedGap exist and validate | test_skill_*, test_posting_*, test_resume_valid_and_blank_text, test_extracted_skill_validation, test_gap_*, test_ranked_gap_rank_boundary, test_models_are_frozen, test_enums_values | covered |
| Hypothesis model round-trips | test_skill_roundtrip, test_gap_and_ranked_roundtrip, test_posting_resume_roundtrip | covered |
| Data: aliases (canonical names, aliases, categories, parents) loadable and valid | test_data_files_exist_and_parse, test_load_config_returns_valid_models, test_alias_entries_well_formed, test_aliases_unique_across_skills, test_parent_chains_acyclic, test_alias_config_rejects_* , test_alias_config_lowercases, test_load_config_missing_dir | covered |
| Data: roles (patterns, exclusions, precedence) loadable and valid | test_roles_config_structure, test_roles_config_rejects_bad_regex, test_roles_config_rejects_bad_precedence | covered |
| Normalizer resolves every alias to canonical | test_every_alias_resolves_to_canonical, test_build_lookup_keys, test_normalizer_alias_casing_property | covered |
| Normalizer lowercasing / stripping / unknown / empty | test_normalize_case_and_whitespace, test_normalize_unknown_and_empty, test_normalize_batch | covered |
| Normalizer idempotence (Hypothesis) | test_normalizer_idempotent | covered |
| Parent resolution | test_get_parents | covered |
| Classifier: category from dictionary | test_classify_matches_dictionary, test_classify_unknown, test_validate_category | covered |
| Classifier: flag ambiguous entries | test_ambiguity_flag, test_every_alias_resolves_to_canonical (ambiguous propagated to Skill) | covered |
| Role classification (roles.yaml usage, exclusions, precedence) | test_classify_role, test_classify_role_precedence_and_exclude_first | covered (not in the spec deliverables list but in public classifier API) |
| Ranking weights 1.0 / 0.75 / 0.5, summed | test_score_constants, test_score_sums_across_postings, test_score_property | covered |
| Ranking sorted by score desc, determinism | test_rank_*, test_rank_order_property (Hypothesis) | covered |
| Dedup by canonical name, merge evidence and counts | test_dedup_extracted_*, test_dedup_preserves_all_mentions, test_merge_*, test_dedup_gaps_* | covered |
| CLI: Typer app with `analyze` placeholder | test_cli_* | covered |
| Exit: `make check`, >=90% unit coverage, no regressions | n/a | not testable at acceptance level (CI/tooling gates) |
| Exit: no AI/network calls | all tests are offline | covered by construction |

## Spec discrepancies and assumptions

- Spec names the data file `dictionary.yaml`; the repo and CLAUDE.md use `aliases.yaml`. Tests target `aliases.yaml`.
- Spec says "merge evidence"; `Gap` has no evidence field, so evidence preservation is tested at the `dedup_extracted_skills` level (all mentions retained).
- Merged-gap score for `dedup_gaps` is assumed to be the sum of input scores (spec: scores summed across postings).
- Version-suffix stripping in the normalizer is not in the spec and is deliberately not tested.
