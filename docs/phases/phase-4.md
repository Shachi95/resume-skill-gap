# Phase 4 — Verified Extraction Pipeline

Goal: Wrap LLM-based skill extraction in a deterministic verification loop that grounds, normalizes, and deduplicates results, with a dictionary-based fallback when the LLM fails.

Depends on: Phase 3 (extractor, grounding), Phase 1 (normalizer, config, models)

## Scope

### In scope

- `extract()` — single-call LLM extraction with DI and configurable model/tokens
- `verify()` — pure deterministic function that grounds, normalizes, deduplicates, and bounds-checks
- `extract_verified()` — retry loop feeding verification errors back to the LLM, with dictionary fallback
- `extract_dictionary()` — regex-based fallback scanning text for known skills and aliases
- `ExtractionConfig` — model name, retry parameters
- `LLMClient` Protocol and `AnthropicLLMClient` — SDK boundary with dependency injection (no monkeypatching in Phase 4 tests)
- Evaluation runner scoring all three extraction paths against golden files
- 15 golden evaluation files (hand-reviewed)

### Out of scope (Phase 5+)

- Near-duplicate skill detection across postings
- Recency weighting / time decay for older postings
- Wording-gap classification (resume demonstrates skill without naming it)
- Diff of resume vs posting skills
- Report generation

## Deliverables

Each deliverable is written as checkable acceptance criteria.

### 1. `extract(text, kind)`

```python
def extract(
    text: str,
    kind: Literal["jd", "resume"],
    *,
    client: LLMClient | None = None,
    config: ExtractionConfig | None = None,
) -> ExtractionResult:
```

- AC-1.1: `kind="jd"` builds the posting extraction prompt; `kind="resume"` builds the resume prompt.
- AC-1.2: Calls `client.extract_skills(text, kind, config)` and returns the validated `ExtractionResult`.
- AC-1.3: Passes `config` to `client.extract_skills()`; `AnthropicLLMClient` uses `config.model` and `config.max_tokens`.
- AC-1.4: When `client is None`, constructs a default `AnthropicLLMClient()`.
- AC-1.5: Returns a Pydantic-validated `ExtractionResult`.
- AC-1.6: On transient errors (429, 5xx), retries with exponential backoff up to `config.max_retries`. After exhausting all retries, raises `LLMExtractionError` with `attempts` set to the number of attempts made, chaining the last underlying error (`raise ... from last_exc`).
- AC-1.7: On non-retryable errors (4xx except 429) or schema-validation failure, the `LLMClient` raises `NonRetryableExtractionError`, which propagates from `extract()`.
- AC-1.8: **Token budget.** Estimates tokens as `len(text) // 4`. If the estimate ≤ `TOKEN_BUDGET` (module constant, 4096), makes exactly 1 `LLMClient` call. If the estimate > `TOKEN_BUDGET`, splits the text into two halves, makes exactly 2 `LLMClient` calls, and merges the resulting skill lists (dedup by canonical name, strongest level wins).

`TOKEN_BUDGET: int = 4096` — module-level constant in `extraction.py`.

`AnthropicLLMClient` — implements `LLMClient`. Wraps `anthropic.Anthropic` (constructed from env when not provided). Uses a single tool named `record_skills`, forced via `tool_choice`, and one user message containing the text. Raises `RetryableExtractionError` on 429/5xx, `NonRetryableExtractionError` on other 4xx or schema failure.

Module: `service/src/skillgap/extraction.py` (new). Imports prompt builders and schema from Phase 3's `extractor.py`.

### 2. `verify(text, result, lookup, config)`

```python
def verify(
    text: str,
    result: ExtractionResult,
    lookup: dict[str, str],
    config: AliasConfig,
    *,
    grounding_threshold: float = 0.85,
) -> VerifyReport:
```

Pure function — no network, no randomness, deterministic for the same inputs.

Checks, in order:

- AC-2.1: **Evidence grounding.** For each skill, the `evidence` field must appear in `text` (case-insensitive substring or fuzzy match above `grounding_threshold`). Failed skills go to `errors` with reason `"evidence_not_in_text"`.
- AC-2.2: **Skill-in-text.** For each remaining skill, the skill `name` or one of its known aliases must appear in `text` (case-insensitive substring). Failed skills go to `errors` with reason `"skill_not_in_text"`.
- AC-2.3: **Normalization.** For each remaining skill, attempt `normalize(name, lookup, config)`. Resolved → `accepted` (with `canonical_name` and dictionary `category`). Unresolved → `candidates`.
- AC-2.4: **Deduplication.** Among `accepted`, group by `canonical_name`. Keep the entry with the strongest `level` (required > unspecified > preferred). Drop others.
- AC-2.5: **Count bounds.** If `len(accepted) < 3`, add error `"too_few_skills"`. If `len(accepted) > 40`, add error `"too_many_skills"`.
- AC-2.6: `ok = len(errors) == 0 and 3 <= len(accepted) <= 40`.

