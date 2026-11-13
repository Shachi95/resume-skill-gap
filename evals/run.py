"""Evaluation runner. Compares service output against golden files."""

from __future__ import annotations

import os
import sys
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent / "golden"
EVAL_MIN_F1 = float(os.environ.get("EVAL_MIN_F1", "0.80"))


def main() -> None:
    golden_files = sorted(GOLDEN_DIR.glob("*.yaml"))

    if not golden_files:
        print("eval: no reviewed golden files — skipping.")
        return

    import yaml

    reviewed = [f for f in golden_files if _is_reviewed(f, yaml)]

    if not reviewed:
        print("eval: no reviewed golden files — skipping.")
        return

    # Future: compute precision/recall/F1 per skill against service output.
    print(f"eval: {len(reviewed)} golden file(s) found — evaluation not yet implemented.")
    sys.exit(1)


def _is_reviewed(path: Path, yaml: object) -> bool:
    try:
        with open(path) as f:
            data = yaml.safe_load(f)  # type: ignore[attr-defined]
        return bool(data and data.get("reviewed"))
    except Exception:
        return False


if __name__ == "__main__":
    main()
