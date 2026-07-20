from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "bundle"


def load(relative: str):
    return json.loads((BUNDLE / relative).read_text(encoding="utf-8"))


class BundleTests(unittest.TestCase):
    def test_generated_bundle_is_current(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/build_bundle.py", "--check"],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_declared_counts_and_safety_boundary(self) -> None:
        descriptor = load("okf-explorer.json")
        self.assertEqual(descriptor["counts"]["records"], 18)
        self.assertEqual(descriptor["counts"]["documents"], 6)
        self.assertEqual(descriptor["counts"]["issues"], 9)
        self.assertTrue(descriptor["scope"]["metadata_only"])
        self.assertFalse(descriptor["scope"]["live_execution_included"])
        self.assertFalse(descriptor["scope"]["observations_included"])
        self.assertIn("internal/private", descriptor["warning"])

    def test_manifest_entrypoints_and_chunks_exist(self) -> None:
        descriptor = load("okf-explorer.json")
        manifest = load(descriptor["entrypoints"]["data_manifest"])
        for path in descriptor["entrypoints"].values():
            if path.startswith("https://"):
                continue
            self.assertTrue((BUNDLE / path).is_file(), path)
        for paths in manifest["chunks"].values():
            for path in paths:
                self.assertTrue((BUNDLE / path).is_file(), path)
        self.assertEqual(manifest["counts"]["datasets"], 18)
        self.assertEqual(manifest["counts"]["resources"], 18)

    def test_every_operation_is_non_executing_get(self) -> None:
        operations = load("data/datasets-0.json")
        self.assertEqual(len(operations), 18)
        self.assertEqual(len({operation["id"] for operation in operations}), 18)
        for operation in operations:
            self.assertEqual(operation["method"], "GET")
            self.assertFalse(operation["execution"]["included"])
            self.assertFalse(operation["execution"]["live_verified"])
            self.assertNotIn("observation_values", operation)

    def test_openapi_preserves_known_route_and_parameter_conflicts(self) -> None:
        openapi = load("data/openapi.json")
        self.assertEqual(len(openapi["paths"]), 18)
        source_path = (
            "/api/v1/metadata/indicators/{indicator}/dimensions/{dimension}"
        )
        operation = openapi["paths"][source_path]["get"]
        self.assertEqual(
            operation["x-okf-documented-path"],
            "/api/v1/metadata/indicators/{indicator}/{dimension}",
        )
        issue_ids = {
            issue["id"] for issue in operation["x-okf-documentation-issues"]
        }
        self.assertIn("drift-metadata-dimension-route", issue_ids)
        reverse = openapi["paths"]["/api/v1/geo/reverse"]["get"]
        parameter_names = {row["name"] for row in reverse["parameters"]}
        self.assertNotIn("includeDates", parameter_names)
        self.assertIn(
            "includeDates",
            reverse["x-okf-documented-only-parameters"],
        )

    def test_review_register_has_usage_boundary(self) -> None:
        issues = load("data/review/issues.json")
        by_id = {issue["id"]: issue for issue in issues}
        self.assertEqual(
            by_id["boundary-internal-api"]["severity"],
            "critical-boundary",
        )
        self.assertEqual(
            by_id["drift-geo-includedates"]["kind"],
            "wiki-source-conflict",
        )

    def test_jsonld_models_a_data_service(self) -> None:
        descriptor = load("okf-bundle.jsonld")
        self.assertEqual(descriptor["@type"], "dcat:Catalog")
        services = descriptor["dcat:service"]
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0]["@type"], "dcat:DataService")
        self.assertFalse(services[0]["okf:executionIncluded"])
        self.assertEqual(len(services[0]["hydra:supportedOperation"]), 18)

    def test_checksum_manifest_matches_payloads(self) -> None:
        manifest = load("checksums.json")
        self.assertEqual(manifest["fileCount"], len(manifest["files"]))
        for row in manifest["files"]:
            payload = (BUNDLE / row["path"]).read_bytes()
            self.assertEqual(len(payload), row["bytes"])
            self.assertEqual(hashlib.sha256(payload).hexdigest(), row["sha256"])


if __name__ == "__main__":
    unittest.main()
