#!/usr/bin/env python3
"""Build a deterministic, metadata-only OKF bundle for the ELS API wiki."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import shutil
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from okf_v02 import (
    OKFConformanceError,
    OKF_SPEC_COMMIT,
    OKF_SPECIFICATION,
    OKF_VERSION,
    render_concept,
    render_frontmatter,
    validate_okf_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "bundle"
REGISTER_PATH = ROOT / "source" / "api-register.json"
SNAPSHOT_PATH = ROOT / "source" / "wiki-snapshot.json"
PUBLICATION_PATH = ROOT / "source" / "publication.json"
STANDARDS_TERMS_PATH = ROOT / "source" / "standards-terms.json"
PAGES_ROOT = "https://chris-page-gov.github.io/okf-els-api/"
PUBLISHED_DESCRIPTOR = f"{PAGES_ROOT}okf-explorer.json"
EXPLORER_ROOT = "https://chris-page-gov.github.io/okf-explorer/"
BUNDLE_VERSION = "0.2.0"
BUNDLE_LICENSE = "https://github.com/chris-page-gov/okf-els-api/blob/main/LICENSE"
EXPLORER_DESCRIPTOR = f"{PUBLISHED_DESCRIPTOR}?version={BUNDLE_VERSION}"
EXPLORER_URL = f"{EXPLORER_ROOT}?bundle={quote(EXPLORER_DESCRIPTOR, safe='')}"
SEARCH_FIELD_WEIGHTS = {
    "title": 16,
    "route": 15,
    "name": 14,
    "publisher": 8,
    "notes": 8,
    "resources": 7,
    "formats": 6,
    "tags": 5,
}
SEARCH_FIELD_MASKS = {
    field: 1 << index for index, field in enumerate(SEARCH_FIELD_WEIGHTS)
}
SEARCH_STOP_WORDS = {
    "and",
    "for",
    "from",
    "into",
    "of",
    "or",
    "the",
    "to",
    "with",
}


class BuildError(RuntimeError):
    """Raised when source registers or generated output violate the contract."""


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def canonical_json_bytes(value: Any) -> bytes:
    return canonical_json(value).encode("utf-8")


def json_resource_reference(path: str, value: Any) -> dict[str, Any]:
    payload = canonical_json_bytes(value)
    return {
        "path": path,
        "sha256": digest_bytes(payload),
    }


def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BuildError(f"Unable to read JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise BuildError(f"Expected a JSON object: {path}")
    return value


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_json(value: Any) -> str:
    return digest_bytes(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )


_COMPACT_TERM = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):([A-Za-z][A-Za-z0-9._-]*)$")


def _term_occurrences(
    value: Any,
    *,
    artifact: str,
    prefixes: set[str],
    path: str = "$",
) -> list[dict[str, str]]:
    occurrences: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            match = _COMPACT_TERM.fullmatch(str(key))
            if match and match.group(1) in prefixes:
                occurrences.append(
                    {
                        "artifact": artifact,
                        "path": f"{path}.{key}",
                        "role": "key",
                        "term": str(key),
                    }
                )
            child_path = f"{path}.{key}"
            if key == "standard_term_ids" and isinstance(child, list):
                for index, term in enumerate(child):
                    occurrences.append(
                        {
                            "artifact": artifact,
                            "path": f"{child_path}[{index}]",
                            "role": "declared-term",
                            "term": str(term),
                        }
                    )
            else:
                occurrences.extend(
                    _term_occurrences(
                        child,
                        artifact=artifact,
                        prefixes=prefixes,
                        path=child_path,
                    )
                )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            occurrences.extend(
                _term_occurrences(
                    child,
                    artifact=artifact,
                    prefixes=prefixes,
                    path=f"{path}[{index}]",
                )
            )
    elif isinstance(value, str):
        match = _COMPACT_TERM.fullmatch(value)
        if match and match.group(1) in prefixes:
            occurrences.append(
                {
                    "artifact": artifact,
                    "path": path,
                    "role": "value",
                    "term": value,
                }
            )
    return occurrences


def governed_terms(
    source: dict[str, Any],
    *,
    snapshot_id: str,
    generated_at: str,
    artifacts: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build and validate the governed standards/UI term datapack.

    This is a closed-world publication check. It confirms that each emitted
    compact term is registered, expands through the declared namespace, has
    authoritative provenance, and carries a reviewed bounded-use statement.
    It does not claim that a live vocabulary endpoint was queried.
    """

    if source.get("schema") != "okf-els-api.standards-terms-source.v1":
        raise BuildError("Unsupported standards-term source schema")
    vocabularies = source.get("vocabularies")
    terms = source.get("terms")
    ui_terms = source.get("uiTerms")
    if not isinstance(vocabularies, list) or not isinstance(terms, list):
        raise BuildError("Standards-term source requires vocabularies and terms")
    if not isinstance(ui_terms, list):
        raise BuildError("Standards-term source requires uiTerms")
    review = source.get("review")
    if not isinstance(review, dict):
        raise BuildError("Standards-term source requires a review record")
    for required in ("method", "checkedBy", "checkedAt", "scope"):
        if not str(review.get(required) or "").strip():
            raise BuildError(f"Standards-term review requires {required}")
    if review.get("applicationStatus") != "validated-for-bounded-use":
        raise BuildError("Standards-term review must validate bounded application")
    if not isinstance(review.get("liveLookupPerformed"), bool):
        raise BuildError("Standards-term review must record whether live lookup occurred")

    vocabulary_by_id: dict[str, dict[str, Any]] = {}
    vocabulary_by_prefix: dict[str, dict[str, Any]] = {}
    for vocabulary in vocabularies:
        if not isinstance(vocabulary, dict):
            raise BuildError("Every standards vocabulary must be an object")
        vocabulary_id = str(vocabulary.get("id") or "")
        prefix = str(vocabulary.get("prefix") or "")
        namespace = str(vocabulary.get("namespace") or "")
        source_url = str(vocabulary.get("source") or "")
        if not vocabulary_id or not prefix or not namespace or not source_url:
            raise BuildError("Standards vocabulary id, prefix, namespace and source are required")
        if vocabulary_id in vocabulary_by_id or prefix in vocabulary_by_prefix:
            raise BuildError(f"Duplicate standards vocabulary or prefix: {vocabulary_id}")
        vocabulary_by_id[vocabulary_id] = vocabulary
        vocabulary_by_prefix[prefix] = vocabulary

    public_terms: list[dict[str, Any]] = []
    term_by_id: dict[str, dict[str, Any]] = {}
    for term in terms:
        if not isinstance(term, dict):
            raise BuildError("Every governed standards term must be an object")
        term_id = str(term.get("id") or "")
        vocabulary_id = str(term.get("vocabulary") or "")
        match = _COMPACT_TERM.fullmatch(term_id)
        vocabulary = vocabulary_by_id.get(vocabulary_id)
        if not match or vocabulary is None:
            raise BuildError(f"Invalid governed term identifier or vocabulary: {term_id}")
        if match.group(1) != vocabulary["prefix"]:
            raise BuildError(f"Governed term prefix does not match vocabulary: {term_id}")
        if term_id in term_by_id:
            raise BuildError(f"Duplicate governed term: {term_id}")
        if term.get("status") != "validated":
            raise BuildError(f"Used governed term is not application-validated: {term_id}")
        for required in ("label", "definition", "application", "kind"):
            if not str(term.get(required) or "").strip():
                raise BuildError(f"Governed term {term_id} requires {required}")
        if term["kind"] == "specification-object":
            source_locator = str(term.get("sourceLocator") or "")
            if source_locator != match.group(2):
                raise BuildError(
                    f"Specification-object term {term_id} must use its authoritative "
                    "source locator as the compact local name"
                )
        row = dict(term)
        row["iri"] = f"{vocabulary['namespace']}{match.group(2)}"
        row["provenance"] = {
            "vocabulary": vocabulary_id,
            "resource": vocabulary["source"],
            "version": vocabulary["version"],
        }
        row["validation"] = {
            "recognition": "validated",
            "meaning": "validated",
            "application": "validated",
            "method": review["method"],
            "checkedBy": review["checkedBy"],
            "checkedAt": review["checkedAt"],
        }
        public_terms.append(row)
        term_by_id[term_id] = row

    public_ui_terms: list[dict[str, Any]] = []
    for term in ui_terms:
        if not isinstance(term, dict):
            raise BuildError("Every governed UI term must be an object")
        term_id = str(term.get("id") or "")
        match = _COMPACT_TERM.fullmatch(term_id)
        if not match or match.group(1) != "ui":
            raise BuildError(f"Invalid governed UI term identifier: {term_id}")
        if term_id in term_by_id:
            raise BuildError(f"Duplicate governed term: {term_id}")
        for required in ("label", "definition", "helpKey"):
            if not str(term.get(required) or "").strip():
                raise BuildError(f"Governed UI term {term_id} requires {required}")
        vocabulary = vocabulary_by_prefix["ui"]
        row = {
            **term,
            "application": f"Explorer help key {term['helpKey']}",
            "iri": f"{vocabulary['namespace']}{match.group(2)}",
            "kind": "ui-term",
            "provenance": {
                "vocabulary": vocabulary["id"],
                "resource": vocabulary["source"],
                "version": vocabulary["version"],
            },
            "validation": {
                "recognition": "validated",
                "meaning": "validated",
                "application": "validated",
                "method": review["method"],
                "checkedBy": review["checkedBy"],
                "checkedAt": review["checkedAt"],
            },
            "status": "validated",
            "vocabulary": vocabulary["id"],
        }
        public_ui_terms.append(row)
        term_by_id[term_id] = row

    prefixes = set(vocabulary_by_prefix)
    occurrences = [
        occurrence
        for artifact, value in artifacts.items()
        for occurrence in _term_occurrences(
            value,
            artifact=artifact,
            prefixes=prefixes,
        )
    ]
    unregistered = sorted(
        {
            occurrence["term"]
            for occurrence in occurrences
            if occurrence["term"] not in term_by_id
        }
    )
    if unregistered:
        raise BuildError(
            "Generated artifacts use unregistered governed terms: "
            + ", ".join(unregistered)
        )

    occurrences_by_term: dict[str, list[dict[str, str]]] = defaultdict(list)
    for occurrence in occurrences:
        occurrences_by_term[occurrence["term"]].append(occurrence)
    unused = sorted(
        term["id"]
        for term in public_terms
        if not occurrences_by_term.get(term["id"])
    )
    if unused:
        raise BuildError(
            "Governed standards terms are not used by generated artifacts: "
            + ", ".join(unused)
        )

    for term in [*public_terms, *public_ui_terms]:
        rows = occurrences_by_term.get(term["id"], [])
        grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            grouped[row["artifact"]].append(row)
        term["usage"] = [
            {
                "artifact": artifact,
                "occurrences": len(artifact_rows),
                "samplePaths": [
                    item["path"] for item in artifact_rows[:5]
                ],
            }
            for artifact, artifact_rows in sorted(grouped.items())
        ]

    review = dict(review)
    registry = {
        "schema": "okf-explorer-governed-terms.v1",
        "snapshot": snapshot_id,
        "generated_at": generated_at,
        "title": "ELS OKF governed metadata terms",
        "description": (
            "Authoritative provenance, bounded-use meaning and validation state "
            "for standards and reader-facing terms emitted by this bundle."
        ),
        "review": review,
        "vocabularies": vocabularies,
        "terms": [*public_terms, *public_ui_terms],
        "counts": {
            "vocabularies": len(vocabularies),
            "standardsTerms": len(public_terms),
            "uiTerms": len(public_ui_terms),
            "usedStandardsTerms": len(occurrences_by_term),
            "occurrences": len(occurrences),
        },
    }
    report = {
        "schema": "okf-explorer-governed-term-validation.v1",
        "snapshot": snapshot_id,
        "generated_at": generated_at,
        "status": "conformant",
        "scope": review["scope"],
        "method": review["method"],
        "checkedBy": review["checkedBy"],
        "checkedAt": review["checkedAt"],
        "liveLookupPerformed": review["liveLookupPerformed"],
        "checks": {
            "uniqueIdentifiers": "passed",
            "termRecognition": "passed",
            "namespaceExpansion": "passed",
            "authoritativeProvenance": "passed",
            "termKindDeclared": "passed",
            "meaningReviewed": "passed",
            "boundedApplicationReviewed": "passed",
            "generatedTermCoverage": "passed",
        },
        "counts": {
            "registeredTerms": len(term_by_id),
            "usedTerms": len(occurrences_by_term),
            "occurrences": len(occurrences),
            "unregisteredTerms": 0,
            "unusedStandardsTerms": 0,
            "pendingApplicationReviews": 0,
        },
        "unregisteredTerms": [],
        "unusedStandardsTerms": [],
        "pendingApplicationReviews": [],
        "limitations": [
            "This is a deterministic closed-world publication check against the checked-in curated register.",
            "It does not perform a live vocabulary lookup or claim human review.",
            "A validated mapping applies only to the artifact locations and bounded meanings recorded in the registry.",
        ],
    }
    return registry, report


