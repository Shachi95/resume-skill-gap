# Phase 4 Review, Round 2

Verified by running `make check` (494 passed, 2 skipped, ruff/mypy clean, locks OK) and `make eval` (combined F1 0.8888, PASS).

## 1. Criteria Lacking Meaningful Tests
Round 1 gaps are closed. `service/tests/unit/test_extraction.py` covers config forwarding, forced tool_choice, status mapping (including the new AnthropicError catch-all), schema failure, `_merge` and `_split`.

## 2. Tests That Would Pass Against a Broken Implementation
No new concerns. The unit tests assert specific outcomes: exception types, kwargs, a single merged entry, and strongest level wins.

## 3. Scope Creep
None. The per-file eval output and the stderr note are direct fixes for round 1 item 3.

## 4. Risks for a Human
- The eval LLM path is still a dummy client, so the llm row is 0 and combined equals dictionary-only. This is now disclosed on stderr. The 0.80 gate measures dictionary quality only, not the LLM.
- Test-lock modification was approved by the user (item 1).

## Item check
1. Lock modification: accepted per user approval.
2. F1 at least 0.80: 0.8888, confirmed.
3. Eval honesty: stderr note, per-file P/R/F1 in table and JSON, warning on unparseable golden files. Done.
4. Never raises: `except anthropic.AnthropicError` is placed after the specific handlers, and the unit test covers it. Done.
5. Unit tests: 14 tests added. Done.
6. `_merge` no longer reloads config; `lookup` and `alias_config` are threaded through `extract` and `extract_verified`. Done.

## Verdict
**PASS**
