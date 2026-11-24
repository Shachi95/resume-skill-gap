# Phase 6 Review: MCP Integration

Verdict: **PASS** (with non-blocking risks below)

Verified: `make check` gives 563 passed, 2 skipped, and the acceptance locks are OK. `make test-acceptance PHASE=6` gives 31 passed, none xfailed.

## Summary
The build adds a FastAPI server (`/health`, `/analyze` with X-API-Key auth) and a FastMCP tool `analyze_gaps`. It also adds a Dockerfile, a compose file, three dependencies, and a short SKILL.md section (1b) with a changelog entry. Both entry points call `compute_ranked()`, so results match the CLI.

## 1. Criteria lacking meaningful tests
- "Skill successfully calls service via MCP in a test session" and "Docker container builds and runs" cannot be tested without a network or Docker daemon. The Docker tests only check file contents. This is acceptable, but a human should build and run the image once.
- MCP stdio startup (`main()`) is untested. Tests call the function directly, plus `list_tools` if `mcp` exists.
- The README paste-install block: README has no copy of SKILL.md, so there was nothing to sync.

## 2. Tests that would pass against a broken implementation
- Auth tests accept 401 or 403 and only try one wrong key, so a prefix-match comparison would pass. The implementation uses `hmac.compare_digest`, so this is fine in practice.
- `test_ac_1_8_empty_resume` uses `>=`, so it is loose.
- The no-company test relies on the fixture containing "Zorblatt". If `compute_ranked` leaked evidence text, the test would only catch it when that name appears in the evidence.
- The MCP test accepts any return shape. The tool returns a JSON string, which is fine.
- The `_xf_*` guards would silently xfail if the modules were missing. Here they are present and not xfailed.
- Health and docker tests are shallow, for example EXPOSE alone satisfies the check.

## 3. Scope creep
None of substance. `if __name__ == "__main__"` and `main()` in mcp_server are needed to run it. The `/health` route is covered by the tests. An untracked `service/.coverage` file is not committed, but it should stay ignored.

## 4. Risks for a human
- **Evidence leakage and company names:** the endpoint returns evidence phrases from posting text. Phase 5 handles company names, so I assume `compute_ranked` is already scrubbed.
- **Auth:** the check fails closed if the env var is unset and uses a constant-time compare. There is no rate limiting or request size limit, so large bodies can be sent. The service is intended for local use only.
- **Docker:** `uv:latest` is unpinned. The container runs as root. The HEALTHCHECK has no interval or timeout flags and relies on defaults. There is no `.dockerignore` visible, and `COPY data` assumes the data directory is at `service/data`. The image was not built in this review, so verify with `docker compose build`.
- **Dependency pins:** `fastapi>=0.165.0` and `uvicorn>=0.54.0` have no upper bounds, unlike the other dependencies. `mcp` is pinned `<2`.
- **Synchronous work:** `compute_ranked` is a sync def. FastAPI runs it in a threadpool, so this is fine. If it ever makes AI calls, that would conflict with the "no network in tests" rule. Confirm the pipeline in `compute_ranked` is deterministic and offline.
- **SKILL.md:** the change is minimal, with no personal or role-specific content, and the description is 141 characters or fewer (<200). It still contains "the tool covers technical roles only", which matches the service scope. The compose file uses `${SKILLGAP_API_KEY:?...}`, so there is no baked-in secret. The shipped zip already includes section 1b.
- **CHANGELOG version:** the jump to 7.0.0 while the previous entry was 6.0.0 for Phase 3 is consistent with the earlier numbering, but a human should confirm it.

## Criteria checklist
1. Deliverables: met (FastAPI, MCP tool, skill update, auth, Docker).
2. `make check`: passes.
3. 31/31 acceptance tests pass, no xfails.
4. Typing and structure: good, annotated and mypy strict clean.
5. Security: no secret handling problems, constant-time compare, fail-closed.
6. Server uses `compute_ranked()`: yes.
7. MCP wraps the pipeline: yes, via `generate_json_report(compute_ranked(...))`.
8. Dockerfile: no baked secret, has a healthcheck. Minor hardening is possible (non-root user, pinned uv).
9. SKILL.md: minimal and correct.
10. Edge cases: empty postings and a malformed body are handled (422).

**PASS**
