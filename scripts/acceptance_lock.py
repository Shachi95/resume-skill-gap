#!/usr/bin/env python3
"""Manage integrity locks for acceptance test directories.

Commands:
    lock N      Regenerate LOCK.json for tests/acceptance/phase_N/
    verify      Check every phase directory against its LOCK.json
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ACCEPTANCE_DIR = REPO_ROOT / "service" / "tests" / "acceptance"
LOCK_FILE = "LOCK.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _phase_dir(n: int) -> Path:
    d = ACCEPTANCE_DIR / f"phase_{n}"
    if not d.is_dir():
        print(f"error: {d} does not exist", file=sys.stderr)
        sys.exit(1)
    return d


def _test_files(phase_dir: Path) -> dict[str, str]:
    """Return {relative_name: sha256} for every file except LOCK.json and __pycache__."""
    result: dict[str, str] = {}
    for f in sorted(phase_dir.iterdir()):
        if f.name == LOCK_FILE or f.name == "__pycache__" or f.is_dir():
            continue
        result[f.name] = _sha256(f)
    return result


def cmd_lock(phase_num: int) -> None:
    phase_dir = _phase_dir(phase_num)
    manifest = _test_files(phase_dir)
    lock_path = phase_dir / LOCK_FILE
    lock_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"locked {len(manifest)} file(s) in {phase_dir.relative_to(REPO_ROOT)}")


def cmd_verify() -> None:
    errors: list[str] = []
    phase_dirs = sorted(ACCEPTANCE_DIR.glob("phase_*"))
    if not phase_dirs:
        print("verify: no phase directories found — nothing to verify")
        return

    for phase_dir in phase_dirs:
        if not phase_dir.is_dir():
            continue
        lock_path = phase_dir / LOCK_FILE
        rel = phase_dir.relative_to(REPO_ROOT)
        if not lock_path.exists():
            continue
        manifest: dict[str, str] = json.loads(lock_path.read_text())
        actual = _test_files(phase_dir)

        for name, expected_hash in manifest.items():
            if name not in actual:
                errors.append(f"{rel}/{name}: REMOVED (expected sha256 {expected_hash[:12]}…)")
            elif actual[name] != expected_hash:
                errors.append(f"{rel}/{name}: MODIFIED (expected {expected_hash[:12]}…, got {actual[name][:12]}…)")

        for name in actual:
            if name not in manifest:
                errors.append(f"{rel}/{name}: ADDED (not in {LOCK_FILE})")

    if errors:
        print("acceptance lock verification FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)
    else:
        print("verify: all acceptance locks OK")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "lock":
        if len(sys.argv) != 3:
            print("usage: acceptance_lock.py lock N", file=sys.stderr)
            sys.exit(1)
        try:
            n = int(sys.argv[2])
        except ValueError:
            print("error: phase number must be an integer", file=sys.stderr)
            sys.exit(1)
        cmd_lock(n)
    elif cmd == "verify":
        cmd_verify()
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
