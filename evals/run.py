"""Evaluation runner. Compares extraction output against golden files."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

GOLDEN_DIR = Path(__file__).parent / "golden"
FIXTURES_DIR = Path(__file__).parent.parent / "service" / "tests" / "fixtures"
EVAL_MIN_F1 = float(os.environ.get("EVAL_MIN_F1", "0.80"))

sys.path.insert(0, str(Path(__file__).parent.parent / "service" / "src"))


def _load_golden(path: Path) -> dict[str, Any] | None:
    import yaml

    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        if data and data.get("reviewed"):
            return data  # type: ignore[no-any-return]
    except Exception as e:
        print(f"eval: WARNING — skipping {path.name}: {e}", file=sys.stderr)
        return None
    return None


def _read_fixture(golden: dict[str, Any]) -> str:
    fixture_path = FIXTURES_DIR / golden["fixture"]
    return fixture_path.read_text()


def _expected_skills(golden: dict[str, Any]) -> set[str]:
    return {e["skill"] for e in golden.get("expected", [])}


def _precision_recall_f1(expected: set[str], extracted: set[str]) -> dict[str, float]:
    if not expected and not extracted:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not extracted:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    if not expected:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    tp = len(expected & extracted)
    p = tp / len(extracted) if extracted else 0.0
    r = tp / len(expected) if expected else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return {"precision": p, "recall": r, "f1": f1}


def _aggregate(per_file: list[dict[str, float]]) -> dict[str, float]:
    if not per_file:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    n = len(per_file)
    return {
        "precision": sum(pf["precision"] for pf in per_file) / n,
        "recall": sum(pf["recall"] for pf in per_file) / n,
        "f1": sum(pf["f1"] for pf in per_file) / n,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["json", "table"], default="table")
    args = parser.parse_args()
    print(
        "eval: NOTE — LLM path uses a dummy client (no recorded responses); "
        "llm scores are 0, combined = dictionary fallback",
        file=sys.stderr,
    )

    golden_files = sorted(GOLDEN_DIR.glob("*.yaml"))
    if not golden_files:
        print("eval: no golden files found — skipping.")
        return

    goldens: list[tuple[Path, dict[str, Any]]] = []
    for gf in golden_files:
        data = _load_golden(gf)
        if data is not None:
            goldens.append((gf, data))

    if not goldens:
        print("eval: no reviewed golden files — skipping.")
        return

    from skillgap.config import load_config
    from skillgap.extraction import (
        ExtractionConfig,
        extract,
        extract_dictionary,
        extract_verified,
    )
    from skillgap.normalizer import build_lookup, normalize

    alias_config, _ = load_config()
    lookup = build_lookup(alias_config)

    per_file: dict[str, dict[str, float]] = {}
    llm_scores: list[dict[str, float]] = []
    dict_scores: list[dict[str, float]] = []
    combined_scores: list[dict[str, float]] = []

    class _DictOnlyClient:
        """Returns empty result so extract() produces nothing from the LLM path."""

        def extract_skills(self, text: str, kind: str, config: object) -> Any:
            from skillgap.models import ExtractionResult

            return ExtractionResult(skills=())

    dummy_client = _DictOnlyClient()
    fast_config = ExtractionConfig(max_retries=0, base_delay=0.0)

    for gf_path, golden in goldens:
        text = _read_fixture(golden)
        expected = _expected_skills(golden)
        kind = golden.get("kind", "jd")

        llm_result = extract(text, kind, client=dummy_client, config=fast_config)
        llm_canonical: set[str] = set()
        for skill in llm_result.skills:
            resolved = normalize(skill.name, lookup, alias_config)
            llm_canonical.add(resolved.canonical_name if resolved else skill.name.lower())
        llm_scores.append(_precision_recall_f1(expected, llm_canonical))

        dict_skills = extract_dictionary(text, kind, lookup, alias_config)
        dict_canonical = {s.name for s in dict_skills}
        dict_scores.append(_precision_recall_f1(expected, dict_canonical))

        combined_result = extract_verified(
            text,
            kind,
            client=dummy_client,
            config=fast_config,
            lookup=lookup,
            alias_config=alias_config,
            max_attempts=1,
        )
        combined_canonical = {s.canonical_name for s in combined_result.skills}
        file_scores = _precision_recall_f1(expected, combined_canonical)
        combined_scores.append(file_scores)
        per_file[gf_path.name] = file_scores

    results = {
        "llm": _aggregate(llm_scores),
        "dictionary": _aggregate(dict_scores),
        "combined": _aggregate(combined_scores),
    }

    if args.format == "json":
        print(json.dumps({**results, "per_file": per_file}, indent=2))
    else:
        print(f"{'File':<32} {'Precision':>10} {'Recall':>10} {'F1':>10}")
        print("-" * 64)
        for name, s in per_file.items():
            print(f"{name:<32} {s['precision']:>10.4f} {s['recall']:>10.4f} {s['f1']:>10.4f}")
        print()
        print(f"{'Path':<12} {'Precision':>10} {'Recall':>10} {'F1':>10}")
        print("-" * 44)
        for path_name in ("llm", "dictionary", "combined"):
            s = results[path_name]
            print(f"{path_name:<12} {s['precision']:>10.4f} {s['recall']:>10.4f} {s['f1']:>10.4f}")
        print()

    combined_f1 = results["combined"]["f1"]
    if combined_f1 < EVAL_MIN_F1:
        print(
            f"eval: FAIL — combined F1 {combined_f1:.4f} < {EVAL_MIN_F1:.4f}",
            file=sys.stderr,
        )
        sys.exit(1)
    else:
        print(f"eval: PASS — combined F1 {combined_f1:.4f} >= {EVAL_MIN_F1:.4f}", file=sys.stderr)


if __name__ == "__main__":
    main()
