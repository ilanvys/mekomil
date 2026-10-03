#!/usr/bin/env python3
"""Reject catastrophic refreshes while allowing ordinary upstream changes."""

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "mcp" / "data" / "manifest.json"


def validate_delta(previous, candidate):
    failures = []

    for field in ("org", "maxFileBytes"):
        if previous.get(field) != candidate.get(field):
            failures.append(
                f"{field} changed from {previous.get(field)!r} to {candidate.get(field)!r}"
            )

    for field in ("repos", "skills"):
        old_count = len(previous.get(field, {}))
        new_count = len(candidate.get(field, {}))
        if old_count and new_count * 4 < old_count * 3:
            failures.append(
                f"{field} collapsed from {old_count} to {new_count} "
                "(more than 25% disappeared)"
            )

    return failures


def load_previous():
    result = subprocess.run(
        ["git", "show", "HEAD:mcp/data/manifest.json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def names(value):
    return set(value if isinstance(value, list) else value.keys())


def main():
    try:
        previous = load_previous()
        candidate = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"refresh delta check failed: could not load manifests: {error}", file=sys.stderr)
        return 1

    for field in ("repos", "skills"):
        old_names = names(previous.get(field, {}))
        new_names = names(candidate.get(field, {}))
        print(
            f"{field}: {len(old_names)} -> {len(new_names)} "
            f"(+{len(new_names - old_names)}, -{len(old_names - new_names)})"
        )

    failures = validate_delta(previous, candidate)
    if failures:
        print("refresh delta check failed:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    print("refresh delta check OK: ordinary additions and removals are allowed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
