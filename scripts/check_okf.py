#!/usr/bin/env python3
"""Validate the generated OKF v0.2 Markdown concept layer."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from okf_v02 import OKFConformanceError, validate_okf_bundle

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    try:
        report = validate_okf_bundle(ROOT / "bundle")
    except OKFConformanceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    expected_path = ROOT / "bundle" / "data" / "standards" / "okf-v0.2.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    if report != expected:
        print("error: generated conformance report is out of date", file=sys.stderr)
        return 1
    print(
        "OKF v0.2 conformant: "
        f"{report['conceptCount']} concepts; "
        f"{report['trustTiers']['unverified']} explicitly unverified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
