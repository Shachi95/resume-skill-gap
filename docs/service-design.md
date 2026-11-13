# Service Design — resume-skill-gap

## 1. Goal

Build a deterministic, reproducible skill-gap analysis pipeline for tech roles. Every step that can be done with code is done with code. AI (an LLM) is used only where human-like reading comprehension is required — extracting skills from unstructured posting text, classifying requirement levels, and identifying wording gaps. All AI output is schema-validated and grounded: every extracted skill must trace to a phrase in the source text.

## 2. Scope

### In scope — three role families

- **Software Engineer** — backend, frontend, full-stack, platform, infrastructure, DevOps, SRE, mobile
- **AI / ML Engineer** — ML engineer, AI engineer, ML infrastructure, applied scientist (engineering-heavy)
- **Forward Deployed / Solutions Engineer** — forward deployed engineer, solutions engineer, solutions architect, customer engineer

### Out of scope

Interns, new-grad / junior roles, engineering managers, recruiters, sales engineers, data scientists (research-heavy), QA / SDET.

## 3. Code vs AI

| Step | Who | Reason |
|------|-----|--------|
| Fetch posting text | Code | HTTP request, HTML parse |
| Clean HTML → plain text | Code | Deterministic tag stripping, boilerplate removal |
| Split into sections (requirements, preferred, responsibilities, etc.) | Code-first, AI fallback | Most postings use standard headings; AI handles non-standard layouts |
| Extract skills from posting | AI | Reading meaning from unstructured text |
| Tag required / preferred / unspecified | AI | Context-dependent; heading alone isn't always enough |
| Normalize synonyms (K8s → Kubernetes) | Code | Lookup in aliases.yaml |
| Deduplicate postings | Code | Text similarity threshold |
| Extract skills from resume | AI | Same as posting extraction |
| Diff resume skills against posting skills | Code | Set operations on canonical names |
| Score and rank gaps | Code | Arithmetic: required 1.0, unspecified 0.75, preferred 0.5 |
| Classify wording gaps | AI | Judging whether resume experience demonstrates a skill without naming it |
| Suggest next steps per gap | AI | Needs knowledge of learning paths, certifications |
| Generate report | Code | Template rendering from structured data |

Every AI step returns a Pydantic model. Validation rejects any output that doesn't parse or whose evidence phrase isn't found in the source text.

## 4. Data models

Fields only — no code in this doc.

### Posting

| Field | Type | Notes |
|-------|------|-------|
| id | str | Auto-generated, stable per URL |
| role_title | str | e.g., "Sr Backend Engineer" |
| url | str or None | Source URL if fetched |
| posted_date | date or None | Parsed from posting if available |
| raw_text | str | Full cleaned text |
| sections | dict[str, str] | Keyed by heading: "requirements", "preferred", "responsibilities", etc. |

Company name is stored only internally for deduplication. It never appears in user-facing output — postings are referenced by number and role title only.

### ExtractedSkill

| Field | Type | Notes |
|-------|------|-------|
| name | str | As written in the posting or resume |
| canonical_name | str | Normalized via aliases.yaml |
| category | enum | tools_software, technical_skills, certs_licenses, domain_knowledge, soft_skills |
| level | enum | required, preferred, unspecified |
| evidence | str | Exact phrase from source text |

### Gap

| Field | Type | Notes |
|-------|------|-------|
| skill | str | Canonical name |
| category | enum | Same as ExtractedSkill |
| gap_type | enum | true, wording, partial |
| score | float | Sum across postings (see Scoring) |
| posting_ids | list[str] | Which postings mention this skill |
| evidence | list[str] | One posting quote per posting_id |

## 5. Scoring

Same weights as the skill:

| Level | Weight |
|-------|--------|
| Required | 1.0 |
| Unspecified | 0.75 |
| Preferred | 0.5 |

One count per distinct posting. Total score = sum of weights across all postings that mention the skill.

Planned for a later phase: recency decay — postings older than ~60 days contribute a decaying fraction of their weight.

## 6. Relationship to the skill

| | Skill (skill/) | Service (service/) |
|-|----------------|-------------------|
| Audience | Anyone, any industry | Tech roles only |
| Runs as | Claude instructions (SKILL.md) | Python code + AI extraction |
| Install | Upload zip or paste into Claude | `uv run` / API |
| Reproducibility | Varies by Claude session | Deterministic pipeline, recorded AI responses |
| Categories | Industry-agnostic (5 categories) | Same 5 categories, tech-weighted |

The skill is the public front end. The service is the reproducible engine. In a later phase the skill may call the service via MCP, so the skill handles UX (artifact rendering, chat summary) while the service handles extraction and scoring.

## 7. Phases

- **Phase 0** — Repo structure, CLAUDE.md rules, this design doc (no code)
- **Phase 1** — Data models (Pydantic), aliases.yaml, roles.yaml, CLI skeleton
- **Phase 2** — Posting fetcher and section splitter (code-first, AI fallback)
- **Phase 3** — AI skill extraction with schema validation and grounding checks
- **Phase 4** — Diff, scoring, wording-gap classification
- **Phase 5** — Report generation (JSON + HTML template)
- **Phase 6** — MCP integration (skill calls service)

Detailed checklist for each phase: see `docs/phase-checklist.md` (to be written at the start of Phase 1).