Module: `service/src/skillgap/verification.py` (new). Imports `_is_grounded` from `grounding.py` and `normalize` from `normalizer.py`.

### 3. `extract_verified(text, kind, max_attempts=3)`

```python
def extract_verified(
    text: str,
    kind: Literal["jd", "resume"],
    *,
    client: LLMClient | None = None,
    config: ExtractionConfig | None = None,
    lookup: dict[str, str] | None = None,
    alias_config: AliasConfig | None = None,
    max_attempts: int = 3,
) -> VerifiedExtractionResult:
```

- AC-3.1: Loads `lookup` and `alias_config` via `load_config()` + `build_lookup()` when not provided.
- AC-3.2: For each attempt, calls `extract()` then `verify()`. If `report.ok`, returns immediately with `source="llm"`.
- AC-3.3: When `not report.ok` and attempts remain, builds a retry prompt that includes the specific `report.errors` and the previous extraction, then retries.
- AC-3.4: After the last failed attempt, falls back to `extract_dictionary()` and returns with `source="fallback"` and the last `report.errors` attached.
- AC-3.5: **Never raises** on bad model output. Catches `LLMExtractionError` and `NonRetryableExtractionError` and treats them as failed attempts that trigger fallback.
- AC-3.6: Logs each attempt (attempt number, error count, accepted count) via `logging.getLogger(__name__)`.

Module: `service/src/skillgap/extraction.py`.

### 4. `extract_dictionary(text, kind, lookup, config)`

```python
def extract_dictionary(
    text: str,
    kind: Literal["jd", "resume"],
    lookup: dict[str, str],
    config: AliasConfig,
) -> list[ExtractedSkill]:
```

- AC-4.1: Scans `text` for every canonical skill name and alias in `lookup` using case-insensitive word-boundary regex (`\b`).
- AC-4.2: For each match, constructs an `ExtractedSkill` with `name` = canonical name, `category` from the dictionary, `level` = `unspecified`, `evidence` = the line containing the match.
- AC-4.3: Deduplicates by canonical name; first match wins.
- AC-4.4: Skips skills marked `ambiguous: true` in the dictionary unless the match is inside a list context (comma-separated or bullet list).
- AC-4.5: Returns only skills whose canonical name or alias actually appears in the text.

Module: `service/src/skillgap/extraction.py`.

### 5. `ExtractionConfig`

```python
class ExtractionConfig(BaseModel, frozen=True):
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    max_retries: int = 3
    base_delay: float = 1.0
```

- AC-5.1: Frozen Pydantic model with sensible defaults.
- AC-5.2: `model` and `max_tokens` are passed to `LLMClient.extract_skills()` via `config`; `AnthropicLLMClient` uses them for each SDK call.
- AC-5.3: `max_retries` and `base_delay` control transient-error retries within `extract()`.

Module: `service/src/skillgap/extraction.py`.

### 6. Dependency injection

- AC-6.1: `extract()` and `extract_verified()` accept `client: LLMClient | None`.
- AC-6.2: Phase 4 acceptance tests pass a `FakeLLMClient` — no `monkeypatch.setattr` and no assertions on SDK types or kwargs.
- AC-6.3: Phase 3 acceptance tests are unchanged (continue using monkeypatch on `_call_llm`).

### 7. Evals

- AC-7.1: `evals/run.py` loads all `*.yaml` from `evals/golden/` where `reviewed: true`.
- AC-7.2: For each golden file, runs three extraction paths against the fixture text:
  - LLM path: `extract()` with recorded responses
  - Dictionary path: `extract_dictionary()`
  - Combined path: `extract_verified()` with recorded responses
- AC-7.3: Computes per-file and aggregate precision, recall, F1 on canonical skill names. Accepts `--format json` to output a machine-readable JSON object:
  ```json
  {
    "llm":        {"precision": 0.82, "recall": 0.75, "f1": 0.78},
    "dictionary": {"precision": 0.91, "recall": 0.60, "f1": 0.72},
    "combined":   {"precision": 0.85, "recall": 0.83, "f1": 0.84}
  }
  ```
  Default (no flag) is a human-readable table at the builder's discretion.