class Writer:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.paths: set[Path] = set()

    def write_json(self, relative: str | Path, value: Any) -> None:
        self.write_text(relative, canonical_json(value))

    def write_text(self, relative: str | Path, value: str) -> None:
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise BuildError(f"Unsafe output path: {path}")
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value, encoding="utf-8", newline="\n")
        self.paths.add(path)

    def checksum_manifest(self) -> dict[str, Any]:
        files: list[dict[str, Any]] = []
        for path in sorted(self.paths, key=lambda item: item.as_posix()):
            payload = (self.root / path).read_bytes()
            files.append(
                {
                    "path": path.as_posix(),
                    "bytes": len(payload),
                    "sha256": digest_bytes(payload),
                }
            )
        return {
            "schema": "okf-els-api.checksums.v1",
            "algorithm": "sha256",
            "fileCount": len(files),
            "files": files,
            "rootSha256": digest_json(
                [{"path": row["path"], "sha256": row["sha256"]} for row in files]
            ),
        }


def wiki_url(page: str) -> str:
    root = "https://github.com/ONSdigital/explore-local-statistics-app/wiki"
    return root if page == "Home" else f"{root}/{page}"


def source_url(register: dict[str, Any], source_path: str) -> str:
    commit = register["sourceVerification"]["commit"]
    return (
        "https://github.com/ONSdigital/explore-local-statistics-app/blob/"
        f"{commit}/{quote(source_path, safe='/().[]+')}"
    )


def validate_inputs(register: dict[str, Any], snapshot: dict[str, Any]) -> None:
    if register.get("schema") != "okf-els-api.register.v1":
        raise BuildError("Unsupported API register schema")
    if snapshot.get("schema") != "okf-els-api.wiki-snapshot.v1":
        raise BuildError("Unsupported wiki snapshot schema")
    if snapshot.get("metadataOnly") is not True:
        raise BuildError("Wiki snapshot must assert metadataOnly=true")
    if snapshot.get("observationsIncluded") is not False:
        raise BuildError("Wiki snapshot must assert observationsIncluded=false")
    if register.get("method") != "GET":
        raise BuildError("Only a read-only GET API register is supported")
    if register.get("policy", {}).get("liveExecutionIncluded") is not False:
        raise BuildError("The bundle must not include live execution")
    operations = register.get("operations")
    if not isinstance(operations, list) or not operations:
        raise BuildError("API register has no operations")
    operation_ids = [row.get("id") for row in operations if isinstance(row, dict)]
    if len(operation_ids) != len(set(operation_ids)):
        raise BuildError("API operation identifiers must be unique")
    page_names = {page.get("name") for page in snapshot.get("pages", [])}
    if len(page_names) != snapshot["denominator"]["pageCount"]:
        raise BuildError("Wiki page denominator does not match the page manifest")
    issue_ids = {issue.get("id") for issue in register.get("issues", [])}
    parameter_ids = set(register.get("parameters", {}))
    format_ids = set(register.get("formats", {}))
    for operation in operations:
        if operation.get("wiki") not in page_names:
            raise BuildError(f"Unknown wiki page on operation {operation.get('id')}")
        unknown_parameters = set(operation.get("queryParameters", [])) - parameter_ids
        unknown_parameters |= set(operation.get("documentedOnlyParameters", [])) - parameter_ids
        unknown_parameters |= set(operation.get("sourceOnlyParameters", [])) - parameter_ids
        if unknown_parameters:
            raise BuildError(
                f"Unknown parameters on operation {operation.get('id')}: "
                f"{sorted(unknown_parameters)}"
            )
        unknown_formats = set(operation.get("formats", [])) - format_ids
        if unknown_formats:
            raise BuildError(
                f"Unknown formats on operation {operation.get('id')}: {sorted(unknown_formats)}"
            )
        unknown_issues = set(operation.get("issueIds", [])) - issue_ids
        if unknown_issues:
            raise BuildError(
                f"Unknown issues on operation {operation.get('id')}: {sorted(unknown_issues)}"
            )


def validate_publication(publication: dict[str, Any]) -> None:
    if publication.get("schema") != "okf-els-api.publication.v1":
        raise BuildError("Unsupported publication schema")
    if publication.get("generatedBy") != "process:okf-els-api-build":
        raise BuildError("Publication must identify the deterministic build process")
    specification = publication.get("okfSpecification")
    if not isinstance(specification, dict):
        raise BuildError("Publication has no OKF specification pin")
    if specification.get("version") != OKF_VERSION:
        raise BuildError("Publication must target OKF v0.2")
    if specification.get("commit") != OKF_SPEC_COMMIT:
        raise BuildError("Publication must pin the reviewed OKF v0.2 commit")
    if specification.get("resource") != OKF_SPECIFICATION:
        raise BuildError("Publication must use the pinned OKF v0.2 specification")
    generated_at = publication.get("generatedAt")
    if not isinstance(generated_at, str):
        raise BuildError("Publication generatedAt must be an ISO 8601 datetime")
    try:
        parsed = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BuildError(
            "Publication generatedAt must be an ISO 8601 datetime"
        ) from exc
    if parsed.tzinfo is None:
        raise BuildError("Publication generatedAt must include a timezone")


def parameter_record(
    name: str,
    definition: dict[str, Any],
    operation: dict[str, Any],
) -> dict[str, Any]:
    row = {
        "name": name,
        "in": definition["in"],
        "required": name in operation.get("requiredQueryParameters", []),
        "schema": {
            key: definition[key]
            for key in ("type", "enum", "minimum", "maximum")
            if key in definition
        },
        "description": definition["description"],
        "evidence": "wiki-and-source",
    }
    if name in operation.get("defaults", {}):
        row["default"] = operation["defaults"][name]
    if name in operation.get("sourceOnlyParameters", []):
        row["evidence"] = "source-only"
    if definition.get("dynamic"):
        row["dynamic"] = True
    return row


def operation_standards_alignment() -> dict[str, Any]:
    return {
        "claim": "standards-alignable-not-conformant",
        "profiles": ["DCAT 3", "Hydra Core", "OpenAPI 3.1.0"],
        "dcat": {
            "term": None,
            "parent_term": "dcat:DataService",
            "export_status": "roll-up-to-parent-service",
            "required_missing": [],
            "explanation": (
                "DCAT models the parent API as dcat:DataService; an individual "
                "HTTP operation has no direct DCAT class in this projection."
            ),
        },
        "hydra": {
            "term": "hydra:Operation",
            "export_status": "bounded-operation-description",
            "required_missing": ["returns", "status codes", "response class"],
        },
        "openapi": {
            "term": "OpenAPI Operation Object",
            "term_id": "openapi:operation-object",
            "export_status": "operation-fragment",
            "required_missing": [
                "complete response schemas",
                "common error schema",
                "upstream security scheme",
            ],
        },
        "notes": [
            "The Hydra and OpenAPI mappings describe a generated bounded review projection, not an upstream contract.",
            "Evidence confidence is independent from OKF verified trust and live deployment status.",
        ],
    }


def operation_records(
    register: dict[str, Any],
    snapshot: dict[str, Any],
    generated_at: str,
) -> list[dict[str, Any]]:
    issue_lookup = {issue["id"]: issue for issue in register["issues"]}
    records: list[dict[str, Any]] = []
    for operation in register["operations"]:
        parameters = [
            parameter_record(name, register["parameters"][name], operation)
            for name in operation.get("queryParameters", [])
        ]
        path_parameters = [
            {
                "name": name,
                "in": "path",
                "required": True,
                "description": definition.get("description", f"Path value for {name}."),
                "schema": {
                    key: definition[key]
                    for key in ("type", "enum", "minimum", "maximum")
                    if key in definition
                },
                "evidence": "wiki-and-source",
            }
            for name, definition in operation.get("pathParameters", {}).items()
        ]
        issue_rows = [issue_lookup[issue_id] for issue_id in operation.get("issueIds", [])]
        path = operation["path"]
        record_id = f"els-api:operation:{operation['id']}"
        records.append(
            {
                "id": record_id,
                "record_id": record_id,
                "native_id": operation["id"],
                "name": operation["id"],
                "title": operation["title"],
                "notes": operation["summary"],
                "description": operation["summary"],
                "record_type": "ELS API operation",
                "type": "API Endpoint",
                "concept_id": f"knowledge/operations/{operation['id']}.md",
                "dcat_type": None,
                "hydra_type": "hydra:Operation",
                "openapi_type": "OpenAPI Operation Object",
                "standard_term_ids": [
                    "dcat:DataService",
                    "hydra:Operation",
                    "openapi:operation-object",
                ],
                "standards_alignment": operation_standards_alignment(),
                "source_surface": "els-api-wiki",
                "source_adapter": "wiki-and-static-source-review",
                "source_tier": "wiki-and-pinned-static-source",
                "confidence": "static-source-observed",
                "publisher": "office-for-national-statistics",
                "publisher_title": "Office for National Statistics",
                "route": f"operation/{operation['id']}",
                "open": f"operation/{operation['id']}",
                "url": f"{register['baseUrl']}{path}",
                "documentation": wiki_url(operation["wiki"]),
                "host": "www.ons.gov.uk",
                "formats": operation["formats"],
                "protocol": ["HTTPS", "REST/HTTP"],
                "topics": [operation["family"]],
                "tags": [
                    "api",
                    "get",
                    operation["family"],
                    register["status"],
                ],
                "state": register["status"],
                "lifecycle_status": "draft",
                "visibility": "internal-private",
                "access_model": "not-documented",
                "contract_status": "generated-review-draft-not-upstream-contract",
                "private": True,
                "isopen": False,
                "method": "GET",
                "path_template": path,
                "documented_path_template": operation["documentedPath"],
                "parameters": path_parameters + parameters,
                "documented_only_parameters": operation.get("documentedOnlyParameters", []),
                "source_only_parameters": operation.get("sourceOnlyParameters", []),
                "issue_count": len(issue_rows),
                "issues": [
                    {
                        "id": issue["id"],
                        "severity": issue["severity"],
                        "title": issue["title"],
                    }
                    for issue in issue_rows
                ],
                "privacy_note": operation.get("privacyNote", ""),
                "execution": {
                    "included": False,
                    "live_verified": False,
                    "requires_explicit_client_action": True,
                    "warning": register["policy"]["warning"],
                },
                "documentation_evidence": {
                    "wiki": wiki_url(operation["wiki"]),
                    "wiki_commit": snapshot["source"]["commit"],
                    "source_handler": source_url(register, operation["sourcePath"]),
                    "source_commit": register["sourceVerification"]["commit"],
                    "verification_mode": register["sourceVerification"]["mode"],
                },
                "evidence_availability": {
                    "present": [
                        "method",
                        "path",
                        "summary",
                        "parameter names",
                        "selected defaults",
                        "representation names",
                        "source provenance",
                    ],
                    "absent": [
                        "complete response schemas",
                        "common error schema",
                        "live deployment verification",
                        "stability guarantee",
                        "compatibility and deprecation policy",
                    ],
                    "service_quality_evaluated": False,
                },
                "license_id": "mit-associated-repository",
                "license_title": "MIT evidence from associated application repository",
                "license_source_id": (
                    f"{register['sourceVerification']['repository']}/blob/"
                    f"{register['sourceVerification']['commit']}/LICENSE.md"
                ),
                "license_source_title": (
                    "Associated application repository licence; the wiki has no "
                    "separate licence file"
                ),
                "license_basis": "associated-repository-evidence-not-wiki-license",
                "source_observed_at": snapshot["retrievedAt"],
                "provenance": {
                    "schema": "okf-provenance.v1",
                    "snapshot_id": snapshot["snapshotId"],
                    "retrieved_at": snapshot["retrievedAt"],
                    "source_url": wiki_url(operation["wiki"]),
                    "source_commit": snapshot["source"]["commit"],
                    "source_handler_url": source_url(register, operation["sourcePath"]),
                    "source_handler_commit": register["sourceVerification"]["commit"],
                },
            }
        )
    return records


def document_records(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": f"els-api:document:{page['name']}",
            "name": page["name"],
            "title": page["name"].replace("-", " "),
            "notes": "Pinned wiki source-document metadata.",
            "description": "Metadata for one page in the frozen ELS API wiki snapshot.",
            "record_type": "Wiki documentation page",
            "type": "Reference",
            "concept_id": f"knowledge/documents/{page['name']}.md",
            "route": f"document/{page['name']}",
            "open": f"document/{page['name']}",
            "url": page["url"],
            "documentation": page["url"],
            "file": page["file"],
            "sha256": page["sha256"],
            "lines": page["lines"],
            "bytes": page["bytes"],
            "source_commit": snapshot["source"]["commit"],
            "retrieved_at": snapshot["retrievedAt"],
            "source_observed_at": snapshot["retrievedAt"],
            "source_surface": "els-api-wiki",
            "source_adapter": "pinned-wiki-snapshot",
            "source_tier": "pinned-source-document",
            "confidence": "source-observed",
            "publisher": "office-for-national-statistics",
            "publisher_title": "Office for National Statistics",
            "formats": ["markdown"],
            "protocol": ["HTTPS"],
            "topics": ["documentation"],
            "tags": ["wiki", "source-document", "snapshot"],
            "state": "bounded-review-draft",
            "lifecycle_status": "draft",
            "visibility": "public-source-document",
            "access_model": "anonymous-web",
            "contract_status": "source-document",
            "private": False,
            "isopen": False,
            "issues": [],
            "standard_term_ids": ["foaf:Document"],
            "license_evidence": snapshot["licenceEvidence"],
        }
        for page in snapshot["pages"]
    ]


