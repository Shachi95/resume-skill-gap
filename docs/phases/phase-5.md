# Phase 5 — Report Generation

Goal: Generate structured JSON output and an HTML report from scored gaps, with a Typer CLI entry point.

Depends on: Phase 4 (diff, scoring, wording gaps)

## Deliverables

- JSON report: structured output matching the Gap/RankedGap models, machine-readable
- HTML report: template-rendered, theme-aware, responsive, matching the skill's artifact style
- CLI entry point: `skillgap analyze` command via Typer, accepts resume + postings, outputs report
- Output format flag: `--format json|html|both`
- No company names in any output — postings referenced by number and role title only

## Exit criteria

- `make check` passes (includes `verify-acceptance`)
- `make test-acceptance PHASE=5` passes
- Reviewer verdict: PASS
- `skillgap analyze --format json` produces valid JSON matching the schema
- `skillgap analyze --format html` produces a renderable HTML file
- HTML report passes W3C validation (no critical errors)
- CLI help text is accurate and complete

## Iteration cap: 4