- AC-7.4: **DEFERRED — not in scope for this build. Builder must NOT implement baseline or regression logic.** On first run (no `evals/baseline.json`), writes results to `evals/baseline.json`.
- AC-7.5: **DEFERRED — not in scope for this build. Builder must NOT implement baseline or regression logic.** On subsequent runs, loads baseline and reports regressions.
- AC-7.6: Exits with code 1 if aggregate F1 < `EVAL_MIN_F1` (env var, default 0.80).
- AC-7.7: `make eval` invokes `evals/run.py`.

## New models and error classes

All models added to `service/src/skillgap/models.py`. No existing models are modified.
Error classes added to `service/src/skillgap/extraction.py`.

### Error classes

```python
class ExtractionError(Exception):
    """Base class for all extraction errors."""

class LLMExtractionError(ExtractionError):
    """Raised after retry exhaustion in extract().
    
    Has an `attempts: int` attribute and chains the last underlying error:
        raise LLMExtractionError(...) from last_exc
    """
    attempts: int
```

Phase 3's `RetryableExtractionError` and `NonRetryableExtractionError` remain in `extractor.py`, unchanged.

### LLMClient Protocol

```python
class LLMClient(Protocol):
    def extract_skills(
        self, text: str, kind: Literal["jd", "resume"], config: ExtractionConfig
    ) -> ExtractionResult: ...
```

### Models

```python
class ExtractionResult(BaseModel, frozen=True):
    skills: tuple[ExtractedSkill, ...]

class AcceptedSkill(BaseModel, frozen=True):
    skill: ExtractedSkill
    canonical_name: str
    category: Category

class VerifyError(BaseModel, frozen=True):
    skill_name: str
    reason: Literal[
        "evidence_not_in_text",
        "skill_not_in_text",
        "too_few_skills",
        "too_many_skills",
    ]
    detail: str = ""

class VerifyReport(BaseModel, frozen=True):
    ok: bool
    accepted: tuple[AcceptedSkill, ...]
    candidates: tuple[ExtractedSkill, ...]
    errors: tuple[VerifyError, ...]

class VerifiedExtractionResult(BaseModel, frozen=True):
    skills: tuple[AcceptedSkill, ...]
    source: Literal["llm", "fallback"]
    candidates: tuple[ExtractedSkill, ...] = ()
    errors: tuple[VerifyError, ...] = ()
    attempts: int = 1
```

## Hypothesis properties

1. `verify` never accepts a skill whose evidence is absent from the text.
2. `verify` is deterministic: same `(text, result, lookup, config)` → identical `VerifyReport`.
3. `verify` accepted skills are a subset of input skills: `{a.skill for a in report.accepted} ⊆ set(result.skills)`.
4. `verify` never produces duplicate canonical names in `accepted`.
5. `verify` count invariant: every input skill appears in at least one of `accepted`, `candidates`, or `errors`.
6. `verify` `ok` flag is consistent: `ok == (len(errors) == 0 and 3 <= len(accepted) <= 40)`.
7. `extract_verified` never raises (returns `VerifiedExtractionResult` for any input).
8. When `source == "fallback"`, every skill's `canonical_name` exists in the lookup.
9. `extract_dictionary` only returns skills whose name or alias appears in the text.
10. `extract_dictionary` is deterministic and idempotent.

## Exit criteria

- `make check` passes (ruff, mypy strict, pytest, acceptance lock verify).
- `make test-acceptance PHASE=4` passes.
- Reviewer verdict: PASS.
- `make eval` passes with F1 ≥ 0.80 against reviewed golden files.
- `extract_verified()` never raises for any fixture (acceptance test).
- `verify()` is deterministic (Hypothesis property test).
- No `monkeypatch.setattr` in Phase 4 tests (DI used instead).
- No AI or network calls in tests.

## Deferred (not in this build)

AC-7.4 (baseline write) and AC-7.5 (regression detection) are deferred. The builder must NOT implement baseline or regression logic.

Future plan:
- `run.py` will accept `--baseline PATH` (default `evals/baseline.json`) to write/read baseline results.
- `run.py` will accept `--responses DIR` for a directory of recorded LLM responses, so tests can use `tmp_path` and never touch the repo.
- The `--format json` output shape is designed so saving a baseline = writing that JSON to a file, and detecting a regression = comparing two such objects.

## Iteration cap: 25
