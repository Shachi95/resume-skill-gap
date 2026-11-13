# Phase 2 — Posting Fetcher & Splitter

Goal: Fetch job posting HTML, clean it to plain text, and split it into labeled sections (requirements, preferred, responsibilities, etc.).

Depends on: Phase 1 (models, normalizer)

## Deliverables

- HTTP fetcher: httpx-based, respects robots.txt, rate-limited, returns raw HTML
- HTML cleaner: trafilatura for main content extraction, fallback to BeautifulSoup
- Section splitter: regex-first approach using standard headings; AI fallback for non-standard layouts
- Posting parser: orchestrates fetch → clean → split, returns a Posting model
- Recorded HTTP fixtures for tests (no live network calls in CI)

## Exit criteria

- `make check` passes
- Fetcher returns valid HTML for fixture URLs (mocked in tests)
- Cleaner strips boilerplate from all 30 posting fixtures
- Splitter identifies requirements/preferred/responsibilities sections in ≥80% of fixtures
- All network calls are mocked in tests; no live HTTP in CI

## Iteration cap: 5
