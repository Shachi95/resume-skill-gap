# Phase 2 acceptance test coverage (independent audit)

| Criterion | Test function(s) | Status |
|---|---|---|
| Fetcher: httpx-based, returns raw HTML | test_fetch_returns_raw_html_for_mocked_url, test_fetch_second_mocked_url, test_fetch_http_error_status_raises | covered |
| Fetcher respects robots.txt | test_fetch_checks_robots_txt, test_fetch_raises_when_robots_disallows, test_robots_disallowed_does_not_fetch_page, test_robots_disallowed_error_is_exception | covered |
| Fetcher rate-limited | test_fetch_is_rate_limited, test_fetch_high_rate_limit_is_fast | partially covered (timing-based; spec gives no exact semantics) |
| Fetcher identifies itself (user agent) | test_fetch_sends_user_agent_header | partially covered (not in spec; inferred) |
| Cleaner: strips tags, nav, footer, scripts, styles | test_clean_strips_tags, test_clean_strips_nav_footer_script_style, test_clean_fallback_* | covered |
| Cleaner: trafilatura primary, BeautifulSoup fallback | test_clean_fallback_for_minimal_html, test_clean_fallback_on_bare_fragment | partially covered (behavioral only; engine choice not observable) |
| Cleaner edge cases: empty, malformed | test_clean_empty_input_returns_blank, test_clean_malformed_html_does_not_raise | covered |
| Cleaner strips boilerplate from all 30 posting fixtures | test_clean_strips_boilerplate_from_all_posting_fixtures (30 params), test_fixture_corpus_has_thirty_postings, test_clean_html_fixture_strips_boilerplate | partially covered (plain-text fixtures wrapped in HTML with injected boilerplate by the test) |
| Splitter: regex-first standard headings, aliases | test_split_identifies_standard_sections, test_split_heading_aliases_normalize, test_split_is_case_insensitive, test_split_section_bodies_do_not_leak | covered |
| Splitter edge cases: empty, no headings, missing sections | test_split_empty_input, test_split_no_headings_returns_empty, test_split_missing_sections_only_returns_present, test_split_ignores_heading_words_inside_sentences | covered |
| Splitter finds requirements/preferred/responsibilities in >=80% of fixtures | test_split_finds_requirements_in_at_least_80_percent_of_fixtures, test_split_finds_target_sections_in_at_least_80_percent_of_fixtures | covered (criterion read as "at least one target section"; also requirements alone) |
| Splitter: AI fallback for non-standard layouts | none | not testable (no AI in tests; no public interface for it in splitter) |
| Parser orchestrates fetch -> clean -> split, returns Posting | test_parse_posting_*, test_fetch_then_parse_end_to_end, test_posting_model_rejects_blank_title_and_text | covered (parse_posting takes html; fetch composition tested end to end) |
| Fetcher returns valid HTML for fixture URLs (mocked) | test_fetch_returns_raw_html_for_mocked_url | covered |
| No live HTTP in CI | test_no_unmocked_network_calls (plus respx.mock in conftest) | covered |
| Recorded HTTP fixtures exist | tests/fixtures/http_responses present | not tested directly |
| make check passes | n/a | not testable at this level |
