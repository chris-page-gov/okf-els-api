#!/usr/bin/env python3
"""Require contract-declared documentation and changelog lockstep."""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def path_matches(path: str, pattern: str) -> bool:
    """Match repository paths, allowing ``**`` to span path segments."""

    path_parts = path.split("/")
    pattern_parts = pattern.split("/")

    def match(path_index: int, pattern_index: int) -> bool:
        if pattern_index == len(pattern_parts):
            return path_index == len(path_parts)
        component = pattern_parts[pattern_index]
        if component == "**":
            return match(path_index, pattern_index + 1) or (
                path_index < len(path_parts) and match(path_index + 1, pattern_index)
            )
        return (
            path_index < len(path_parts)
            and fnmatch.fnmatchcase(path_parts[path_index], component)
            and match(path_index + 1, pattern_index + 1)
        )

    return match(0, 0)


def matches_any(path: str, patterns: Iterable[str]) -> bool:
    return any(path_matches(path, pattern) for pattern in patterns)


def changed_files(root: Path, base: str | None) -> set[str]:
    arguments = ["git", "diff", "--name-only"]
    if base:
        arguments.append(base)
    result = subprocess.run(
        arguments,
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    files = {line for line in result.stdout.splitlines() if line}
    if base is None:
        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        files.update(line for line in staged.stdout.splitlines() if line)
        files.update(line for line in untracked.stdout.splitlines() if line)
    return files


def lockstep_errors(
    contract: Mapping[str, Any], changed: Iterable[str]
) -> tuple[list[str], list[str], list[str]]:
    files = set(changed)
    policy = contract["lockstep"]
    controlled = sorted(
        path for path in files if matches_any(path, policy["controlled_paths"])
    )
    if not controlled:
        return [], [], []
    documentation = sorted(
        path for path in files if matches_any(path, policy["documentation_paths"])
    )
    errors: list[str] = []
    if not documentation:
        errors.append(
            "controlled publication files changed without a contract-declared documentation change"
        )
    changelog = policy["changelog_path"]
    if changelog not in files:
        errors.append(f"controlled publication files changed without {changelog}")
    return errors, controlled, documentation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="git diff range to inspect")
    args = parser.parse_args()
    try:
        contract = json.loads((ROOT / "okf.publication.json").read_text(encoding="utf-8"))
        errors, controlled, documentation = lockstep_errors(
            contract, changed_files(ROOT, args.base)
        )
    except (OSError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"documentation lockstep could not be evaluated: {error}", file=sys.stderr)
        return 2
    if errors:
        print("documentation lockstep failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    if not controlled:
        print("documentation lockstep: no controlled publication files changed")
        return 0
    print(
        "documentation lockstep: "
        f"{len(controlled)} controlled file(s), "
        f"{len(documentation)} documentation file(s), changelog updated"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