def explorer_concept_records(
    register: dict[str, Any],
    snapshot: dict[str, Any],
    operations: list[dict[str, Any]],
    documents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    project_publisher = "okf-els-api-project"
    project_title = "OKF ELS API project"
    common_project = {
        "publisher": project_publisher,
        "publisher_title": project_title,
        "source_surface": "bounded-wiki-and-source-review",
        "source_adapter": "okf-els-api-build",
        "source_tier": "generated-from-pinned-evidence",
        "confidence": "bounded-review",
        "formats": ["markdown"],
        "protocol": ["HTTPS"],
        "state": "bounded-review-draft",
        "lifecycle_status": "draft",
        "visibility": "public-metadata-bundle",
        "access_model": "anonymous-web",
        "private": False,
        "isopen": True,
        "source_observed_at": snapshot["retrievedAt"],
        "issues": [],
        "standard_term_ids": [],
    }
    service = {
        "id": "els-api:service",
        "record_id": "els-api:service",
        "native_id": "els-api",
        "name": "els-api-service",
        "title": register["title"],
        "notes": register["description"],
        "description": register["description"],
        "record_type": "API Service",
        "type": "API Service",
        "concept_id": "knowledge/service.md",
        "route": "service/els-api",
        "open": "service/els-api",
        "url": register["baseUrl"],
        "documentation": snapshot["source"]["url"],
        "host": "www.ons.gov.uk",
        "publisher": "office-for-national-statistics",
        "publisher_title": "Office for National Statistics",
        "source_surface": "els-api-wiki",
        "source_adapter": "wiki-and-static-source-review",
        "source_tier": "wiki-and-pinned-static-source",
        "confidence": "static-source-observed",
        "formats": ["application-json"],
        "protocol": ["HTTPS", "REST/HTTP"],
        "topics": ["service"],
        "tags": ["api", "ons", "internal-private", "metadata-only"],
        "state": register["status"],
        "lifecycle_status": "draft",
        "visibility": "internal-private",
        "access_model": "not-documented",
        "contract_status": "generated-review-draft-not-upstream-contract",
        "private": True,
        "isopen": False,
        "source_observed_at": snapshot["retrievedAt"],
        "issues": [
            issue
            for issue in register["issues"]
            if issue["id"] in {"boundary-internal-api", "gap-compatibility-policy"}
        ],
        "dcat_type": "dcat:DataService",
        "standard_term_ids": ["dcat:DataService"],
        "standards_alignment": {
            "claim": "standards-alignable-not-conformant",
            "profiles": ["DCAT 3", "Hydra Core", "OpenAPI 3.1.0"],
            "dcat": {
                "term": "dcat:DataService",
                "export_status": "service-description-with-gaps",
                "required_missing": [
                    "machine-readable upstream endpoint description",
                    "documented access rights",
                ],
            },
            "notes": [
                "The service mapping is a generated metadata projection and does not certify the upstream service as DCAT conformant."
            ],
        },
    }
    issue_records = [
        {
            **common_project,
            "id": f"els-api:issue:{issue['id']}",
            "record_id": f"els-api:issue:{issue['id']}",
            "native_id": issue["id"],
            "name": issue["id"],
            "title": issue["title"],
            "notes": issue["statement"],
            "description": issue["statement"],
            "record_type": "Governance Finding",
            "type": "Governance Finding",
            "concept_id": f"knowledge/issues/{issue['id']}.md",
            "route": f"issue/{issue['id']}",
            "open": f"issue/{issue['id']}",
            "url": f"{PAGES_ROOT}knowledge/issues/{issue['id']}.md",
            "documentation": f"{PAGES_ROOT}knowledge/issues/{issue['id']}.md",
            "topics": ["review-finding"],
            "tags": ["review-finding", issue["kind"], issue["severity"]],
            "severity": issue["severity"],
            "finding_kind": issue["kind"],
            "recommendation": issue["recommendation"],
        }
        for issue in register["issues"]
    ]
    artifact_definitions = [
        {
            "id": "openapi-review",
            "title": "ELS API OpenAPI review draft",
            "description": "Generated OpenAPI 3.1 projection of the bounded source review.",
            "record_type": "API Contract Draft",
            "resource": "data/openapi.json",
            "tags": ["openapi", "review-draft", "non-executing"],
            "contract_status": "generated-review-draft-not-upstream-contract",
        },
        {
            "id": "selection-plan",
            "title": "ELS API non-executing selection plan",
            "description": "Checks a proposed GET request plan without calling the service.",
            "record_type": "Request Planning Contract",
            "resource": "data/selection-contract.json",
            "tags": ["request-plan", "validation", "non-executing"],
            "contract_status": "non-executing-planning-contract",
        },
    ]
    artifact_records = [
        {
            **common_project,
            "id": f"els-api:artifact:{artifact['id']}",
            "record_id": f"els-api:artifact:{artifact['id']}",
            "native_id": artifact["id"],
            "name": artifact["id"],
            "title": artifact["title"],
            "notes": artifact["description"],
            "description": artifact["description"],
            "record_type": artifact["record_type"],
            "type": artifact["record_type"],
            "concept_id": f"knowledge/artifacts/{artifact['id']}.md",
            "route": f"artifact/{artifact['id']}",
            "open": f"artifact/{artifact['id']}",
            "url": f"{PAGES_ROOT}{artifact['resource']}",
            "documentation": f"{PAGES_ROOT}knowledge/artifacts/{artifact['id']}.md",
            "topics": ["review-artifact"],
            "tags": artifact["tags"],
            "contract_status": artifact["contract_status"],
        }
        for artifact in artifact_definitions
    ]
    snapshot_record = {
        **common_project,
        "id": "els-api:snapshot:wiki-and-source",
        "record_id": "els-api:snapshot:wiki-and-source",
        "native_id": "wiki-and-source",
        "name": "wiki-and-source",
        "title": "ELS wiki and application source review boundary",
        "notes": "Frozen evidence from six wiki pages and a bounded static review of v1 GET route handlers.",
        "description": "Frozen evidence from six wiki pages and a bounded static review of v1 GET route handlers.",
        "record_type": "Source Snapshot",
        "type": "Source Snapshot",
        "concept_id": "knowledge/snapshots/wiki-and-source.md",
        "route": "snapshot/wiki-and-source",
        "open": "snapshot/wiki-and-source",
        "url": f"{PAGES_ROOT}data/provenance/wiki-snapshot.json",
        "documentation": f"{PAGES_ROOT}knowledge/snapshots/wiki-and-source.md",
        "topics": ["provenance"],
        "tags": ["snapshot", "provenance", "drift"],
        "snapshot_id": snapshot["snapshotId"],
        "snapshot_mode": "frozen",
        "live_status": "not-checked",
    }
    standards_record = {
        **common_project,
        "id": "els-api:standards:governed-terms",
        "record_id": "els-api:standards:governed-terms",
        "native_id": "governed-terms",
        "name": "governed-terms",
        "title": "ELS OKF governed metadata terms",
        "notes": "Validated term identifiers, authoritative provenance and bounded application meanings.",
        "description": "Validated term identifiers, authoritative provenance and bounded application meanings.",
        "record_type": "Standards Term Registry",
        "type": "Standards Term Registry",
        "concept_id": "knowledge/standards/governed-terms.md",
        "route": "standard/governed-terms",
        "open": "standard/governed-terms",
        "url": f"{PAGES_ROOT}data/standards/terms.json",
        "documentation": f"{PAGES_ROOT}knowledge/standards/governed-terms.md",
        "topics": ["standards"],
        "tags": ["standards", "vocabulary", "validation", "provenance"],
        "contract_status": "validated-bounded-term-register",
    }
    return [
        service,
        *operations,
        *documents,
        *issue_records,
        *artifact_records,
        snapshot_record,
        standards_record,
    ]


def resource_records(
    register: dict[str, Any],
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "id": f"{record['id']}#endpoint",
            "name": f"{record['name']}-endpoint",
            "title": f"Documented endpoint for {record['title']}",
            "description": (
                "Metadata-only endpoint template. This bundle does not execute the "
                "request or store its response."
            ),
            "resource_type": "api-endpoint-template",
            "dataset": record["name"],
            "dataset_id": record["id"],
            "dataset_route": record["route"],
            "route": f"resource/{record['name']}-endpoint",
            "url": record["url"],
            "documentation": record["documentation"],
            "method": "GET",
            "format": record["formats"][0],
            "formats": record["formats"],
            "protocol": record["protocol"],
            "bundle_metadata_only": True,
            "upstream_may_return_observations": record["native_id"] == "data",
            "execution_included": False,
            "warning": register["policy"]["warning"],
            "provenance": record["provenance"],
        }
        for record in records
    ]


