# resume-skill-gap

Resume-to-posting skill-gap analysis: a Claude skill and a Python service.

## Repo layout
```
skill/                  # the Claude skill
  resume-skill-gap/     # uploadable folder (name matches SKILL.md frontmatter)
    SKILL.md
  tests/                # sample resumes, postings, expected outputs
  dist/                 # built zip (generated; don't edit by hand)
service/                # Python backend
docs/                   # design notes
README.md               # covers both skill and service
```

## Repo-wide rules
- Never include real resumes, names, or contact info anywhere in the repo; test data must be fictional.
- Never instruct Claude (or code) to bypass logins or scrape sites.
- No company names in any user-facing output — reference postings by number and role title only.
- Update CHANGELOG.md for every user-facing change.

## Skill rules (skill/)
- Nothing personal or role-specific in SKILL.md.
- Categories must work outside tech: tools/software, technical skills, certifications/licenses, domain knowledge, soft skills.
- Plain instructions only: no scripts and no package installs.
- The skill is a single SKILL.md with no extra files, so users can install it by pasting into "Write skill instructions."
- Unreachable links are listed for the user to paste.
- Folder name must match the `name` in SKILL.md frontmatter.
- `description` stays under 200 characters and says when to use the skill.
- Instructions are short imperative steps, not essays.
- When SKILL.md changes, also update the paste-install instructions block in README.md so they never differ.

## Service rules (service/)
- Tech-only scope: SWE, AI Engineer, Forward Deployed Engineer, and similar technical roles.
- Role and skill knowledge lives in data files (aliases.yaml, roles.yaml), not code.
- Deterministic steps in code — AI is used only to read meaning from text, not for control flow.
- Every AI output is schema-validated, grounded (evidence phrase must exist in the source text), and normalized before use.
- No AI or network calls in tests or CI; use recorded responses and fixtures.
- Stack: Python 3.12+, uv, Pydantic v2, Typer, pytest + Hypothesis, ruff, mypy strict.
- Architecture source of truth: docs/service-design.md.

## Roles and loop (service/)

Each phase is built by three roles, each running in a **fresh context** (separate subagent or session). No role takes on another role mid-session.

### Roles
1. **Test writer** (`.claude/agents/test-writer.md`): reads only the phase spec and public interfaces; writes acceptance tests in `tests/acceptance/phase_N/`; locks them with `scripts/acceptance_lock.py lock N`. Never writes implementation code.
2. **Builder** (`.claude/agents/builder.md`): implements until `make test-acceptance PHASE=N` and `make check` pass. May add unit tests in `tests/unit/`. May never modify acceptance tests — the lock and CI enforce this.
3. **Reviewer** (`.claude/agents/reviewer.md`): reads the spec, acceptance tests, and diff; writes `docs/reviews/phase-N-review.md` with a PASS or CHANGES NEEDED verdict. Never modifies code or tests.

### Per-phase workflow
1. Test writer writes acceptance tests on branch `phase-N-tests`.
2. I review and approve the tests, merge to `main`.
3. Builder implements on branch `phase-N-build`.
4. Reviewer reviews; if CHANGES NEEDED, builder gets one more round (max 2 rounds total).
5. I do a final review and merge to `main`.

### Rules that apply to all roles
- Read the phase spec (`docs/phases/phase-N.md`) before starting work.
- Never weaken a lint rule, skip a type error, or delete a test to make a check pass.
- If stuck for 3 iterations on the same error, write the details to `docs/blocked.md` and stop.
- After finishing a phase, update `docs/progress.md` and run `make eval` if golden files exist.
- Respect the iteration cap in the phase spec.
- Every function must have type annotations and pass mypy strict.
- No AI or network calls in tests — use recorded responses and fixtures.

## Scoring (don't change without updating README)
required 1.0, unspecified 0.75, preferred 0.5, summed across distinct postings.

## When changing SKILL.md
1. Run all three test cases in `skill/tests/` (engineer, nurse, marketer) and compare against expected outputs.
2. Check that no gap is invented (every skill traces to posting text).
3. Update README if inputs, output format, or scoring changed.
4. Rebuild the zip: `cd skill && zip -r dist/resume-skill-gap.zip resume-skill-gap`
5. Add a line to CHANGELOG.md.
