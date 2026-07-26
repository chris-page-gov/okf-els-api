from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from okf_v02 import (  # noqa: E402
    OKFConformanceError,
    render_concept,
    render_frontmatter,
    validate_okf_bundle,
    validate_okf_core_bundle,
    validate_okf_producer_profile,
)


class OKFV02ValidatorTests(unittest.TestCase):
    def make_bundle(self, concept: str) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "index.md").write_text(
            render_frontmatter({"okf_version": "0.2"})
            + "\n# Test bundle\n\n* [Concept](concept.md)\n",
            encoding="utf-8",
        )
        (root / "log.md").write_text(
            "# Update log\n\n## 2026-07-25\n* **Creation**: Test.\n",
            encoding="utf-8",
        )
        (root / "concept.md").write_text(concept, encoding="utf-8")
        return root

    def valid_fields(self) -> dict:
        return {
            "type": "Unknown Extension Type",
            "status": "draft",
            "generated": {
                "by": "process:test-build",
                "at": "2026-07-25T12:00:00Z",
            },
            "sources": [
                {
                    "id": "source",
                    "resource": "https://example.test/source",
                }
            ],
            "producer_extension": {"preserved": True},
        }

    def test_unknown_type_and_extension_are_allowed(self) -> None:
        report = validate_okf_bundle(
            self.make_bundle(render_concept(self.valid_fields(), "# Body\n"))
        )
        self.assertEqual(report["conceptCount"], 1)
        self.assertEqual(report["trustTiers"]["unverified"], 1)
        self.assertTrue(report["unknownExtensionFieldsAllowed"])

    def test_core_and_producer_profile_are_reported_separately(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "minimal.md").write_text(
            "---\ntype: \"Minimal Concept\"\n---\n\n# Minimal\n",
            encoding="utf-8",
        )
        core = validate_okf_core_bundle(root)
        self.assertEqual(core["status"], "conformant")
        self.assertEqual(core["conceptCount"], 1)
        self.assertTrue(core["missingIndexesAllowed"])
        with self.assertRaisesRegex(
            OKFConformanceError,
            "root index.md is required by profile",
        ):
            validate_okf_producer_profile(root)

    def test_verified_actor_derives_trust_tier(self) -> None:
        fields = self.valid_fields()
        fields["verified"] = {
            "by": "human:reviewer",
            "at": "2026-07-25T12:30:00Z",
        }
        report = validate_okf_bundle(
            self.make_bundle(render_concept(fields, "# Body\n"))
        )
        self.assertEqual(report["trustTiers"]["humanReviewed"], 1)
        self.assertEqual(report["trustTiers"]["unverified"], 0)

    def test_invalid_actor_cannot_upgrade_trust(self) -> None:
        fields = self.valid_fields()
        fields["verified"] = {
            "by": "reviewed",
            "at": "2026-07-25T12:30:00Z",
        }
        with self.assertRaisesRegex(OKFConformanceError, "actor convention"):
            validate_okf_bundle(
                self.make_bundle(render_concept(fields, "# Body\n"))
            )

    def test_invalid_generated_datetime_is_rejected(self) -> None:
        fields = self.valid_fields()
        fields["generated"]["at"] = "2026-07-25"
        with self.assertRaisesRegex(OKFConformanceError, "ISO 8601 datetime"):
            validate_okf_bundle(
                self.make_bundle(render_concept(fields, "# Body\n"))
            )

    def test_attested_computation_requires_contract(self) -> None:
        fields = self.valid_fields()
        fields["type"] = "Attested Computation"
        with self.assertRaisesRegex(OKFConformanceError, "requires a runtime"):
            validate_okf_bundle(
                self.make_bundle(render_concept(fields, "# Body\n"))
            )

    def test_nested_index_frontmatter_is_rejected(self) -> None:
        root = self.make_bundle(render_concept(self.valid_fields(), "# Body\n"))
        nested = root / "nested"
        nested.mkdir()
        (nested / "index.md").write_text(
            render_frontmatter({"type": "Reference"})
            + "\n# Nested\n\n* [Concept](../concept.md)\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(OKFConformanceError, "must not have frontmatter"):
            validate_okf_bundle(root)

    def test_log_dates_must_be_newest_first(self) -> None:
        root = self.make_bundle(render_concept(self.valid_fields(), "# Body\n"))
        (root / "log.md").write_text(
            "# Update log\n\n"
            "## 2026-07-20\n* First.\n\n"
            "## 2026-07-25\n* Second.\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(OKFConformanceError, "newest first"):
            validate_okf_bundle(root)


if __name__ == "__main__":
    unittest.main()
