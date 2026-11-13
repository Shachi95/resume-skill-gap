# Phase Workflow Guide

How to run each role for a phase build. Every role runs in a fresh Claude Code session.

## Prerequisites

- `make check` passes on `main` before starting any phase.
- Phase N-1 is merged to `main` (or phase is independent).

## Step 1: Write Acceptance Tests

**Branch:** `phase-N-tests` (from `main`)

```bash
git checkout main && git pull
git checkout -b phase-N-tests
```

**Start the test-writer agent:**
```
claude --agent .claude/agents/test-writer.md "Write acceptance tests for phase N"
```

**Outputs:**
- `service/tests/acceptance/phase_N/test_phase_N.py`
- `service/tests/acceptance/phase_N/LOCK.json`
- `docs/reviews/phase-N-tests.md` (coverage table)

**Verify before merging:**
```bash
make verify-acceptance          # lock is valid
make check                      # no regressions
cd service && uv run pytest tests/acceptance/phase_N/ --collect-only -q   # tests are discovered
```

**Your action:** Review the tests and coverage table. Merge `phase-N-tests` to `main`.

## Step 2: Build the Phase

**Branch:** `phase-N-build` (from `main`, after tests are merged)

```bash
git checkout main && git pull
git checkout -b phase-N-build
```

**Start the builder agent:**
```
claude --agent .claude/agents/builder.md "Implement phase N"
```

**Outputs:**
- Implementation in `service/src/skillgap/`
- Unit tests in `service/tests/unit/`
- Updated `docs/progress.md`

**Verify:**
```bash
make check                      # all checks pass (includes verify-acceptance)
make test-acceptance PHASE=N    # acceptance tests pass
```

## Step 3: Review

**Same branch:** `phase-N-build`

**Start the reviewer agent:**
```
claude --agent .claude/agents/reviewer.md "Review phase N"
```

**Output:**
- `docs/reviews/phase-N-review.md`

**If verdict is CHANGES NEEDED:**
1. Re-run builder: `claude --agent .claude/agents/builder.md "Fix review findings for phase N — see docs/reviews/phase-N-review.md"`
2. Re-run reviewer (max 2 rounds total).

**If verdict is PASS:**
- Do your final review and merge `phase-N-build` to `main`.

## Step 4: Post-merge

```bash
git checkout main && git pull
make check
make eval       # if golden files exist
```

Update `docs/progress.md` if the builder didn't already.

## Quick Reference

| Step | Role | Agent | Branch | Writes to | Reads |
|------|------|-------|--------|-----------|-------|
| 1 | Test writer | `test-writer.md` | `phase-N-tests` | `tests/acceptance/`, `docs/reviews/` | Spec, public interfaces |
| 2 | Builder | `builder.md` | `phase-N-build` | `service/src/`, `tests/unit/` | Spec, acceptance tests, source |
| 3 | Reviewer | `reviewer.md` | `phase-N-build` | `docs/reviews/` | Spec, acceptance tests, diff |
