from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_documentation_lockstep as lockstep  # noqa: E402
import check_publication_contract as contract_check  # noqa: E402


class PublicationMethodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(
            (ROOT / "okf.publication.json").read_text(encoding="utf-8")
        )

    def test_contract_has_valid_local_references(self) -> None:
        self.assertEqual([], contract_check.validate_document(self.contract))

    def test_unknown_command_fails_closed(self) -> None:
        document = copy.deepcopy(self.contract)
        document["planes"][0]["command_ids"].append("not-declared")
        self.assertTrue(
            any(
                "unknown command" in error
                for error in contract_check.validate_document(document)
            )
        )

    def test_plane_cycle_is_rejected(self) -> None:
        document = copy.deepcopy(self.contract)
        document["planes"][0]["depends_on"] = [document["planes"][-1]["id"]]
        self.assertTrue(
            any("cycle" in error for error in contract_check.validate_document(document))
        )

    def test_controlled_change_requires_documentation_and_changelog(self) -> None:
        errors, controlled, documentation = lockstep.lockstep_errors(
            self.contract, {"scripts/build_bundle.py"}
        )
        self.assertEqual(["scripts/build_bundle.py"], controlled)
        self.assertEqual([], documentation)
        self.assertEqual(2, len(errors))

    def test_documentation_and_changelog_satisfy_lockstep(self) -> None:
        errors, _, documentation = lockstep.lockstep_errors(
            self.contract,
            {"scripts/build_bundle.py", "docs/publication-method.md", "CHANGELOG.md"},
        )
        self.assertEqual([], errors)
        self.assertEqual(["docs/publication-method.md"], documentation)

    def test_contract_is_named_in_lockstep_surfaces(self) -> None:
        for path in ("README.md", "AGENTS.md", "CHANGELOG.md"):
            self.assertIn(
                "okf.publication.json",
                (ROOT / path).read_text(encoding="utf-8"),
                path,
            )

    def test_pages_workflow_checks_before_publication_without_rebuilding(self) -> None:
        workflow = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
        self.assertNotIn("run: python scripts/build_bundle.py\n", workflow)
        self.assertIn("run: python scripts/build_bundle.py --check", workflow)
        self.assertIn("cancel-in-progress: ${{ github.event_name == 'pull_request' }}", workflow)
        self.assertIn("group: pages-publication", workflow)
        self.assertGreaterEqual(workflow.count("timeout-minutes:"), 2)
        uses = re.findall(r"uses: ([^\s]+)", workflow)
        self.assertTrue(uses)
        for action in uses:
            self.assertRegex(action, r"@[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
