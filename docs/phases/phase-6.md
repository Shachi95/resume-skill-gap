# Phase 6 — MCP Integration

Goal: Expose the service as an MCP server so the Claude skill can call it for deterministic, reproducible analysis.

Depends on: Phase 5 (report generation, CLI)

## Deliverables

- FastAPI server: wraps the analysis pipeline as HTTP endpoints
- MCP SDK integration: register tools for skill extraction, gap analysis, report generation
- Skill update: modify SKILL.md to call the service via MCP when available, fall back to in-session analysis
- Auth: API key validation for service access
- Docker: Dockerfile + compose for local deployment

## Exit criteria

- `make check` passes (includes `verify-acceptance`)
- `make test-acceptance PHASE=6` passes
- Reviewer verdict: PASS
- MCP server starts and responds to tool calls
- Skill successfully calls service via MCP in a test session
- Service returns identical results whether called via CLI or MCP
- Docker container builds and runs without errors

## Iteration cap: 4
