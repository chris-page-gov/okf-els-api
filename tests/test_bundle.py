from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit

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
        self.assertEqual(descriptor["kind"], "okf-large-corpus")
        self.assertEqual(descriptor["version"], "0.3.0")
        self.assertEqual(descriptor["counts"]["records"], 38)
        self.assertEqual(descriptor["counts"]["operations"], 18)
        self.assertEqual(descriptor["counts"]["documents"], 6)
        self.assertEqual(descriptor["counts"]["issues"], 9)
        self.assertTrue(descriptor["scope"]["metadata_only"])
        self.assertFalse(descriptor["scope"]["live_execution_included"])
        self.assertFalse(descriptor["scope"]["observations_included"])
        self.assertIn("internal/private", descriptor["warning"])

    def test_okf_v03_normative_layer_and_trust_boundary(self) -> None:
        descriptor = load("okf-explorer.json")
        report = load("data/standards/okf-core-0.3.json")
        self.assertEqual(descriptor["okf_version"], "0.3")
        self.assertEqual(
            descriptor["profile"],
            "https://chris-page-gov.github.io/okf-explorer/profile/bundle-wiki/v2/",
        )
        self.assertEqual(descriptor["normative_entrypoint"], "index.md")
        self.assertEqual(report["schema"], "okf-els-api.okf-conformance.v3")
        self.assertEqual(report["conceptCount"], 40)
        self.assertEqual(report["trustTiers"]["unverified"], 40)
        self.assertEqual(report["lifecycle"]["draft"], 40)
        self.assertTrue(report["allConceptsRemainUnverified"])
        self.assertEqual(len(report["conceptPaths"]), len(set(report["conceptPaths"])))
        register = json.loads((ROOT / "source/api-register.json").read_text())
        snapshot = json.loads((ROOT / "source/wiki-snapshot.json").read_text())
        original_paths = {
            "knowledge/service.md",
            "knowledge/snapshots/wiki-and-source.md",
            "knowledge/standards/governed-terms.md",
            "knowledge/artifacts/openapi-review.md",
            "knowledge/artifacts/selection-plan.md",
            *(f"knowledge/operations/{row['id']}.md" for row in register["operations"]),
            *(f"knowledge/documents/{row['name']}.md" for row in snapshot["pages"]),
            *(f"knowledge/issues/{row['id']}.md" for row in register["issues"]),
        }
        self.assertEqual(len(original_paths), 38)
        self.assertTrue(original_paths.issubset(report["conceptPaths"]))
        self.assertEqual(
            set(report["conceptPaths"]) - original_paths,
            {
                "knowledge/complex-question-guide.md",
                "knowledge/artifacts/ai-handoff.md",
            },
        )

        root_index = (BUNDLE / "index.md").read_text(encoding="utf-8")
        self.assertTrue(root_index.startswith('---\nokf_version: "0.3"\n---\n'))
        for relative in report["conceptPaths"]:
            concept = (BUNDLE / relative).read_text(encoding="utf-8")
            self.assertTrue(concept.startswith("---\ntype:"), relative)
            self.assertIn('\nstatus: "draft"\n', concept, relative)
            self.assertIn('"by":"process:okf-els-api-build"', concept, relative)
            self.assertNotIn("\nverified:", concept, relative)

    def test_okf_v03_checker_accepts_generated_report(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/check_okf.py"],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("40 concepts", result.stdout)
        self.assertIn("40 explicitly unverified", result.stdout)

    def test_snapshot_and_publication_dates_remain_distinct(self) -> None:
        publication = json.loads(
            (ROOT / "source" / "publication.json").read_text(encoding="utf-8")
        )
        snapshot = json.loads(
            (ROOT / "source" / "wiki-snapshot.json").read_text(encoding="utf-8")
        )
        register = json.loads(
            (ROOT / "source" / "api-register.json").read_text(encoding="utf-8")
        )
        descriptor = load("okf-explorer.json")
        self.assertEqual(descriptor["generated_at"], publication["generatedAt"])
        self.assertNotEqual(
            descriptor["generated_at"],
            snapshot["source"]["commitDate"],
        )
        self.assertNotEqual(
            descriptor["generated_at"],
            register["sourceVerification"]["commitDate"],
        )
        snapshot_concept = (
            BUNDLE / "knowledge" / "snapshots" / "wiki-and-source.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Current live/upstream state: **not checked**", snapshot_concept)
        self.assertIn(snapshot["source"]["commit"], snapshot_concept)
        self.assertIn(register["sourceVerification"]["commit"], snapshot_concept)

    def test_semantic_yamlld_is_byte_equivalent_jsonld(self) -> None:
        jsonld = (BUNDLE / "okf-bundle.jsonld").read_bytes()
        yamlld = (BUNDLE / "okf-bundle.yamlld").read_bytes()
        self.assertEqual(yamlld, jsonld)
        semantic = json.loads(yamlld)
        self.assertEqual(semantic["okf:okfVersion"], "0.3")
        self.assertEqual(semantic["okf:snapshotMode"], "frozen")
        self.assertEqual(semantic["okf:liveStatus"], "not-checked")

    def test_output_guard_refuses_repository_targets(self) -> None:
        for unsafe in (ROOT, ROOT / "scripts" / "generated-bundle"):
            with self.subTest(unsafe=unsafe):
                result = subprocess.run(
                    [
                        sys.executable,
                        "scripts/build_bundle.py",
                        "--output",
                        str(unsafe),
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    check=False,
                    text=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("refusing", result.stderr.lower())

    def test_generated_markdown_internal_links_resolve(self) -> None:
        markdown_link = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
        for source in sorted(BUNDLE.rglob("*.md")):
            for raw_target in markdown_link.findall(
                source.read_text(encoding="utf-8")
            ):
                parsed = urlsplit(raw_target)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                relative = Path(unquote(parsed.path))
                target = (
                    BUNDLE / str(relative).lstrip("/")
                    if parsed.path.startswith("/")
                    else source.parent / relative
                )
                if parsed.path.endswith("/") or target.is_dir():
                    target /= "index.md"
                with self.subTest(
                    source=source.relative_to(BUNDLE),
                    target=raw_target,
                ):
                    self.assertTrue(target.resolve().is_relative_to(BUNDLE.resolve()))
                    self.assertTrue(target.is_file())

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
        self.assertEqual(manifest["counts"]["datasets"], 38)
        self.assertEqual(manifest["counts"]["operations"], 18)
        self.assertEqual(manifest["counts"]["resources"], 18)
        for name, reference in descriptor["entrypoint_integrity"].items():
            payload = (BUNDLE / reference["path"]).read_bytes()
            self.assertEqual(
                hashlib.sha256(payload).hexdigest(),
                reference["sha256"],
                name,
            )
        for name, rows in manifest["shards"].items():
            self.assertEqual(len(rows), 1, name)
            payload = (BUNDLE / rows[0]["path"]).read_bytes()
            self.assertEqual(
                hashlib.sha256(payload).hexdigest(),
                rows[0]["sha256"],
                name,
            )

    def test_pages_landing_and_okf_explorer_link(self) -> None:
        descriptor = load("okf-explorer.json")
        publication = descriptor["publication"]
        self.assertEqual(
            publication["descriptor"],
            "https://chris-page-gov.github.io/okf-els-api/okf-explorer.json",
        )
        self.assertIn(
            "bundle=https%3A%2F%2Fchris-page-gov.github.io%2Fokf-els-api%2Fokf-explorer.json",
            publication["okf_explorer"],
        )
        self.assertIn("%3Fversion%3D0.3.0", publication["okf_explorer"])
        landing = (BUNDLE / "index.html").read_text(encoding="utf-8")
        self.assertIn(publication["okf_explorer"], landing)
        self.assertTrue((BUNDLE / "site.css").is_file())

    def test_complex_question_browser_guide_has_bound_identity_and_sources(self) -> None:
        descriptor = load("okf-explorer.json")
        manifest = load("data/manifest.json")
        self.assertEqual(
            descriptor["@id"],
            "https://chris-page-gov.github.io/okf-els-api/okf-explorer.json",
        )
        self.assertEqual(descriptor["version"], "0.3.0")
        self.assertEqual(descriptor["okf_version"], "0.3")
        self.assertEqual(descriptor["entrypoints"]["complex_question"], "complex-question.html")
        self.assertEqual(manifest["indexes"]["complex_question"], "complex-question.html")
        self.assertIn("complex_question", descriptor["entrypoint_integrity"])
        checksums = load("checksums.json")
        guide_checksum = next(
            item for item in checksums["files"] if item["path"] == "complex-question.html"
        )
        self.assertEqual(
            descriptor["entrypoint_integrity"]["complex_question"]["sha256"],
            guide_checksum["sha256"],
        )
        page = (BUNDLE / "complex-question.html").read_text(encoding="utf-8")
        self.assertIn('aria-label="Evidence stages"', page)
        evidence_nav = page.split('<nav class="evidence-controls"', 1)[1].split("</nav>", 1)[0]
        expected_stages = (
            "knowledge/documents/Requesting-data.md",
            "knowledge/operations/data.md",
            "knowledge/issues/index.md",
            "knowledge/artifacts/selection-plan.md",
        )
        self.assertEqual(evidence_nav.count("<a href="), 4)
        for target in expected_stages:
            self.assertIn(f'href="{target}"', evidence_nav)
        self.assertIn('aria-labelledby="source-title"', page)
        self.assertIn("Worked answer from the pinned records", page)
        self.assertIn("drift-data-hasgeo-default.md", page)
        self.assertIn("includeNames", page)
        self.assertIn("els-wiki-2026-07-20", page)
        data_operation = (BUNDLE / "knowledge/operations/data.md").read_text()
        self.assertIn("# Parameter evidence", data_operation)
        self.assertIn("`time`", data_operation)
        self.assertIn("Recorded default: `latest`", data_operation)
        self.assertIn("geography-level keys or GSS codes", data_operation)
        self.assertIn('id="handoff-prompt" readonly', page)
        self.assertNotIn("knowledge/issues/;", page)
        self.assertIn('src="knowledge/artifacts/complex-question.svg"', page)
        for target in (
            "knowledge/documents/Requesting-data.md",
            "knowledge/operations/data.md",
            "knowledge/issues/index.md",
            "knowledge/artifacts/selection-plan.md",
        ):
            self.assertIn(f'href="{target}"', page)
        for target in (
            "knowledge/issues/drift-data-hasgeo-default.md",
            "knowledge/issues/drift-data-includenames.md",
            "knowledge/issues/gap-data-measure.md",
            "knowledge/issues/gap-response-schemas.md",
            "knowledge/snapshots/wiki-and-source.md",
        ):
            self.assertIn(target, page)
        self.assertIn("@media (max-width: 440px)", (BUNDLE / "site.css").read_text())
        self.assertTrue((BUNDLE / ".nojekyll").is_file())

    def test_okf_explorer_search_index_covers_operations(self) -> None:
        descriptor = load("okf-explorer.json")
        search = load(descriptor["entrypoints"]["search_manifest"])
        self.assertEqual(search["schema"], "okf-static-search.v1")
        self.assertEqual(search["counts"]["documents"], 38)
        self.assertEqual(search["counts"]["postings_shards"], 1)

        lexicon = load(search["entrypoints"]["lexicon"]["_"])
        reverse = next(row for row in lexicon if row["token"] == "reverse")
        postings = load(reverse["postings"])["tokens"]["reverse"]
        results = load(search["entrypoints"]["result_docs"][0])
        matched = [results[row[0]]["name"] for row in postings]
        self.assertIn("geo-reverse", matched)
        data_result = next(row for row in results if row["name"] == "data")
        self.assertEqual(data_result["hydra_type"], "hydra:Operation")
        self.assertIn(
            "openapi:operation-object",
            data_result["standard_term_ids"],
        )

        document_map = load(search["entrypoints"]["doc_map"])
        self.assertEqual(set(document_map), {row["name"] for row in results})
        overview = load("data/overview.json")
        self.assertTrue(overview["recent_datasets"])
        self.assertIn("family", overview["facet_previews"])

    def test_every_operation_is_non_executing_get(self) -> None:
        operations = [
            record
            for record in load("data/datasets-0.json")
            if record["record_type"] == "ELS API operation"
        ]
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
        self.assertEqual(len(services[0]["okf:supportedOperation"]), 18)
        self.assertNotIn("hydra:supportedOperation", services[0])
        for operation in services[0]["okf:supportedOperation"]:
            self.assertIn("okf:requestTemplate", operation)
            self.assertNotIn("hydra:expects", operation)
        self.assertIn("dct:hasPart", descriptor)
        self.assertNotIn("dcat:record", descriptor)
        self.assertEqual(descriptor["okf:okfVersion"], "0.3")
        self.assertEqual(descriptor["okf:liveStatus"], "not-checked")

    def test_governed_terms_cover_generated_standards_usage(self) -> None:
        descriptor = load("okf-explorer.json")
        registry = load(descriptor["entrypoints"]["terms"])
        report = load(descriptor["entrypoints"]["term_validation"])
        self.assertEqual(registry["schema"], "okf-explorer-governed-terms.v1")
        self.assertEqual(registry["counts"]["standardsTerms"], 45)
        self.assertEqual(registry["counts"]["uiTerms"], 15)
        self.assertEqual(report["status"], "conformant")
        self.assertEqual(report["counts"]["unregisteredTerms"], 0)
        self.assertEqual(report["counts"]["unusedStandardsTerms"], 0)
        by_id = {term["id"]: term for term in registry["terms"]}
        self.assertEqual(by_id["hydra:Operation"]["kind"], "class")
        self.assertIn("spec/latest/core", by_id["hydra:Operation"]["provenance"]["resource"])
        self.assertIn(
            "non-executing",
            by_id["hydra:Operation"]["application"].lower(),
        )
        self.assertEqual(
            by_id["openapi:operation-object"]["iri"],
            "https://spec.openapis.org/oas/v3.1.0.html#operation-object",
        )
        self.assertEqual(
            by_id["openapi:operation-object"]["sourceLocator"],
            "operation-object",
        )
        for term in registry["terms"]:
            self.assertEqual(
                {
                    term["validation"]["recognition"],
                    term["validation"]["meaning"],
                    term["validation"]["application"],
                },
                {"validated"},
                term["id"],
            )
        self.assertEqual(
            by_id["ui:access-model"]["helpKey"],
            "access-model",
        )

    def test_every_relationship_endpoint_resolves_to_an_explorer_entity(self) -> None:
        datasets = load("data/datasets-0.json")
        publishers = load("data/publishers-0.json")
        resources = load("data/resources-0.json")
        relationships = load("data/relationships-0.json")
        routes = {
            *[record["route"] for record in datasets],
            *[record["route"] for record in publishers],
            *[record["route"] for record in resources],
        }
        for relationship in relationships:
            self.assertIn(relationship["source"], routes)
            self.assertIn(relationship["target"], routes)
            self.assertIn("predicate", relationship)
            self.assertIn("predicate_term", relationship)
            self.assertIn("basis", relationship)
            self.assertIn("observed_at", relationship)

    def test_explorer_projection_uses_evidence_dates_not_generation_dates(self) -> None:
        descriptor = load("okf-explorer.json")
        operations = [
            record
            for record in load("data/datasets-0.json")
            if record["record_type"] == "ELS API operation"
        ]
        results = load("data/search/results-0.json")
        self.assertTrue(all("metadata_modified" not in row for row in operations))
        self.assertTrue(
            all(row["source_observed_at"] != descriptor["generated_at"] for row in operations)
        )
        self.assertTrue(
            all(row["timestamp"] != descriptor["generated_at"] for row in results)
        )

    def test_descriptor_surfaces_both_semantic_serializations(self) -> None:
        descriptor = load("okf-explorer.json")
        self.assertEqual(descriptor["core_conformance"], "Markdown concept layer")
        self.assertEqual(descriptor["entrypoints"]["markdown_index"], "index.md")
        self.assertEqual(descriptor["semantic_descriptor"], "okf-bundle.yamlld")
        self.assertEqual(
            descriptor["entrypoints"]["semantic_jsonld"],
            "okf-bundle.jsonld",
        )
        self.assertEqual(
            descriptor["entrypoints"]["semantic_yamlld"],
            "okf-bundle.yamlld",
        )

    def test_checksum_manifest_matches_payloads(self) -> None:
        manifest = load("checksums.json")
        self.assertEqual(manifest["fileCount"], len(manifest["files"]))
        for row in manifest["files"]:
            payload = (BUNDLE / row["path"]).read_bytes()
            self.assertEqual(len(payload), row["bytes"])
            self.assertEqual(hashlib.sha256(payload).hexdigest(), row["sha256"])


if __name__ == "__main__":
    unittest.main()
