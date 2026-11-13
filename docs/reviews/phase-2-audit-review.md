# Phase 2 Independent Audit Review

## Verdict: PASS

Verification run: `uv run pytest tests/ -x -q` gives 321 passed. `mypy src` is clean (14 files). `ruff check src tests` is clean.

## Test coverage assessment

The 87 acceptance tests cover every testable criterion in `docs/phases/phase-2.md`:

- **Fetcher:** raw HTML is returned, robots.txt is checked, and a disallowed path raises `RobotsDisallowedError` without fetching the page. HTTP error status raises, a non-default user agent is sent, rate limiting is tested, and no unmocked network hosts are hit.
- **Cleaner:**
  - Tags, nav, footer, script and style are stripped.
  - Fallback paths, empty input and malformed HTML are covered.
  - All 30 posting fixtures are run through the cleaner. The plain-text fixtures are wrapped in HTML with injected boilerplate, which the coverage table flags honestly.
- **Splitter:**
  - Standard headings, aliases, case-insensitivity and body leakage are covered.
  - Empty input, missing sections and heading words inside sentences are covered.
  - The 80% threshold is tested, read as "at least one target section", with a stricter requirements-only variant.
- **Parser:** a valid Posting, sections, cleaned text, a deterministic and URL-specific id, empty and blank input raising `ValueError`, malformed HTML, and fetch-to-parse end to end.

Gaps, none blocking:

1. The AI fallback for non-standard layouts is untested. The splitter exposes no interface for it and tests may not call AI, so this is correctly recorded as not testable. It should get a phase-3 or unit-level test once an interface exists.
2. The criterion "trafilatura primary, BeautifulSoup fallback" is checked behaviorally only. Engine choice is not observable.
3. The rate-limit tests are timing-based. The 0.3s lower bound has slack, and the upper bound (under 2s) is generous, so flakiness risk is low. Keep an eye on them in slow CI.
4. The user-agent test goes beyond the spec. It is reasonable, but it constrains the implementation. It is acknowledged as "inferred" in the coverage table.
5. The spec still says "Acceptance tests pending independent audit". That note should be updated when this audit is merged. This is housekeeping, not a code change.

## Bug fix assessment

`cleaner.py` now removes `nav`, `footer`, `header`, `script`, `style` and `noscript` with BeautifulSoup before calling trafilatura. The BeautifulSoup fallback reuses the same stripping helper, so both paths are consistent.

- **Correctness:** it fixes the reported leak of nav text on minimal HTML, where trafilatura's heuristics keep short pages mostly intact. The change is about 10 lines, with no data flow change and no new dependencies.
- **Typing:** mypy strict passes. The `type: ignore[import-untyped]` on trafilatura is scoped to that import and predates the fix.
- **Regressions:** none. The full suite, including the Phase 1 tests, passes.

## Risks and concerns

1. **Stripping `<header>` can drop real content.** Some job boards put the title, location, or an intro inside `<header>` within `<article>` or `<main>`. Removing it unconditionally would lose the title, and `parse_posting` derives the title from content. The fixtures do not exercise this, so tests pass. It is a real-world risk, not a blocker. A cheap mitigation would be to strip `header` only when it is not inside `main` or `article`. Add a regression test for it if real postings show the problem.
2. The fallback re-parses the original HTML. That is a minor inefficiency and harmless.
3. `html.parser` is lenient but not perfect on badly broken markup. The malformed-input tests pass.
4. The splitter acceptance threshold is only 80% on fixtures that the Phase 1 or 2 authors designed. Real postings may be messier, which is what the AI fallback is for. It remains unbuilt and untested.

## Required builder items

None. No further builder round is needed.