def relationship_records(
    register: dict[str, Any],
    records: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(
        *,
        source: str,
        target: str,
        kind: str,
        label: str,
        predicate: str,
        predicate_term: str,
        confidence: str,
        evidence_type: str,
        evidence: list[str],
        basis: str,
    ) -> None:
        relationship_id = digest_json(
            {
                "source": source,
                "target": target,
                "predicate": predicate,
            }
        )[:16]
        rows.append(
            {
                "id": f"relationship:{relationship_id}",
                "kind": kind,
                "label": label,
                "source": source,
                "target": target,
                "predicate": predicate,
                "predicate_term": predicate_term,
                "standard_term_ids": [predicate_term],
                "assertion_status": "normalized",
                "confidence": confidence,
                "evidence_type": evidence_type,
                "evidence": evidence,
                "basis": basis,
                "observed_at": snapshot["retrievedAt"],
            }
        )

    for record in records:
        add(
            source="service/els-api",
            target=record["route"],
            kind="has-operation",
            label="has operation",
            predicate=(
                "https://chris-page-gov.github.io/okf-explorer/vocab/hasOperation"
            ),
            predicate_term="okf:hasOperation",
            confidence="declared",
            evidence_type="wiki-and-static-source-review",
            evidence=[
                record["documentation"],
                record["documentation_evidence"]["source_handler"],
            ],
            basis="The operation is represented by the pinned wiki and reviewed route handler.",
        )
        add(
            source=record["route"],
            target=f"document/{record['documentation'].rsplit('/', 1)[-1]}",
            kind="documented-by",
            label="documented by",
            predicate="http://purl.org/dc/terms/source",
            predicate_term="dct:source",
            confidence="declared",
            evidence_type="wiki-page-reference",
            evidence=[record["documentation"]],
            basis="The operation register identifies this pinned wiki page as its documentation source.",
        )
        for issue in record["issues"]:
            add(
                source=record["route"],
                target=f"issue/{issue['id']}",
                kind="has-documentation-issue",
                label="has documentation finding",
                predicate=(
                    "https://chris-page-gov.github.io/okf-explorer/vocab/hasFinding"
                ),
                predicate_term="okf:hasFinding",
                confidence="observed",
                evidence_type="wiki-source-comparison",
                evidence=[record["documentation"], issue["id"]],
                basis="The bounded review register attaches this finding to the operation.",
            )

    for issue in register["issues"]:
        if issue["id"] in {"boundary-internal-api", "gap-compatibility-policy"}:
            add(
                source="service/els-api",
                target=f"issue/{issue['id']}",
                kind="has-service-finding",
                label="has service finding",
                predicate=(
                    "https://chris-page-gov.github.io/okf-explorer/vocab/hasFinding"
                ),
                predicate_term="okf:hasFinding",
                confidence="declared",
                evidence_type="wiki-warning",
                evidence=[snapshot["source"]["url"], issue["id"]],
                basis="The finding applies to the documented service boundary.",
            )
        add(
            source=f"issue/{issue['id']}",
            target="snapshot/wiki-and-source",
            kind="derived-from",
            label="derived from",
            predicate="http://www.w3.org/ns/prov#wasDerivedFrom",
            predicate_term="prov:wasDerivedFrom",
            confidence="observed",
            evidence_type="bounded-review-register",
            evidence=[snapshot["snapshotId"]],
            basis="The finding was produced from the frozen wiki and application-source review.",
        )

    for document in documents:
        add(
            source="snapshot/wiki-and-source",
            target=document["route"],
            kind="includes-document",
            label="includes document",
            predicate="http://purl.org/dc/terms/hasPart",
            predicate_term="dct:hasPart",
            confidence="observed",
            evidence_type="snapshot-manifest",
            evidence=[document["sha256"]],
            basis="The source snapshot manifest includes this exact wiki-page digest.",
        )

    for artifact_id in ("openapi-review", "selection-plan"):
        add(
            source=f"artifact/{artifact_id}",
            target="snapshot/wiki-and-source",
            kind="derived-from",
            label="derived from",
            predicate="http://www.w3.org/ns/prov#wasDerivedFrom",
            predicate_term="prov:wasDerivedFrom",
            confidence="observed",
            evidence_type="deterministic-build",
            evidence=[snapshot["snapshotId"]],
            basis="The generated artifact is deterministically derived from the frozen evidence registers.",
        )

    add(
        source="service/els-api",
        target="snapshot/wiki-and-source",
        kind="derived-from",
        label="derived from",
        predicate="http://www.w3.org/ns/prov#wasDerivedFrom",
        predicate_term="prov:wasDerivedFrom",
        confidence="observed",
        evidence_type="bounded-review-register",
        evidence=[snapshot["snapshotId"]],
        basis="The service concept is a metadata projection of the frozen source review.",
    )
    return rows


def openapi_parameter(row: dict[str, Any]) -> dict[str, Any]:
    parameter = {
        "name": row["name"],
        "in": row["in"],
        "required": row["required"],
        "description": row["description"],
        "schema": dict(row["schema"]),
        "x-okf-evidence": row["evidence"],
    }
    default = row.get("default")
    if isinstance(default, (str, int, float, bool)) and not (
        isinstance(default, str) and (";" in default or " for " in default)
    ):
        parameter["schema"]["default"] = default
    return parameter


def response_content(
    operation: dict[str, Any],
    register: dict[str, Any],
) -> dict[str, Any]:
    content: dict[str, Any] = {}
    for format_id in operation["formats"]:
        format_row = register["formats"][format_id]
        media_type = format_row["mediaType"]
        if media_type in content:
            continue
        if media_type == "text/csv":
            schema = {"type": "string"}
        elif media_type.endswith("spreadsheetml.sheet"):
            schema = {"type": "string", "format": "binary"}
        else:
            schema = {}
        content[media_type] = {
            "schema": schema,
            "x-okf-schema-status": "not-specified-by-wiki",
        }
    return content


def build_openapi(
    register: dict[str, Any],
    records: list[dict[str, Any]],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    record_lookup = {record["native_id"]: record for record in records}
    paths: dict[str, Any] = {}
    for operation in register["operations"]:
        record = record_lookup[operation["id"]]
        parameters = [
            openapi_parameter(row)
            for row in record["parameters"]
            if not row.get("dynamic")
        ]
        operation_object: dict[str, Any] = {
            "operationId": operation["id"].replace("-", "_"),
            "summary": operation["title"],
            "description": operation["summary"],
            "tags": [operation["family"]],
            "parameters": parameters,
            "responses": {
                "200": {
                    "description": "Successful response. The wiki does not provide a complete response schema.",
                    "content": response_content(operation, register),
                },
                "400": {
                    "description": "Invalid, duplicate, unsupported or oversized request."
                },
                "404": {"description": "Requested indicator, dimension or area was not found."},
            },
            "x-okf-status": "review-draft-not-upstream-contract",
            "x-okf-execution-included": False,
            "x-okf-live-verified": False,
            "x-okf-documentation": wiki_url(operation["wiki"]),
            "x-okf-source-handler": source_url(register, operation["sourcePath"]),
            "x-okf-documentation-issues": record["issues"],
        }
        dynamic_parameters = [
            row for row in record["parameters"] if row.get("dynamic")
        ]
        if dynamic_parameters:
            operation_object["x-okf-dynamic-query-parameters"] = dynamic_parameters
        if operation.get("documentedOnlyParameters"):
            operation_object["x-okf-documented-only-parameters"] = operation[
                "documentedOnlyParameters"
            ]
        if operation.get("sourceOnlyParameters"):
            operation_object["x-okf-source-only-parameters"] = operation[
                "sourceOnlyParameters"
            ]
        if operation["documentedPath"] != operation["path"]:
            operation_object["x-okf-documented-path"] = operation["documentedPath"]
        paths[operation["path"]] = {"get": operation_object}
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Explore Local Statistics internal API — OKF review draft",
            "version": "0.1.0",
            "description": (
                f"{register['policy']['warning']} This file is generated from a wiki "
                "snapshot and static source review; it is not an upstream ONS API contract."
            ),
            "license": {
                "name": "MIT (generated review artifact)",
                "url": BUNDLE_LICENSE,
            },
        },
        "servers": [{"url": register["baseUrl"]}],
        "tags": [
            {"name": "data", "description": "Statistical filtering and download."},
            {"name": "metadata", "description": "Indicator metadata and taxonomy."},
            {"name": "geography", "description": "Area metadata and boundaries."},
        ],
        "paths": paths,
        "x-okf": {
            "schema": "okf-els-api.openapi-review.v1",
            "status": "review-draft",
            "sourceSnapshot": snapshot["snapshotId"],
            "wikiCommit": snapshot["source"]["commit"],
            "sourceCommit": register["sourceVerification"]["commit"],
            "liveProbePerformed": False,
            "observationsIncluded": False,
            "executionIncluded": False,
            "sourceLicenceEvidence": {
                "status": snapshot["licenceEvidence"]["status"],
                "statement": snapshot["licenceEvidence"]["statement"],
                "url": (
                    f"{register['sourceVerification']['repository']}/blob/"
                    f"{register['sourceVerification']['commit']}/LICENSE.md"
                ),
            },
        },
    }


