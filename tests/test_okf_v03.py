from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from okf_v03 import (  # noqa: E402
    OKFConformanceError,
    render_concept,
    render_frontmatter,
    validate_okf_bundle,
)


class OKFV03ValidatorTests(unittest.TestCase):
    def make_bundle(self, fields: dict) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "index.md").write_text(
            render_frontmatter({"okf_version": "0.3"})
            + "\n# Test bundle\n\n* [Concept](concept.md)\n",
            encoding="utf-8",
        )
        (root / "log.md").write_text(
            "# Update log\n\n## 2026-11-25\n* **Creation**: Test.\n",
            encoding="utf-8",
        )
        (root / "concept.md").write_text(
            render_concept(fields, "# Evidence\n\nA bounded test concept.\n"),
            encoding="utf-8",
        )
        return root

    def valid_fields(self) -> dict:
        return {
            "type": "API Endpoint",
            "title": "Test endpoint",
            "description": "A test endpoint.",
            "status": "draft",
            "generated": {"by": "process:test-build", "at": "2026-11-25T00:00:00Z"},
            "sources": [
                {
                    "id": "source",
                    "resource": "https://example.test/source",
                    "last_modified": "2026-11-20",
                }
            ],
        }

    def test_valid_draft_is_unverified(self) -> None:
        report = validate_okf_bundle(self.make_bundle(self.valid_fields()))
        self.assertEqual(report["conceptCount"], 1)
        self.assertTrue(report["allConceptsRemainUnverified"])
        self.assertEqual(report["lifecycle"]["draft"], 1)

    def test_verified_event_is_rejected_for_frozen_review(self) -> None:
        fields = self.valid_fields()
        fields["verified"] = [{"by": "human:reviewer", "at": "2026-11-25T00:00:00Z"}]
        with self.assertRaisesRegex(OKFConformanceError, "no verification events"):
            validate_okf_bundle(self.make_bundle(fields))

    def test_missing_lifecycle_is_rejected(self) -> None:
        fields = self.valid_fields()
        del fields["status"]
        with self.assertRaisesRegex(OKFConformanceError, "explicit lifecycle"):
            validate_okf_bundle(self.make_bundle(fields))

    def test_invalid_source_date_is_rejected(self) -> None:
        fields = self.valid_fields()
        fields["sources"][0]["last_modified"] = "25 November 2026"
        with self.assertRaisesRegex(OKFConformanceError, "ISO 8601 date"):
            validate_okf_bundle(self.make_bundle(fields))


if __name__ == "__main__":
    unittest.main()
