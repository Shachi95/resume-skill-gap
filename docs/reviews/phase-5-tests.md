# Phase 5 acceptance test coverage

Assumed API: `skillgap.report.generate_json_report(ranked) -> str`, `generate_html_report(ranked) -> str`;
CLI `skillgap analyze POSTING... --resume PATH --format json|html|both` (json/html to stdout; `both` to stdout and/or files in cwd).
End-to-end tests use dictionary-only extraction (all postings level `unspecified`) and resume skills are subtracted from gaps.

| Criterion | Test function(s) | Status |
|---|---|---|
| AC-1.1 JSON string | test_ac_1_1_json_report_returns_valid_json_string | covered |
| AC-1.2 RankedGap schema | test_ac_1_2_json_round_trips_to_ranked_gaps, test_ac_1_5_json_deterministic_and_round_trips_property, test_ac_1_unicode_skill_survives_json | covered |
| AC-1.3 empty -> [] | test_ac_1_3_empty_gaps_gives_empty_json_array | covered |
| AC-1.4 no company names (JSON) | test_ac_1_4_json_has_no_company_names | partially covered (report fn only sees gaps; real check is AC-5.1) |
| AC-1.5 deterministic | test_ac_1_5_json_is_deterministic_example, ..._property | covered |
| AC-2.1 HTML string | test_ac_2_1_html_report_returns_string, test_ac_2_empty_gaps_still_valid_document | covered |
| AC-2.2 all skills present | test_ac_2_2_html_contains_all_skills, test_ac_2_2_html_escapes_markup_in_skill_names | covered |
| AC-2.3 structure | test_ac_2_3_html_document_structure (doctype, html lang, head, title, meta viewport, body) | covered |
| AC-2.4 no company names (HTML) | test_ac_2_4_html_has_no_company_names | partially covered (see AC-5.1) |
| AC-2.5 styled | test_ac_2_5_html_is_styled, test_ac_2_5_html_is_theme_aware_and_responsive | covered |
| AC-2.6 ordered by score | test_ac_2_6_html_orders_by_score_descending | covered |
| AC-2.7 category/levels/score | test_ac_2_7_html_shows_category_counts_and_score | partially covered (presence in page, not per-row, to allow layout freedom) |
| AC-3.1 command/help | test_ac_3_1_analyze_help | covered |
| AC-3.2 --format json | test_ac_3_2_format_json_prints_json_to_stdout, test_ac_3_5_default_format_is_valid_output | covered |
| AC-3.3 --format html | test_ac_3_3_format_html_prints_html_to_stdout | covered |
| AC-3.4 --format both | test_ac_3_4_format_both_produces_both_formats | covered (flexible on stdout vs files) |
| AC-3.5 resume + positional postings | test_ac_3_5_accepts_resume_and_positional_postings | covered |
| AC-3.6 exit 0 | test_ac_3_6_exit_zero_on_success | covered |
| AC-3.7 nonexistent paths | test_ac_3_7_nonexistent_posting_exits_nonzero, ..._resume_..., test_ac_3_invalid_format_value_rejected | covered |
| AC-3.8 help completeness | test_ac_3_8_help_mentions_all_options_and_arguments | covered |
| AC-4.1 e2e JSON | test_ac_4_1_end_to_end_json_report, test_ac_4_1_skills_on_resume_are_not_gaps, test_ac_4_cli_json_is_deterministic, test_ac_4_cli_posting_order_does_not_change_gaps | covered |
| AC-4.2 e2e HTML | test_ac_4_2_end_to_end_html_report | covered |
| AC-4.3 matches rank_gaps | test_ac_4_3_cli_gaps_match_rank_gaps | covered |
| AC-5.1 company name absent | test_ac_5_1_company_name_never_appears_in_any_format, test_ac_5_1_evidence_lines_are_not_emitted | covered |
| AC-5.2 number + role title only | test_ac_5_2_postings_referenced_by_number_not_path | partially covered: only checks file names/paths are not leaked. Posting number/title rendering is not asserted because the spec'd report input (ranked gaps) carries no posting metadata; builder's choice. |
| W3C validation | not testable offline (no network); structural checks in AC-2.3 approximate it | not testable |
| `make check` / reviewer PASS | process criteria | not testable |

Report-module tests are strict-xfail until `skillgap.report` exists; the builder must expect XPASS(strict) failures to be resolved by creating it.
