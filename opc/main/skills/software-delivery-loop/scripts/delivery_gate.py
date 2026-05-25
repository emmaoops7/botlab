#!/usr/bin/env python3
"""Check a software delivery summary for required phase-gate sections."""
from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED = [
    ("Objective", [r"\bobjective\b"]),
    ("Acceptance", [r"\bacceptance\b", r"\bacceptance criteria\b"]),
    ("User path", [r"\buser path\b", r"\bhappy path\b", r"\bcritical path\b"]),
    ("Changed files", [r"\bchanged files\b", r"\bfiles changed\b"]),
    ("Validation evidence", [r"\bvalidation evidence\b", r"\bevidence\b", r"\bvalidation\b"]),
    ("Risks", [r"\brisks?\b"]),
]
RELEASE_OR_ROLLBACK = ("Rollback or Release plan", [r"\brollback\b", r"\brelease plan\b"])


def has_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] in {"-h", "--help"}:
        print("Usage: delivery_gate.py <delivery-summary.md|txt>", file=sys.stderr)
        return 2

    path = Path(argv[1])
    if not path.is_file():
        print(f"Missing file: {path}", file=sys.stderr)
        return 2

    text = path.read_text(encoding="utf-8", errors="replace")
    missing = [name for name, patterns in REQUIRED if not has_any(text, patterns)]
    if not has_any(text, RELEASE_OR_ROLLBACK[1]):
        missing.append(RELEASE_OR_ROLLBACK[0])

    if missing:
        print("Missing required delivery gate items:")
        for item in missing:
            print(f"- {item}")
        return 1

    print("Delivery gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