def semantic_descriptor(
    register: dict[str, Any],
    records: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    snapshot: dict[str, Any],
    publication: dict[str, Any],
) -> dict[str, Any]:
    operations = [
        {
            "@id": f"urn:okf:els-api:operation:{record['native_id']}",
            "@type": "hydra:Operation",
            "hydra:method": "GET",
            "dct:title": record["title"],
            "dct:description": record["description"],
            "okf:requestTemplate": {
                "@type": "hydra:IriTemplate",
                "hydra:template": record["url"],
                "hydra:mapping": [
                    {
                        "@type": "hydra:IriTemplateMapping",
                        "hydra:variable": parameter["name"],
                        "hydra:required": parameter["required"],
                        "okf:evidence": parameter["evidence"],
                    }
                    for parameter in record["parameters"]
                ],
            },
            "dct:source": {"@id": record["documentation"]},
            "okf:executionIncluded": False,
            "okf:liveVerified": False,
        }
        for record in records
    ]
    return {
        "@context": {
            "dcat": "http://www.w3.org/ns/dcat#",
            "dct": "http://purl.org/dc/terms/",
            "foaf": "http://xmlns.com/foaf/0.1/",
            "hydra": "http://www.w3.org/ns/hydra/core#",
            "okf": "https://chris-page-gov.github.io/okf-explorer/vocab/",
            "prov": "http://www.w3.org/ns/prov#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        },
        "@id": "urn:okf:els-api:catalogue",
        "@type": "dcat:Catalog",
        "dct:title": "Explore Local Statistics API discovery OKF",
        "dct:description": register["description"],
        "dct:publisher": {
            "@id": "https://github.com/chris-page-gov/okf-els-api",
            "@type": "foaf:Agent",
            "foaf:name": "OKF ELS API project",
        },
        "dct:issued": publication["generatedAt"],
        "dct:conformsTo": {"@id": OKF_SPECIFICATION},
        "dct:license": {"@id": BUNDLE_LICENSE},
        "okf:sourceLicenceEvidence": {
            "@id": (
                f"{register['sourceVerification']['repository']}/blob/"
                f"{register['sourceVerification']['commit']}/LICENSE.md"
            )
        },
        "prov:wasDerivedFrom": [
            {"@id": snapshot["source"]["url"]},
            {"@id": register["sourceVerification"]["repository"]},
        ],
        "dcat:service": [
            {
                "@id": "urn:okf:els-api:service",
                "@type": "dcat:DataService",
                "dct:title": register["title"],
                "dct:description": register["policy"]["warning"],
                "dct:publisher": {
                    "@id": "https://www.ons.gov.uk/",
                    "@type": "foaf:Agent",
                    "foaf:name": "Office for National Statistics",
                },
                "dcat:endpointURL": {"@id": register["baseUrl"]},
                "dcat:endpointDescription": {"@id": snapshot["source"]["url"]},
                "okf:supportedOperation": operations,
                "okf:status": register["status"],
                "okf:executionIncluded": False,
                "okf:observationsIncluded": False,
            }
        ],
        "dct:hasPart": [
            {
                "@id": f"urn:okf:els-api:document:{document['name']}",
                "@type": "foaf:Document",
                "dct:title": document["title"],
                "dct:identifier": document["sha256"],
                "dct:source": {"@id": document["url"]},
            }
            for document in documents
        ],
        "okf:alignmentClaim": {
            "dcat-3": "aligned",
            "hydra": "partial",
            "openapi-3.1": "partial",
            "prov-o": "aligned",
            "claim": "Bundle mapping only; not upstream conformance or service certification.",
        },
        "okf:okfVersion": OKF_VERSION,
        "okf:normativeEntrypoint": {"@id": "index.md"},
        "okf:snapshotMode": "frozen",
        "okf:liveStatus": "not-checked",
        "okf:generatedAt": publication["generatedAt"],
        "okf:wikiSourceModified": snapshot["source"]["commitDate"],
        "okf:applicationSourceModified": register["sourceVerification"][
            "commitDate"
        ],
    }


def facet_rows(values: list[str]) -> list[dict[str, Any]]:
    return [
        {"value": value, "label": value, "count": count}
        for value, count in sorted(Counter(values).items())
    ]


def explorer_facet_values(record: dict[str, Any], key: str) -> list[str]:
    if key == "family":
        return [str(value) for value in record.get("topics", [])]
    if key == "format":
        return [str(value) for value in record.get("formats", [])]
    if key == "has_documentation_issues":
        return ["yes" if record.get("issues") else "no"]
    value = record.get(key)
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    return [] if value in (None, "") else [str(value)]


def explorer_facets(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    keys = [
        "record_type",
        "family",
        "format",
        "has_documentation_issues",
        "publisher",
        "source_tier",
        "visibility",
        "lifecycle_status",
        "state",
    ]
    return {
        key: facet_rows(
            [
                value
                for record in records
                for value in explorer_facet_values(record, key)
            ]
        )
        for key in keys
    }


FACET_DEFINITIONS = {
    "record_type": (
        "Concept type",
        "The normalized kind of knowledge concept represented by the record.",
    ),
    "family": (
        "Topic",
        "The main ELS or bundle-review topic associated with a concept.",
    ),
    "format": (
        "Representation",
        "A documented API representation or metadata-document format.",
    ),
    "has_documentation_issues": (
        "Has findings",
        "Whether the concept has one or more preserved documentation or governance findings.",
    ),
    "publisher": (
        "Publisher",
        "The upstream source publisher or the project responsible for a generated review artifact.",
    ),
    "source_tier": (
        "Evidence tier",
        "The bounded evidence surface from which the record was projected.",
    ),
    "visibility": (
        "Visibility",
        "Whether the described resource is internal/private or a public metadata artifact.",
    ),
    "lifecycle_status": (
        "Lifecycle",
        "The OKF lifecycle status projected for Explorer filtering.",
    ),
    "state": (
        "Source state",
        "The bounded state of the source or generated review record.",
    ),
}


def facet_analysis(
    records: list[dict[str, Any]],
    facets: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    total = len(records)
    rows: list[dict[str, Any]] = []
    primary = {"record_type", "family"}
    secondary = {"format", "has_documentation_issues"}
    for priority, (key, values) in enumerate(facets.items(), start=1):
        assignments = sum(row["count"] for row in values)
        covered = sum(
            1 for record in records if explorer_facet_values(record, key)
        )
        probabilities = [
            row["count"] / assignments for row in values if assignments
        ]
        entropy = (
            -sum(probability * math.log2(probability) for probability in probabilities)
            / math.log2(len(probabilities))
            if len(probabilities) > 1
            else 0.0
        )
        expected_reduction = (
            1
            - sum(
                (row["count"] / assignments) * min(row["count"] / total, 1.0)
                for row in values
            )
            if assignments and total
            else 0.0
        )
        if len(values) <= 1:
            recommendation = "suppressed"
        elif key in primary:
            recommendation = "primary"
        elif key in secondary:
            recommendation = "secondary"
        else:
            recommendation = "advanced"
        label, description = FACET_DEFINITIONS[key]
        rows.append(
            {
                "key": key,
                "label": label,
                "description": description,
                "coverage": round(covered / total, 6) if total else 0,
                "cardinality": len(values),
                "top_share": (
                    round(max(row["count"] for row in values) / total, 6)
                    if values and total
                    else 0
                ),
                "entropy": round(entropy, 6),
                "expected_reduction": round(expected_reduction, 6),
                "recommended_control": (
                    "distribution" if len(values) <= 12 else "search"
                ),
                "recommendation": recommendation,
                "display_priority": priority * 10,
                "default_pinned": key in primary,
                "default_hidden": recommendation == "suppressed",
                "value_type": "nominal",
                "value_order": "count-desc",
                "examples": [row["value"] for row in values[:3]],
                "values": values,
            }
        )
    return rows


def presentation_profile(
    snapshot_id: str,
    analysis: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": "okf-explorer-presentation.v1",
        "status": "experimental",
        "snapshot": snapshot_id,
        "defaults": {
            "facet_mode": "suggested",
            "search_threshold": 48,
            "distribution_segment_limit": 10,
        },
        "facets": [
            {
                "key": row["key"],
                "label": row["label"],
                "description": row["description"],
                "value_type": row["value_type"],
                "order": row["display_priority"],
                "default_state": (
                    "hidden"
                    if row["recommendation"] == "suppressed"
                    else "pinned"
                    if row["recommendation"] == "primary"
                    else "shown"
                ),
                "open_control": row["recommended_control"],
                "value_order": row["value_order"],
                "examples": row["examples"],
            }
            for row in analysis
        ],
        "panels": {
            "left": {
                "tabs": ["facets", "browse", "results"],
                "default_tab": "facets",
            },
            "right": {
                "tabs": ["overview", "evidence", "data"],
                "default_tab": "overview",
            },
        },
    }


def search_tokens(value: Any) -> list[str]:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(character for character in text if not unicodedata.combining(character))
    seen: set[str] = set()
    tokens: list[str] = []
    for match in re.findall(r"[a-z0-9][a-z0-9._-]*", text.lower()):
        token = match.strip("._-")
        if len(token) < 2 or token in SEARCH_STOP_WORDS or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def search_result_documents(
    records: list[dict[str, Any]],
    resources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    resource_counts = Counter(resource["dataset"] for resource in resources)
    return [
        {
            "ordinal": ordinal,
            "name": record["name"],
            "title": record["title"],
            "publisher": record["publisher"],
            "publisher_title": record["publisher_title"],
            "resource_count": resource_counts[record["name"]],
            "formats": record.get("formats", []),
            "tags": record.get("tags", []),
            "topics": record.get("topics", []),
            "timestamp": record.get("source_observed_at"),
            "notes": record.get("notes", record.get("description", "")),
            "endpoint_host": record.get("host"),
            "documentation_host": (
                "github.com"
                if str(record.get("documentation", "")).startswith(
                    "https://github.com/"
                )
                else None
            ),
            "access_model": record.get("access_model"),
            "visibility": record.get("visibility"),
            "contract_status": record.get("contract_status"),
            "record_type": record["record_type"],
            "record_id": record.get("record_id", record["id"]),
            "native_id": record.get("native_id", record["name"]),
            "source_adapter": record.get("source_adapter"),
            "source_surface": record.get("source_surface"),
            "source_tier": record.get("source_tier"),
            "confidence": record.get("confidence"),
            "license_id": record.get("license_id"),
            "license_title": record.get("license_title"),
            "license_source_id": record.get("license_source_id"),
            "license_source_title": record.get("license_source_title"),
            "license_basis": record.get("license_basis"),
            "concept_id": record.get("concept_id"),
            "lifecycle_status": record.get("lifecycle_status"),
            "dcat_type": record.get("dcat_type"),
            "openapi_type": record.get("openapi_type"),
            "hydra_type": record.get("hydra_type"),
            "standard_term_ids": record.get("standard_term_ids", []),
            "standards_alignment": record.get("standards_alignment"),
            "open": record["open"],
            "url": record["url"],
            "documentation": record.get("documentation"),
        }
        for ordinal, record in enumerate(records)
    ]


def delta_encode(ordinals: list[int]) -> list[int]:
    previous = 0
    encoded: list[int] = []
    for index, ordinal in enumerate(ordinals):
        encoded.append(ordinal if index == 0 else ordinal - previous)
        previous = ordinal
    return encoded


def static_search_index(
    records: list[dict[str, Any]],
    resources: list[dict[str, Any]],
    snapshot: dict[str, Any],
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    result_documents = search_result_documents(records, resources)
    resources_by_dataset: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for resource in resources:
        resources_by_dataset[resource["dataset"]].append(resource)

    postings: dict[str, dict[int, list[int]]] = defaultdict(dict)
    for ordinal, record in enumerate(records):
        related_resources = resources_by_dataset[record["name"]]
        parameters = record.get("parameters", [])
        fields = {
            "title": record["title"],
            "route": " ".join(
                [
                    record.get("route", ""),
                    record.get("path_template", ""),
                    record.get("documented_path_template", ""),
                    *[parameter["name"] for parameter in parameters],
                ]
            ),
            "name": f"{record['name']} {record.get('native_id', '')}",
            "publisher": f"{record['publisher']} {record['publisher_title']}",
            "notes": f"{record.get('notes', '')} {record.get('description', '')}",
            "resources": " ".join(
                " ".join(
                    str(resource.get(key, ""))
                    for key in ("name", "title", "description", "format", "url")
                )
                for resource in related_resources
            ),
            "formats": " ".join(record.get("formats", [])),
            "tags": " ".join(
                [*record.get("tags", []), *record.get("topics", [])]
            ),
        }
        for field, value in fields.items():
            for token in search_tokens(value):
                score_mask = postings[token].setdefault(ordinal, [0, 0])
                score_mask[0] += SEARCH_FIELD_WEIGHTS[field]
                score_mask[1] |= SEARCH_FIELD_MASKS[field]

    postings_path = "data/search/postings-0001.json"
    lexicon = [
        {
            "token": token,
            "df": len(documents),
            "postings": postings_path,
        }
        for token, documents in sorted(postings.items())
    ]
    prefixes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for token, documents in sorted(postings.items()):
        for length in range(3, min(len(token), 8) + 1):
            prefixes[token[:length]].append({"token": token, "df": len(documents)})
    prefix_index = {
        prefix: sorted(
            values,
            key=lambda row: (-row["df"], row["token"]),
        )[:24]
        for prefix, values in sorted(prefixes.items())
    }

    facet_ordinals: dict[str, dict[str, list[int]]] = {
        "family": defaultdict(list),
        "format": defaultdict(list),
        "has_documentation_issues": defaultdict(list),
        "publisher": defaultdict(list),
        "record_type": defaultdict(list),
        "source_tier": defaultdict(list),
        "visibility": defaultdict(list),
        "lifecycle_status": defaultdict(list),
        "state": defaultdict(list),
    }
    for ordinal, record in enumerate(records):
        for topic in record.get("topics", []):
            facet_ordinals["family"][topic].append(ordinal)
        facet_ordinals["has_documentation_issues"][
            "yes" if record.get("issues") else "no"
        ].append(ordinal)
        facet_ordinals["publisher"][record["publisher"]].append(ordinal)
        facet_ordinals["record_type"][record["record_type"]].append(ordinal)
        facet_ordinals["source_tier"][record["source_tier"]].append(ordinal)
        facet_ordinals["visibility"][record["visibility"]].append(ordinal)
        facet_ordinals["lifecycle_status"][record["lifecycle_status"]].append(
            ordinal
        )
        facet_ordinals["state"][record["state"]].append(ordinal)
        for format_id in record.get("formats", []):
            facet_ordinals["format"][format_id].append(ordinal)
    search_facets = {
        key: {
            value: delta_encode(ordinals)
            for value, ordinals in sorted(values.items())
        }
        for key, values in facet_ordinals.items()
    }
    document_map = {
        record["name"]: {
            "ordinal": ordinal,
            "doc_chunk": "data/search/results-0.json",
        }
        for ordinal, record in enumerate(records)
    }
    manifest = {
        "schema": "okf-static-search.v1",
        "snapshot": snapshot["snapshotId"],
        "generated_at": generated_at,
        "token_min_length": 2,
        "prefix_min_length": 3,
        "lexicon_shard_length": 1,
        "result_limit": 50,
        "result_doc_chunk_size": len(result_documents),
        "weights": SEARCH_FIELD_WEIGHTS,
        "field_masks": SEARCH_FIELD_MASKS,
        "counts": {
            "documents": len(result_documents),
            "tokens": len(postings),
            "max_postings_per_token": len(result_documents),
            "lexicon_chunks": 1,
            "prefix_chunks": 1,
            "postings_shards": 1,
            "postings": sum(len(rows) for rows in postings.values()),
            "result_doc_chunks": 1,
            "doc_map_shards": 1,
        },
        "entrypoints": {
            "lexicon": {"_": "data/search/lexicon-_.json"},
            "prefixes": {"_": "data/search/prefix-_.json"},
            "postings": [postings_path],
            "result_docs": ["data/search/results-0.json"],
            "facets": "data/search/facets.json",
            "doc_map": "data/search/doc-map.json",
        },
    }
    outputs = {
        "data/search/manifest.json": manifest,
        "data/search/lexicon-_.json": lexicon,
        "data/search/prefix-_.json": prefix_index,
        postings_path: {
            "schema": "okf-search-postings.v1",
            "tokens": {
                token: [
                    [ordinal, score_mask[0], score_mask[1]]
                    for ordinal, score_mask in sorted(documents.items())
                ]
                for token, documents in sorted(postings.items())
            },
        },
        "data/search/results-0.json": result_documents,
        "data/search/facets.json": search_facets,
        "data/search/doc-map.json": document_map,
    }
    return manifest, outputs


def selection_contract(register: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "okf-els-api.selection-plan.v1",
        "purpose": "Validate a read-only request plan without executing it.",
        "required": ["operationId", "method", "pathArguments", "queryArguments"],
        "constraints": {
            "method": "GET",
            "operationId": sorted(operation["id"] for operation in register["operations"]),
            "pathArguments": "Every path variable for the selected operation must be supplied.",
            "queryArguments": "Names must be registered for the selected operation, except documented dimension_{code} dynamic filters.",
            "documentedOnlyParameters": "Blocked until the wiki/source conflict is resolved.",
        },
        "outcomes": [
            "unknown-operation",
            "incomplete-path",
            "unsupported-parameter",
            "documented-source-conflict",
            "complete-non-executing-plan",
        ],
        "execution": {
            "included": False,
            "requiresExplicitClientAction": True,
            "warning": register["policy"]["warning"],
        },
    }


def write_okf_markdown(
    writer: Writer,
    register: dict[str, Any],
    snapshot: dict[str, Any],
    publication: dict[str, Any],
    records: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    standards_source: dict[str, Any],
) -> dict[str, Any]:
    """Write the normative OKF v0.2 layer and return its validation report."""

    generated = {
        "by": publication["generatedBy"],
        "at": publication["generatedAt"],
    }
    wiki_modified = snapshot["source"]["commitDate"][:10]
    source_modified = register["sourceVerification"]["commitDate"][:10]
    wiki_source = {
        "id": "els-wiki",
        "resource": snapshot["source"]["url"],
        "title": snapshot["source"]["title"],
        "last_modified": wiki_modified,
        "pinned_commit": snapshot["source"]["commit"],
    }
    application_source = {
        "id": "els-application",
        "resource": (
            f"{register['sourceVerification']['repository']}/tree/"
            f"{register['sourceVerification']['commit']}"
        ),
        "title": "Explore Local Statistics application source review",
        "last_modified": source_modified,
        "pinned_commit": register["sourceVerification"]["commit"],
    }

    writer.write_text(
        "index.md",
        render_frontmatter({"okf_version": OKF_VERSION})
        + (
            "\n# Explore Local Statistics API discovery OKF\n\n"
            f"{register['policy']['warning']}\n\n"
            "This Markdown tree is the normative OKF v0.2 layer. JSON, JSON-LD, "
            "YAML-LD, OpenAPI and search files are generated projections.\n\n"
            "## Explore\n\n"
            "* [Knowledge concepts](knowledge/) - service, operation, source, "
            "review and contract concepts.\n"
            "* [Update log](log.md) - publication history.\n"
            "* [OKF conformance report](data/standards/okf-v0.2.json) - "
            "producer validation evidence.\n"
            "* [OKF Explorer descriptor](okf-explorer.json) - interactive "
            "projection entrypoint.\n"
        ),
    )
    writer.write_text(
        "log.md",
        (
            "# Bundle update log\n\n"
            "## 2026-07-25\n"
            "* **Migration**: Added a normative OKF v0.2 Markdown concept layer "
            "without inventing verification, freshness or attestation claims.\n"
            "* **Clarification**: Separated the bundle generation checkpoint from "
            "the pinned wiki and application-source modification dates.\n\n"
            "## 2026-07-20\n"
            "* **Creation**: Published the bounded metadata-only API review bundle.\n"
        ),
    )
    writer.write_text(
        "knowledge/index.md",
        (
            "# Knowledge concepts\n\n"
            "* [ELS API service](service.md) - bounded, non-executing service "
            "discovery concept.\n"
            "* [Operations](operations/) - 18 documented GET operations.\n"
            "* [Source documents](documents/) - six pinned wiki page records.\n"
            "* [Review issues](issues/) - nine preserved findings and gaps.\n"
            "* [Review artifacts](artifacts/) - generated OpenAPI and selection "
            "planning contracts.\n"
            "* [Source snapshot](snapshots/) - frozen wiki and application review "
            "boundary.\n"
            "* [Governed terms](standards/) - validated standards and Explorer "
            "UI terminology.\n"
        ),
    )
    writer.write_text(
        "knowledge/operations/index.md",
        "# API operations\n\n"
        + "".join(
            f"* [{record['title']}]({record['native_id']}.md) - "
            f"{record['description']}\n"
            for record in records
        ),
    )
    writer.write_text(
        "knowledge/documents/index.md",
        "# Source documents\n\n"
        + "".join(
            f"* [{document['title']}]({document['name']}.md) - "
            "pinned wiki page metadata.\n"
            for document in documents
        ),
    )
    writer.write_text(
        "knowledge/issues/index.md",
        "# Review issues\n\n"
        + "".join(
            f"* [{issue['title']}]({issue['id']}.md) - "
            f"{issue['kind']} ({issue['severity']}).\n"
            for issue in register["issues"]
        ),
    )
    writer.write_text(
        "knowledge/artifacts/index.md",
        (
            "# Review artifacts\n\n"
            "* [OpenAPI review draft](openapi-review.md) - generated API contract "
            "projection, not an upstream contract.\n"
            "* [Selection plan](selection-plan.md) - validates request plans without "
            "executing them.\n"
        ),
    )
    writer.write_text(
        "knowledge/snapshots/index.md",
        (
            "# Source snapshots\n\n"
            "* [Wiki and application source review](wiki-and-source.md) - frozen "
            "evidence boundary and live-status declaration.\n"
        ),
    )
    writer.write_text(
        "knowledge/standards/index.md",
        (
            "# Governed metadata terms\n\n"
            "* [Term registry](governed-terms.md) - identifiers, definitions, "
            "provenance, bounded applications and validation results.\n"
        ),
    )

    writer.write_text(
        "knowledge/service.md",
        render_concept(
            {
                "type": "API Service",
                "title": register["title"],
                "description": register["description"],
                "resource": register["baseUrl"],
                "tags": ["api", "ons", "internal-private", "metadata-only"],
                "status": "draft",
                "generated": generated,
                "sources": [wiki_source, application_source],
                "snapshot_mode": "frozen",
                "live_status": "not-checked",
                "execution_included": False,
                "observations_included": False,
            },
            (
                "# Scope\n\n"
                f"{register['policy']['warning']}\n\n"
                "This concept describes the bounded API discovery surface; it does "
                "not certify the service as stable, public, supported or live. See "
                "the [frozen source boundary](snapshots/wiki-and-source.md) and the "
                "[18 operation concepts](operations/).\n\n"
                "# Execution boundary\n\n"
                "The bundle does not execute requests. The generated selection plan "
                "only checks a proposed request's shape."
            ),
        ),
    )
    writer.write_text(
        "knowledge/snapshots/wiki-and-source.md",
        render_concept(
            {
                "type": "Source Snapshot",
                "title": "ELS wiki and application source review boundary",
                "description": (
                    "Frozen evidence from six wiki pages and a bounded static review "
                    "of v1 GET route handlers."
                ),
                "resource": "/data/provenance/wiki-snapshot.json",
                "tags": ["snapshot", "provenance", "drift"],
                "status": "draft",
                "generated": generated,
                "sources": [wiki_source, application_source],
                "snapshot_id": snapshot["snapshotId"],
                "snapshot_mode": "frozen",
                "live_status": "not-checked",
                "drift_scope": "pinned-wiki-versus-pinned-develop-review",
            },
            (
                "# Temporal boundary\n\n"
                f"* Bundle generation checkpoint: `{publication['generatedAt']}`.\n"
                f"* Wiki snapshot: `{snapshot['source']['commit']}` "
                f"({snapshot['source']['commitDate']}).\n"
                "* Reviewed application `develop` commit: "
                f"`{register['sourceVerification']['commit']}` "
                f"({register['sourceVerification']['commitDate']}).\n"
                "* Current live/upstream state: **not checked**.\n\n"
                "The nine drift findings compare the two pinned evidence surfaces. "
                "They do not assert the present state of the wiki, branch or deployed "
                "service."
            ),
        ),
    )
    writer.write_text(
        "knowledge/standards/governed-terms.md",
        render_concept(
            {
                "type": "Standards Term Registry",
                "title": "ELS OKF governed metadata terms",
                "description": (
                    "Validated identifiers, authoritative provenance and bounded "
                    "application meanings for standards and Explorer UI terms."
                ),
                "resource": "/data/standards/terms.json",
                "tags": ["standards", "vocabulary", "validation", "provenance"],
                "status": "draft",
                "generated": generated,
                "sources": [
                    {
                        "id": vocabulary["id"],
                        "resource": vocabulary["source"],
                        "title": vocabulary["title"],
                    }
                    for vocabulary in standards_source["vocabularies"]
                ],
                "validation_report": "/data/standards/term-validation.json",
                "snapshot_mode": "frozen",
                "live_status": "not-checked",
            },
            (
                "# Validation model\n\n"
                "The register separates recognition of an identifier from the "
                "correctness of its application. Every emitted compact term must "
                "have a declared namespace, primary specification provenance, term "
                "kind, bounded-use explanation and validated application status.\n\n"
                "# Trust boundary\n\n"
                "The validation is a deterministic closed-world check against the "
                "checked-in curated register. It is machine-confirmed publication "
                "evidence, not human review, live vocabulary verification or a claim "
                "that the upstream API conforms to every referenced standard.\n\n"
                "See the [machine-readable validation report]"
                "(/data/standards/term-validation.json)."
            ),
        ),
    )

    document_lookup = {document["name"]: document for document in documents}
    for record in records:
        operation = next(
            row for row in register["operations"] if row["id"] == record["native_id"]
        )
        document = document_lookup[operation["wiki"]]
        issue_links = (
            "\n".join(
                f"* [{issue['title']}](../issues/{issue['id']}.md) "
                f"({issue['severity']})"
                for issue in record["issues"]
            )
            or "* No registered issue is attached to this operation."
        )
        parameter_names = ", ".join(
            f"`{parameter['name']}`" for parameter in record["parameters"]
        )
        writer.write_text(
            f"knowledge/operations/{record['native_id']}.md",
            render_concept(
                {
                    "type": "API Endpoint",
                    "title": record["title"],
                    "description": record["description"],
                    "resource": record["url"],
                    "tags": record["tags"],
                    "status": "draft",
                    "generated": generated,
                    "sources": [
                        {
                            "id": "wiki-page",
                            "resource": record["documentation"],
                            "title": document["title"],
                            "pinned_commit": snapshot["source"]["commit"],
                            "revision_at": snapshot["source"]["commitDate"],
                            "sha256": document["sha256"],
                        },
                        {
                            "id": "route-handler",
                            "resource": record["documentation_evidence"][
                                "source_handler"
                            ],
                            "title": "Reviewed application route handler",
                            "pinned_commit": register["sourceVerification"]["commit"],
                            "revision_at": register["sourceVerification"][
                                "commitDate"
                            ],
                        },
                    ],
                    "method": "GET",
                    "path_template": record["path_template"],
                    "documented_path_template": record[
                        "documented_path_template"
                    ],
                    "snapshot_mode": "frozen",
                    "live_status": "not-checked",
                    "execution_included": False,
                },
                (
                    "# Route\n\n"
                    f"`GET {record['path_template']}`\n\n"
                    f"Parameters represented by the bounded review: "
                    f"{parameter_names or 'none'}.\n\n"
                    f"Source page: [{document['title']}]"
                    f"(../documents/{document['name']}.md).\n\n"
                    "# Preserved review findings\n\n"
                    f"{issue_links}\n\n"
                    "# Usage boundary\n\n"
                    f"{register['policy']['warning']} This concept is descriptive "
                    "and does not authorise execution."
                ),
            ),
        )

    for document in documents:
        writer.write_text(
            f"knowledge/documents/{document['name']}.md",
            render_concept(
                {
                    "type": "Reference",
                    "title": document["title"],
                    "description": "Metadata for one page in the frozen ELS API wiki snapshot.",
                    "resource": document["url"],
                    "tags": ["wiki", "source-document", "snapshot"],
                    "status": "draft",
                    "generated": generated,
                    "sources": [
                        {
                            "id": "wiki-page",
                            "resource": document["url"],
                            "title": document["title"],
                            "pinned_commit": document["source_commit"],
                            "revision_at": snapshot["source"]["commitDate"],
                        }
                    ],
                    "snapshot_mode": "frozen",
                    "live_status": "not-checked",
                },
                (
                    "# Snapshot evidence\n\n"
                    f"* File: `{document['file']}`\n"
                    f"* SHA-256: `{document['sha256']}`\n"
                    f"* Lines: {document['lines']}\n"
                    f"* Bytes: {document['bytes']}\n"
                    f"* Retrieved: `{document['retrieved_at']}`\n\n"
                    "The page body is not republished here; this concept records the "
                    "bounded source identity and integrity evidence."
                ),
            ),
        )

    for issue in register["issues"]:
        writer.write_text(
            f"knowledge/issues/{issue['id']}.md",
            render_concept(
                {
                    "type": "Governance Finding",
                    "title": issue["title"],
                    "description": issue["statement"],
                    "tags": ["review-finding", issue["kind"], issue["severity"]],
                    "status": "draft",
                    "generated": generated,
                    "sources": [wiki_source, application_source],
                    "finding_kind": issue["kind"],
                    "severity": issue["severity"],
                    "wiki_evidence": issue.get("wikiEvidence"),
                    "source_evidence": issue.get("sourceEvidence"),
                    "recommendation": issue["recommendation"],
                    "snapshot_mode": "frozen",
                    "live_status": "not-checked",
                },
                (
                    "# Finding\n\n"
                    f"{issue['statement']}\n\n"
                    "# Evidence\n\n"
                    f"* Wiki evidence: {issue.get('wikiEvidence') or 'not supplied'}\n"
                    "* Application source evidence: "
                    f"{issue.get('sourceEvidence') or 'not supplied'}\n\n"
                    "# Recommendation\n\n"
                    f"{issue['recommendation']}\n\n"
                    "# Evidence boundary\n\n"
                    "This finding records a comparison of the pinned wiki snapshot "
                    "and pinned application source review. It has not been rechecked "
                    "against current upstream or a live service."
                ),
            ),
        )

    artifact_source = {
        "id": "snapshot-boundary",
        "resource": "/knowledge/snapshots/wiki-and-source.md",
        "title": "ELS wiki and application source review boundary",
        "revision_at": publication["generatedAt"],
    }
    writer.write_text(
        "knowledge/artifacts/openapi-review.md",
        render_concept(
            {
                "type": "API Contract Draft",
                "title": "ELS API OpenAPI review draft",
                "description": (
                    "Generated OpenAPI 3.1 projection of the bounded source review."
                ),
                "resource": "/data/openapi.json",
                "tags": ["openapi", "review-draft", "non-executing"],
                "status": "draft",
                "generated": generated,
                "sources": [artifact_source],
                "snapshot_mode": "frozen",
                "live_status": "not-checked",
                "upstream_contract": False,
            },
            (
                "# Contract boundary\n\n"
                "This projection preserves known wiki/source conflicts. It is not an "
                "upstream ONS API contract and does not establish compatibility, "
                "support or deployment state."
            ),
        ),
    )
    writer.write_text(
        "knowledge/artifacts/selection-plan.md",
        render_concept(
            {
                "type": "Request Planning Contract",
                "title": "ELS API non-executing selection plan",
                "description": (
                    "Checks a proposed GET request plan without calling the service."
                ),
                "resource": "/data/selection-contract.json",
                "tags": ["request-plan", "validation", "non-executing"],
                "status": "draft",
                "generated": generated,
                "sources": [artifact_source],
                "snapshot_mode": "frozen",
                "live_status": "not-checked",
                "execution_included": False,
                "attested_computation": False,
            },
            (
                "# Planning boundary\n\n"
                "This is passive metadata for request planning. It is not an Attested "
                "Computation, executor, attester or permission to invoke the API."
            ),
        ),
    )

    return validate_okf_bundle(writer.root)


def landing_page(
    register: dict[str, Any],
    snapshot: dict[str, Any],
    publication: dict[str, Any],
    operation_count: int,
) -> str:
    warning = html.escape(register["policy"]["warning"])
    snapshot_id = html.escape(snapshot["snapshotId"])
    generated_at = html.escape(publication["generatedAt"])
    wiki_commit = html.escape(snapshot["source"]["commit"][:12])
    source_commit = html.escape(register["sourceVerification"]["commit"][:12])
    return f"""<!doctype html>
<html lang="en-GB">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Metadata-only OKF discovery bundle for the Explore Local Statistics internal API documentation.">
  <meta name="referrer" content="no-referrer">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'self'; img-src 'self'; object-src 'none'; base-uri 'self'; form-action 'none'">
  <title>Explore Local Statistics API · Open Knowledge Format</title>
  <link rel="stylesheet" href="site.css">
</head>
<body>
  <a class="skip-link" href="#main-content">Skip to bundle summary</a>
  <header class="site-header">
    <div class="shell header-inner">
      <a class="brand" href="./" aria-label="Explore Local Statistics API OKF home">
        <span class="brand-mark" aria-hidden="true">OKF</span>
        <span>
          <strong>Explore Local Statistics API</strong>
          <small>metadata-only discovery bundle</small>
        </span>
      </a>
      <nav aria-label="Bundle links">
        <a href="index.md">OKF 0.2</a>
        <a href="okf-explorer.json">Descriptor</a>
        <a href="data/openapi.json">OpenAPI</a>
        <a href="data/review/issues.json">Review findings</a>
      </nav>
    </div>
  </header>
  <main id="main-content">
    <section class="hero">
      <div class="shell hero-grid">
        <div>
          <p class="eyebrow">Bounded source snapshot · read-only documentation</p>
          <h1>Discover the ELS API surface without executing it.</h1>
          <p class="lede">
            A portable catalogue of routes, parameters, representations,
            provenance and known differences between the wiki and application source.
          </p>
          <div class="actions">
            <a class="button primary" href="{html.escape(EXPLORER_URL)}" rel="noreferrer">
              Open in OKF Explorer
            </a>
            <a class="button secondary" href="okf-explorer.json">
              View machine descriptor
            </a>
          </div>
        </div>
        <aside class="warning" aria-labelledby="warning-title">
          <h2 id="warning-title">Upstream usage boundary</h2>
          <p>{warning}</p>
        </aside>
      </div>
    </section>
    <section class="shell summary" aria-labelledby="summary-title">
      <div>
        <p class="eyebrow">Published snapshot</p>
        <h2 id="summary-title">What is represented</h2>
      </div>
      <dl class="cards">
        <div><dt>GET operations</dt><dd>{operation_count}</dd></div>
        <div><dt>Wiki pages</dt><dd>{snapshot["denominator"]["pageCount"]}</dd></div>
        <div><dt>Review findings</dt><dd>{len(register["issues"])}</dd></div>
        <div><dt>Snapshot</dt><dd class="text-value">{snapshot_id}</dd></div>
      </dl>
    </section>
    <section class="shell temporal" aria-labelledby="temporal-title">
      <p class="eyebrow">Snapshot versus live</p>
      <h2 id="temporal-title">Three dates, no implied live verification</h2>
      <dl class="cards temporal-cards">
        <div><dt>Bundle generated</dt><dd class="text-value">{generated_at}</dd></div>
        <div><dt>Wiki snapshot commit</dt><dd class="text-value">{wiki_commit}</dd></div>
        <div><dt>Reviewed develop commit</dt><dd class="text-value">{source_commit}</dd></div>
        <div><dt>Current live state</dt><dd class="text-value">Not checked</dd></div>
      </dl>
      <p>
        Drift findings compare the two pinned source surfaces only. They do not
        describe the current wiki, current <code>develop</code> branch or deployed API.
      </p>
    </section>
    <section class="shell files" aria-labelledby="files-title">
      <p class="eyebrow">Human and machine entrypoints</p>
      <h2 id="files-title">Use the evidence directly</h2>
      <div class="file-grid">
        <a href="index.md"><strong>OKF v0.2 Markdown</strong><span>Normative concept-tree entrypoint</span></a>
        <a href="data/standards/okf-v0.2.json"><strong>Conformance report</strong><span>Producer validation and trust/lifecycle counts</span></a>
        <a href="okf-explorer.json"><strong>OKF descriptor</strong><span>Portable OKF Explorer entrypoint</span></a>
        <a href="okf-bundle.jsonld"><strong>Semantic JSON-LD</strong><span>DCAT, Hydra and PROV representation</span></a>
        <a href="okf-bundle.yamlld"><strong>Semantic YAML-LD</strong><span>Byte-stable YAML 1.2 projection</span></a>
        <a href="data/openapi.json"><strong>OpenAPI review draft</strong><span>18 source-reviewed GET operations</span></a>
        <a href="data/review/issues.json"><strong>Drift register</strong><span>Wiki conflicts and documentation gaps</span></a>
        <a href="data/standards/terms.json"><strong>Governed terms</strong><span>Definitions, provenance and bounded application validation</span></a>
        <a href="data/standards/term-validation.json"><strong>Term validation</strong><span>Coverage and application checks for emitted terminology</span></a>
        <a href="data/coverage/ledger.json"><strong>Coverage ledger</strong><span>Bounded denominator and exclusions</span></a>
        <a href="checksums.json"><strong>Checksums</strong><span>Deterministic SHA-256 manifest</span></a>
      </div>
    </section>
  </main>
  <footer>
    <div class="shell">
      <p>No observation values, postcode results, boundaries, coordinates or credentials are stored.</p>
      <a href="https://github.com/chris-page-gov/okf-els-api">Source repository</a>
    </div>
  </footer>
</body>
</html>
"""


def landing_styles() -> str:
    return """* { box-sizing: border-box; }
:root {
  color-scheme: light;
  --ink: #16212d;
  --muted: #52616e;
  --paper: #f6f7f8;
  --white: #ffffff;
  --blue: #003c57;
  --cyan: #00a6a6;
  --purple: #6d3f8c;
  --line: #d7dee3;
  --warning: #fff4d6;
}
html { font-family: Arial, Helvetica, sans-serif; color: var(--ink); background: var(--paper); }
body { margin: 0; line-height: 1.5; }
a { color: var(--blue); }
a:focus, button:focus { outline: 3px solid #ffbf47; outline-offset: 3px; }
.shell { width: min(1120px, calc(100% - 2rem)); margin: 0 auto; }
.skip-link { position: absolute; left: -9999px; top: 0; padding: .75rem 1rem; background: var(--white); z-index: 10; }
.skip-link:focus { left: 1rem; top: 1rem; }
.site-header { color: var(--white); background: var(--blue); border-bottom: 5px solid var(--cyan); }
.header-inner { min-height: 5rem; display: flex; align-items: center; justify-content: space-between; gap: 2rem; }
.brand { display: flex; align-items: center; gap: .8rem; color: var(--white); text-decoration: none; }
.brand-mark { display: grid; place-items: center; width: 3rem; height: 3rem; font-weight: 800; color: var(--blue); background: var(--white); border-radius: .25rem; }
.brand strong, .brand small { display: block; }
.brand small { color: #d8edf1; }
nav { display: flex; flex-wrap: wrap; gap: 1.25rem; }
nav a { color: var(--white); font-weight: 700; }
.hero { padding: 5rem 0; color: var(--white); background: linear-gradient(120deg, #003c57 0%, #064d67 55%, #4d3063 100%); }
.hero-grid { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(18rem, .8fr); gap: 3rem; align-items: center; }
.eyebrow { margin: 0 0 .65rem; color: var(--cyan); font-size: .82rem; font-weight: 800; letter-spacing: .09em; text-transform: uppercase; }
.hero .eyebrow { color: #8ce3e3; }
h1 { max-width: 16ch; margin: 0; font-size: clamp(2.5rem, 6vw, 4.8rem); line-height: 1.02; letter-spacing: -.045em; }
h2 { margin: 0; font-size: clamp(1.7rem, 3vw, 2.35rem); line-height: 1.15; }
.lede { max-width: 42rem; margin: 1.5rem 0 0; color: #e2edf1; font-size: 1.2rem; }
.actions { display: flex; flex-wrap: wrap; gap: .8rem; margin-top: 2rem; }
.button { display: inline-block; padding: .85rem 1.2rem; border: 2px solid var(--white); border-radius: .2rem; font-weight: 800; text-decoration: none; }
.button.primary { color: var(--blue); background: var(--white); }
.button.secondary { color: var(--white); }
.warning { padding: 1.6rem; color: var(--ink); background: var(--warning); border-top: 6px solid #e8a900; box-shadow: 0 12px 34px rgb(0 0 0 / .18); }
.warning h2 { font-size: 1.25rem; }
.warning p { margin-bottom: 0; }
.summary, .temporal, .files { padding-top: 4rem; padding-bottom: 4rem; }
.cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin: 2rem 0 0; }
.cards div { min-width: 0; padding: 1.4rem; background: var(--white); border-top: 4px solid var(--purple); box-shadow: 0 2px 10px rgb(0 0 0 / .08); }
.cards dt { color: var(--muted); font-weight: 700; }
.cards dd { margin: .45rem 0 0; font-size: 2.3rem; font-weight: 800; }
.cards .text-value { overflow-wrap: anywhere; font-size: 1rem; }
.temporal { border-top: 1px solid var(--line); }
.temporal-cards div { border-top-color: var(--cyan); }
.temporal > p:last-child { max-width: 54rem; color: var(--muted); }
.files { border-top: 1px solid var(--line); }
.file-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-top: 2rem; }
.file-grid a { min-height: 8rem; padding: 1.35rem; color: var(--ink); background: var(--white); border: 1px solid var(--line); border-bottom: 4px solid var(--cyan); text-decoration: none; }
.file-grid a:hover { border-bottom-color: var(--purple); transform: translateY(-2px); }
.file-grid strong, .file-grid span { display: block; }
.file-grid span { margin-top: .55rem; color: var(--muted); }
footer { padding: 2.5rem 0; color: var(--white); background: var(--ink); }
footer .shell { display: flex; justify-content: space-between; gap: 2rem; }
footer a { color: var(--white); }
footer p { margin: 0; }
@media (max-width: 760px) {
  .header-inner, footer .shell { align-items: flex-start; flex-direction: column; padding: 1rem 0; }
  .hero { padding: 3.5rem 0; }
  .hero-grid { grid-template-columns: 1fr; }
  .cards { grid-template-columns: repeat(2, 1fr); }
  .file-grid { grid-template-columns: 1fr; }
}
@media (max-width: 440px) {
  .cards { grid-template-columns: 1fr; }
}
"""


def write_bundle(target: Path) -> None:
    register = read_object(REGISTER_PATH)
    snapshot = read_object(SNAPSHOT_PATH)
    publication = read_object(PUBLICATION_PATH)
    standards_source = read_object(STANDARDS_TERMS_PATH)
    validate_inputs(register, snapshot)
    validate_publication(publication)
    generated_at = publication["generatedAt"]
    writer = Writer(target)

    operations = operation_records(register, snapshot, generated_at)
    documents = document_records(snapshot)
    records = explorer_concept_records(
        register,
        snapshot,
        operations,
        documents,
    )
    resources = resource_records(register, operations)
    relationships = relationship_records(
        register,
        operations,
        documents,
        snapshot,
    )
    openapi = build_openapi(register, operations, snapshot)
    semantic = semantic_descriptor(
        register,
        operations,
        documents,
        snapshot,
        publication,
    )
    term_registry, term_validation = governed_terms(
        standards_source,
        snapshot_id=snapshot["snapshotId"],
        generated_at=generated_at,
        artifacts={
            "okf-bundle.yamlld": semantic,
            "data/datasets-0.json": records,
            "data/relationships-0.json": relationships,
        },
    )

    family_counts = Counter(record["topics"][0] for record in operations)
    issue_counts = Counter(
        issue["severity"] for issue in register["issues"]
    )
    publisher_counts = Counter(record["publisher"] for record in records)
    publishers = [
        {
            "id": "office-for-national-statistics",
            "name": "office-for-national-statistics",
            "title": "Office for National Statistics",
            "description": "Publisher of the Explore Local Statistics service and wiki.",
            "url": "https://www.ons.gov.uk/",
            "dataset_count": publisher_counts["office-for-national-statistics"],
            "resource_count": len(resources),
            "route": "publisher/office-for-national-statistics",
        },
        {
            "id": "okf-els-api-project",
            "name": "okf-els-api-project",
            "title": "OKF ELS API project",
            "description": "Publisher of the generated bounded review bundle and artifacts.",
            "url": "https://github.com/chris-page-gov/okf-els-api",
            "dataset_count": publisher_counts["okf-els-api-project"],
            "resource_count": 0,
            "route": "publisher/okf-els-api-project",
        },
    ]
    facets = explorer_facets(records)
    facet_analysis_rows = facet_analysis(records, facets)
    presentation = presentation_profile(snapshot["snapshotId"], facet_analysis_rows)
    search_manifest, search_outputs = static_search_index(
        records,
        resources,
        snapshot,
        generated_at,
    )
    result_documents = search_outputs["data/search/results-0.json"]
    analysis = {
        "schema": "okf-explorer-analysis.v1",
        "snapshot": snapshot["snapshotId"],
        "generated_at": generated_at,
        "source_bundle": PUBLISHED_DESCRIPTOR,
        "summary": {
            "title": "Explore Local Statistics API discovery",
            "description": (
                "A bounded metadata-only concept graph for the ELS API wiki and "
                "static application-source review."
            ),
            "record_count": len(records),
            "resource_count": len(resources),
            "relationship_count": len(relationships),
            "notices": [
                "No live service requests were performed.",
                register["policy"]["warning"],
            ],
        },
        "facet_analysis": facet_analysis_rows,
        "relationship_overview": {
            "types": [
                {
                    "kind": kind,
                    "count": count,
                    "samples": [
                        {
                            "source": relationship["source"],
                            "target": relationship["target"],
                            "label": relationship["label"],
                        }
                        for relationship in relationships
                        if relationship["kind"] == kind
                    ][:3],
                }
                for kind, count in sorted(
                    Counter(
                        relationship["kind"] for relationship in relationships
                    ).items()
                )
            ]
        },
        "narrative": {
            "title": "Bounded API discovery, not a service contract",
            "body": (
                "Explore the service, operations, pinned source documents, "
                "preserved review findings, generated artifacts and governed "
                "metadata terms. Evidence strength does not upgrade OKF "
                "verification trust or establish a live deployment state."
            ),
        },
    }
    overview = {
        "schema": "okf-els-api.overview.v1",
        "title": "Explore Local Statistics API discovery",
        "snapshot": snapshot["snapshotId"],
        "generated_at": generated_at,
        "status": register["status"],
        "counts": {
            "records": len(records),
            "operations": len(operations),
            "documents": len(documents),
            "formats": len(register["formats"]),
            "issues": len(register["issues"]),
            "datasets": len(records),
            "publishers": len(publishers),
            "resources": len(resources),
            "relationships": len(relationships),
            "governed_terms": term_registry["counts"]["standardsTerms"]
            + term_registry["counts"]["uiTerms"],
        },
        "top_publishers": [
            {
                "name": publisher["name"],
                "title": publisher["title"],
                "dataset_count": publisher["dataset_count"],
            }
            for publisher in publishers
        ],
        "recent_datasets": result_documents[:6],
        "format_counts": facets["format"],
        "facet_previews": facets,
        "notices": [
            "Metadata-only bundle; no live API requests or observation values are included.",
            register["policy"]["warning"],
        ],
        "familyCounts": dict(sorted(family_counts.items())),
        "issueSeverityCounts": dict(sorted(issue_counts.items())),
        "liveProbePerformed": False,
        "observationsIncluded": False,
        "warning": register["policy"]["warning"],
    }
    coverage = {
        "schema": "okf-els-api.coverage.v1",
        "snapshot": snapshot["snapshotId"],
        "status": "bounded-source-snapshot",
        "wiki": {
            "expected": snapshot["denominator"]["pageCount"],
            "represented": snapshot["denominator"]["representedPageCount"],
            "unrepresented": snapshot["denominator"]["unrepresentedPageCount"],
            "pageSetSha256": snapshot["denominator"]["pageSetSha256"],
            "completeForDeclaredFiles": True,
        },
        "implementationReview": {
            "handlerFiles": register["sourceVerification"]["routeHandlerCount"],
            "operationRecords": len(operations),
            "routeSetSha256": register["sourceVerification"]["routeSetSha256"],
            "completeForAllBehaviour": False,
        },
        "exclusions": [
            "Live API responses and production deployment verification",
            "Observation values and statistical cells",
            "Boundary geometries, postcode results and coordinates",
            "Credentials, cookies and personal information",
            "Historical routes and compatibility behaviour",
            "Complete response schema inference",
        ],
        "claim": (
            "Complete for the six declared wiki pages and the reviewed v1 GET route "
            "handler set only; not complete for all ELS behaviour or deployment state."
        ),
    }

    conformance = write_okf_markdown(
        writer,
        register,
        snapshot,
        publication,
        operations,
        documents,
        standards_source,
    )

    chunk_payloads = {
        "datasets": ("data/datasets-0.json", records),
        "publishers": ("data/publishers-0.json", publishers),
        "relationships": ("data/relationships-0.json", relationships),
        "resources": ("data/resources-0.json", resources),
    }
    manifest = {
        "schema": "okf-explorer-data-manifest.v1",
        "title": "Explore Local Statistics API discovery OKF",
        "snapshot": snapshot["snapshotId"],
        "generated_at": generated_at,
        "chunks": {
            key: [path] for key, (path, _payload) in chunk_payloads.items()
        },
        "shards": {
            key: [json_resource_reference(path, payload)]
            for key, (path, payload) in chunk_payloads.items()
        },
        "counts": {
            "datasets": len(records),
            "records": len(records),
            "operations": len(operations),
            "publishers": len(publishers),
            "relationships": len(relationships),
            "resources": len(resources),
        },
        "indexes": {
            "analysis": "data/analysis/overview.json",
            "coverage": "data/coverage/ledger.json",
            "documents": "data/documents-0.json",
            "facets": "data/facets.json",
            "formats": "data/formats.json",
            "openapi": "data/openapi.json",
            "overview": "data/overview.json",
            "parameters": "data/parameters.json",
            "presentation": "data/presentation.json",
            "review": "data/review/issues.json",
            "search": "data/search/manifest.json",
            "selection_contract": "data/selection-contract.json",
            "snapshot": "data/provenance/wiki-snapshot.json",
            "term_validation": "data/standards/term-validation.json",
            "terms": "data/standards/terms.json",
        },
        "search": {
            "schema": search_manifest["schema"],
            "documents": search_manifest["counts"]["documents"],
            "tokens": search_manifest["counts"]["tokens"],
            "result_limit": search_manifest["result_limit"],
        },
        "performance": {
            "startup_mode": "eager-small-corpus",
            "full_record_hydration": "single-chunk",
            "relationship_hydration": "single-chunk",
            "search": "static browser index",
        },
    }
    entrypoint_payloads = {
        "analysis_overview": ("data/analysis/overview.json", analysis),
        "conformance": ("data/standards/okf-v0.2.json", conformance),
        "data_manifest": ("data/manifest.json", manifest),
        "overview_index": ("data/overview.json", overview),
        "presentation": ("data/presentation.json", presentation),
        "search_manifest": ("data/search/manifest.json", search_manifest),
        "term_validation": (
            "data/standards/term-validation.json",
            term_validation,
        ),
        "terms": ("data/standards/terms.json", term_registry),
    }
    descriptor = {
        "@context": "https://chris-page-gov.github.io/okf-explorer/profile/bundle-wiki/v1/context.jsonld",
        "@id": PUBLISHED_DESCRIPTOR,
        "schema": "okf-explorer-large-corpus.v1",
        "profile": "https://chris-page-gov.github.io/okf-explorer/profile/bundle-wiki/v1/",
        "kind": "okf-large-corpus",
        "title": "Explore Local Statistics API discovery OKF",
        "description": register["description"],
        "version": BUNDLE_VERSION,
        "status": "bounded-review-draft",
        "snapshot": snapshot["snapshotId"],
        "generated_at": generated_at,
        "okf_version": OKF_VERSION,
        "core_conformance": "Markdown concept layer",
        "normative_entrypoint": "index.md",
        "publisher": "https://github.com/chris-page-gov/okf-els-api",
        "license": BUNDLE_LICENSE,
        "semantic_descriptor": "okf-bundle.yamlld",
        "performance": manifest["performance"],
        "counts": {
            "records": len(records),
            "datasets": len(records),
            "operations": len(operations),
            "resources": len(resources),
            "publishers": len(publishers),
            "relationships": len(relationships),
            "documents": len(documents),
            "formats": len(register["formats"]),
            "issues": len(register["issues"]),
            "governed_terms": term_registry["counts"]["standardsTerms"]
            + term_registry["counts"]["uiTerms"],
        },
        "entrypoints": {
            "analysis_overview": "data/analysis/overview.json",
            "coverage": "data/coverage/ledger.json",
            "conformance": "data/standards/okf-v0.2.json",
            "data_manifest": "data/manifest.json",
            "documents": "data/documents-0.json",
            "formats": "data/formats.json",
            "markdown_index": "index.md",
            "openapi": "data/openapi.json",
            "overview_index": "data/overview.json",
            "parameters": "data/parameters.json",
            "presentation": "data/presentation.json",
            "review": "data/review/issues.json",
            "search_manifest": "data/search/manifest.json",
            "selection_contract": "data/selection-contract.json",
            "snapshot": "data/provenance/wiki-snapshot.json",
            "semantic_jsonld": "okf-bundle.jsonld",
            "semantic_yamlld": "okf-bundle.yamlld",
            "term_validation": "data/standards/term-validation.json",
            "terms": "data/standards/terms.json",
            "viewer": "https://chris-page-gov.github.io/okf-explorer/",
        },
        "entrypoint_integrity": {
            key: json_resource_reference(path, payload)
            for key, (path, payload) in entrypoint_payloads.items()
        },
        "scope": {
            "metadata_only": True,
            "live_execution_included": False,
            "observations_included": False,
            "wiki_pages": snapshot["denominator"]["pageCount"],
            "api_operations": len(operations),
            "knowledge_concepts": len(records),
            "complete_for_declared_source_files": True,
            "complete_for_all_els_behaviour": False,
        },
        "source": {
            "title": snapshot["source"]["title"],
            "url": snapshot["source"]["url"],
            "wiki_commit": snapshot["source"]["commit"],
            "application_source_commit": register["sourceVerification"]["commit"],
            "verification_mode": register["sourceVerification"]["mode"],
        },
        "extensions": {
            "okf-v0.2": {
                "specification": OKF_SPECIFICATION,
                "normative_entrypoint": "index.md",
                "trust_model": "derived-from-verified",
                "attested_computation_execution": "not-included",
            },
            "okf-explorer-analysis.v1": {
                "entrypoint": "analysis_overview",
                "mode": "external",
            },
            "okf-explorer-presentation.v1": {
                "entrypoint": "presentation",
                "mode": "external",
            },
            "okf-semantic-model.v1": {
                "status": "experimental",
                "term_registry": "terms",
                "validation_report": "term_validation",
                "validation_model": (
                    "recognition-provenance-kind-and-bounded-application"
                ),
                "live_vocabulary_lookup_performed": False,
            },
            "okf-api-discovery.v1": {
                "openapi": "openapi",
                "selection_contract": "selection_contract",
                "execution_included": False,
                "read_only_documented_method": "GET",
            },
            "okf-documentation-review.v1": {
                "review": "review",
                "conflicts_preserved": True,
                "live_probe_performed": False,
            },
            "okf-pages-publication.v1": {
                "site": PAGES_ROOT,
                "descriptor": PUBLISHED_DESCRIPTOR,
                "explorer": EXPLORER_URL,
            },
        },
        "vocabulary": {
            "record_singular": "knowledge concept",
            "record_plural": "knowledge concepts",
            "resource_singular": "endpoint template",
            "resource_plural": "endpoint templates",
            "publisher_singular": "publisher",
            "publisher_plural": "publishers",
            "search_placeholder": (
                "Search operations, documents, findings, artifacts and standards terms"
            ),
        },
        "warning": register["policy"]["warning"],
        "publication": {
            "site": PAGES_ROOT,
            "descriptor": PUBLISHED_DESCRIPTOR,
            "okf_explorer": EXPLORER_URL,
        },
    }
    context = {
        "@context": {
            "dcat": "http://www.w3.org/ns/dcat#",
            "dct": "http://purl.org/dc/terms/",
            "foaf": "http://xmlns.com/foaf/0.1/",
            "hydra": "http://www.w3.org/ns/hydra/core#",
            "okf": "https://chris-page-gov.github.io/okf-explorer/vocab/",
            "prov": "http://www.w3.org/ns/prov#",
        }
    }

    writer.write_json("okf-explorer.json", descriptor)
    writer.write_json("okf-bundle.jsonld", semantic)
    # JSON is a strict YAML 1.2 subset, making this a byte-stable YAML-LD
    # projection without introducing a runtime YAML dependency.
    writer.write_json("okf-bundle.yamlld", semantic)
    writer.write_json("context/okf-els-api.jsonld", context)
    writer.write_json("data/datasets-0.json", records)
    writer.write_json("data/documents-0.json", documents)
    writer.write_json("data/formats.json", register["formats"])
    writer.write_json("data/parameters.json", register["parameters"])
    writer.write_json("data/publishers-0.json", publishers)
    writer.write_json("data/relationships-0.json", relationships)
    writer.write_json("data/resources-0.json", resources)
    writer.write_json("data/overview.json", overview)
    writer.write_json("data/analysis/overview.json", analysis)
    writer.write_json("data/manifest.json", manifest)
    writer.write_json("data/facets.json", facets)
    writer.write_json("data/presentation.json", presentation)
    writer.write_json("data/coverage/ledger.json", coverage)
    writer.write_json("data/openapi.json", openapi)
    writer.write_json("data/provenance/wiki-snapshot.json", snapshot)
    writer.write_json("data/review/issues.json", register["issues"])
    writer.write_json("data/standards/terms.json", term_registry)
    writer.write_json("data/standards/term-validation.json", term_validation)
    writer.write_json("data/standards/okf-v0.2.json", conformance)
    writer.write_json("data/selection-contract.json", selection_contract(register))
    for path, payload in search_outputs.items():
        writer.write_json(path, payload)
    writer.write_text(
        "index.html",
        landing_page(register, snapshot, publication, len(operations)),
    )
    writer.write_text("site.css", landing_styles())
    writer.write_text(".nojekyll", "")
    writer.write_json("checksums.json", writer.checksum_manifest())


def directory_bytes(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and path.name != ".DS_Store"
    }


def safe_output_path(requested: Path) -> Path:
    """Resolve a build destination while refusing broad or source-tree targets."""

    expanded = requested.expanduser()
    if expanded.is_symlink():
        raise BuildError(f"Refusing symlink output path: {requested}")
    output = expanded.resolve()
    repository = ROOT.resolve()
    default_output = DEFAULT_OUTPUT.resolve()
    if output == Path(output.anchor) or output == Path.home().resolve():
        raise BuildError(f"Refusing broad output path: {output}")
    if output == repository or output in repository.parents:
        raise BuildError(f"Refusing repository or ancestor output path: {output}")
    if output != default_output and output.is_relative_to(repository):
        raise BuildError(
            "Custom output paths must be outside the repository; "
            f"refusing to replace {output}"
        )
    return output


def build(output: Path, check: bool) -> None:
    output = safe_output_path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".okf-els-api-", dir=output.parent) as temp:
        candidate = Path(temp) / "bundle"
        candidate.mkdir()
        write_bundle(candidate)
        if check:
            expected = directory_bytes(candidate)
            actual = directory_bytes(output)
            if expected != actual:
                missing = sorted(set(expected) - set(actual))
                extra = sorted(set(actual) - set(expected))
                changed = sorted(
                    path
                    for path in set(expected) & set(actual)
                    if expected[path] != actual[path]
                )
                raise BuildError(
                    "Generated bundle differs "
                    f"(missing={missing}, extra={extra}, changed={changed})"
                )
            return
        if output.is_symlink():
            raise BuildError(f"Refusing symlink output path: {output}")
        if output.exists():
            shutil.rmtree(output)
        shutil.copytree(candidate, output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        build(args.output, args.check)
    except (BuildError, OKFConformanceError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    action = "verified" if args.check else "built"
    print(f"{action}: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
