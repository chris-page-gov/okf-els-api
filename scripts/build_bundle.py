#!/usr/bin/env python3
"""Build a deterministic, metadata-only OKF bundle for the ELS API wiki."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "bundle"
REGISTER_PATH = ROOT / "source" / "api-register.json"
SNAPSHOT_PATH = ROOT / "source" / "wiki-snapshot.json"
PAGES_ROOT = "https://chris-page-gov.github.io/okf-els-api/"
PUBLISHED_DESCRIPTOR = f"{PAGES_ROOT}okf-explorer.json"
EXPLORER_ROOT = "https://chris-page-gov.github.io/okf-explorer/"
EXPLORER_URL = f"{EXPLORER_ROOT}?bundle={quote(PUBLISHED_DESCRIPTOR, safe='')}"


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


def operation_records(
    register: dict[str, Any],
    snapshot: dict[str, Any],
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
                "dcat_type": "hydra:Operation",
                "source_surface": "els-api-wiki",
                "source_adapter": "wiki-and-static-source-review",
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
                "license_title": "MIT (associated application repository)",
                "license_source_id": snapshot["licenceEvidence"]["url"],
                "metadata_modified": snapshot["source"]["commitDate"],
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
            "record_type": "Wiki documentation page",
            "url": page["url"],
            "file": page["file"],
            "sha256": page["sha256"],
            "lines": page["lines"],
            "bytes": page["bytes"],
            "source_commit": snapshot["source"]["commit"],
            "retrieved_at": snapshot["retrievedAt"],
            "license_evidence": snapshot["licenceEvidence"],
        }
        for page in snapshot["pages"]
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
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        rows.append(
            {
                "kind": "has-operation",
                "source": "service/els-api",
                "target": record["route"],
                "confidence": "declared",
                "evidence_type": "wiki-and-static-source-review",
            }
        )
        rows.append(
            {
                "kind": "documented-by",
                "source": record["route"],
                "target": f"document/{record['documentation'].rsplit('/', 1)[-1]}",
                "confidence": "declared",
                "evidence_type": "wiki-page-reference",
            }
        )
        for issue in record["issues"]:
            rows.append(
                {
                    "kind": "has-documentation-issue",
                    "source": record["route"],
                    "target": f"issue/{issue['id']}",
                    "confidence": "observed",
                    "evidence_type": "wiki-source-comparison",
                }
            )
    for issue in register["issues"]:
        if issue["id"] == "boundary-internal-api":
            rows.append(
                {
                    "kind": "has-usage-boundary",
                    "source": "service/els-api",
                    "target": f"issue/{issue['id']}",
                    "confidence": "declared",
                    "evidence_type": "wiki-warning",
                }
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
                "name": "MIT (associated application repository)",
                "url": snapshot["licenceEvidence"]["url"],
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
        },
    }


def semantic_descriptor(
    register: dict[str, Any],
    records: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    operations = [
        {
            "@id": f"urn:okf:els-api:operation:{record['native_id']}",
            "@type": "hydra:Operation",
            "hydra:method": "GET",
            "dct:title": record["title"],
            "dct:description": record["description"],
            "hydra:expects": {
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
            "@id": "https://www.ons.gov.uk/",
            "@type": "foaf:Agent",
            "foaf:name": "Office for National Statistics",
        },
        "dct:issued": snapshot["retrievedAt"],
        "dct:license": {"@id": snapshot["licenceEvidence"]["url"]},
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
                "dcat:endpointURL": {"@id": register["baseUrl"]},
                "dcat:endpointDescription": {"@id": snapshot["source"]["url"]},
                "hydra:supportedOperation": operations,
                "okf:status": register["status"],
                "okf:executionIncluded": False,
                "okf:observationsIncluded": False,
            }
        ],
        "dcat:record": [
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
    }


def facet_rows(values: list[str]) -> list[dict[str, Any]]:
    return [
        {"value": value, "label": value, "count": count}
        for value, count in sorted(Counter(values).items())
    ]


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


def landing_page(
    register: dict[str, Any],
    snapshot: dict[str, Any],
    operation_count: int,
) -> str:
    warning = html.escape(register["policy"]["warning"])
    snapshot_id = html.escape(snapshot["snapshotId"])
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
    <section class="shell files" aria-labelledby="files-title">
      <p class="eyebrow">Human and machine entrypoints</p>
      <h2 id="files-title">Use the evidence directly</h2>
      <div class="file-grid">
        <a href="okf-explorer.json"><strong>OKF descriptor</strong><span>Portable OKF Explorer entrypoint</span></a>
        <a href="okf-bundle.jsonld"><strong>Semantic JSON-LD</strong><span>DCAT, Hydra and PROV representation</span></a>
        <a href="data/openapi.json"><strong>OpenAPI review draft</strong><span>18 source-reviewed GET operations</span></a>
        <a href="data/review/issues.json"><strong>Drift register</strong><span>Wiki conflicts and documentation gaps</span></a>
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
.summary, .files { padding-top: 4rem; padding-bottom: 4rem; }
.cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin: 2rem 0 0; }
.cards div { min-width: 0; padding: 1.4rem; background: var(--white); border-top: 4px solid var(--purple); box-shadow: 0 2px 10px rgb(0 0 0 / .08); }
.cards dt { color: var(--muted); font-weight: 700; }
.cards dd { margin: .45rem 0 0; font-size: 2.3rem; font-weight: 800; }
.cards .text-value { overflow-wrap: anywhere; font-size: 1rem; }
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
    validate_inputs(register, snapshot)
    writer = Writer(target)
    records = operation_records(register, snapshot)
    documents = document_records(snapshot)
    resources = resource_records(register, records)
    relationships = relationship_records(register, records)
    openapi = build_openapi(register, records, snapshot)
    family_counts = Counter(record["topics"][0] for record in records)
    issue_counts = Counter(
        issue["severity"] for issue in register["issues"]
    )
    publisher = {
        "id": "office-for-national-statistics",
        "name": "office-for-national-statistics",
        "title": "Office for National Statistics",
        "description": "Publisher of the Explore Local Statistics service.",
        "url": "https://www.ons.gov.uk/",
        "dataset_count": len(records),
        "resource_count": len(resources),
        "route": "publisher/office-for-national-statistics",
    }
    overview = {
        "schema": "okf-els-api.overview.v1",
        "title": "Explore Local Statistics API discovery",
        "snapshot": snapshot["snapshotId"],
        "generated_at": snapshot["retrievedAt"],
        "status": register["status"],
        "counts": {
            "operations": len(records),
            "documents": len(documents),
            "formats": len(register["formats"]),
            "issues": len(register["issues"]),
            "resources": len(resources),
            "relationships": len(relationships),
        },
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
            "operationRecords": len(records),
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
    manifest = {
        "schema": "okf-explorer-data-manifest.v1",
        "title": "Explore Local Statistics API discovery OKF",
        "snapshot": snapshot["snapshotId"],
        "generated_at": snapshot["retrievedAt"],
        "chunks": {
            "datasets": ["data/datasets-0.json"],
            "publishers": ["data/publishers-0.json"],
            "relationships": ["data/relationships-0.json"],
            "resources": ["data/resources-0.json"],
        },
        "counts": {
            "datasets": len(records),
            "records": len(records),
            "publishers": 1,
            "relationships": len(relationships),
            "resources": len(resources),
        },
        "indexes": {
            "coverage": "data/coverage/ledger.json",
            "documents": "data/documents-0.json",
            "facets": "data/facets.json",
            "formats": "data/formats.json",
            "openapi": "data/openapi.json",
            "overview": "data/overview.json",
            "parameters": "data/parameters.json",
            "review": "data/review/issues.json",
            "selection_contract": "data/selection-contract.json",
            "snapshot": "data/provenance/wiki-snapshot.json",
        },
        "performance": {
            "startup_mode": "eager-small-corpus",
            "full_record_hydration": "single-chunk",
        },
    }
    facets = {
        "family": facet_rows([record["topics"][0] for record in records]),
        "format": facet_rows(
            [format_id for record in records for format_id in record["formats"]]
        ),
        "has_documentation_issues": facet_rows(
            ["yes" if record["issues"] else "no" for record in records]
        ),
        "state": facet_rows([record["state"] for record in records]),
    }
    descriptor = {
        "@context": "https://chris-page-gov.github.io/okf-explorer/profile/bundle-wiki/v1/context.jsonld",
        "@id": PUBLISHED_DESCRIPTOR,
        "schema": "okf-explorer-large-corpus.v1",
        "profile": "https://chris-page-gov.github.io/okf-explorer/profile/bundle-wiki/v1/",
        "kind": "okf-small-api-corpus",
        "title": "Explore Local Statistics API discovery OKF",
        "description": register["description"],
        "version": "0.1.0",
        "status": "bounded-review-draft",
        "snapshot": snapshot["snapshotId"],
        "generated_at": snapshot["retrievedAt"],
        "publisher": "https://www.ons.gov.uk/",
        "license": snapshot["licenceEvidence"]["url"],
        "semantic_descriptor": "okf-bundle.jsonld",
        "counts": {
            "records": len(records),
            "datasets": len(records),
            "resources": len(resources),
            "publishers": 1,
            "relationships": len(relationships),
            "documents": len(documents),
            "formats": len(register["formats"]),
            "issues": len(register["issues"]),
        },
        "entrypoints": {
            "coverage": "data/coverage/ledger.json",
            "data_manifest": "data/manifest.json",
            "documents": "data/documents-0.json",
            "formats": "data/formats.json",
            "openapi": "data/openapi.json",
            "overview_index": "data/overview.json",
            "parameters": "data/parameters.json",
            "review": "data/review/issues.json",
            "selection_contract": "data/selection-contract.json",
            "snapshot": "data/provenance/wiki-snapshot.json",
            "viewer": "https://chris-page-gov.github.io/okf-explorer/",
        },
        "scope": {
            "metadata_only": True,
            "live_execution_included": False,
            "observations_included": False,
            "wiki_pages": snapshot["denominator"]["pageCount"],
            "api_operations": len(records),
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
            "record_singular": "API operation",
            "record_plural": "API operations",
            "resource_singular": "endpoint template",
            "resource_plural": "endpoint templates",
            "publisher_singular": "publisher",
            "publisher_plural": "publishers",
            "search_placeholder": "Search routes, parameters, formats and geography operations",
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
    writer.write_json(
        "okf-bundle.jsonld",
        semantic_descriptor(register, records, documents, snapshot),
    )
    writer.write_json("context/okf-els-api.jsonld", context)
    writer.write_json("data/datasets-0.json", records)
    writer.write_json("data/documents-0.json", documents)
    writer.write_json("data/formats.json", register["formats"])
    writer.write_json("data/parameters.json", register["parameters"])
    writer.write_json("data/publishers-0.json", [publisher])
    writer.write_json("data/relationships-0.json", relationships)
    writer.write_json("data/resources-0.json", resources)
    writer.write_json("data/overview.json", overview)
    writer.write_json("data/manifest.json", manifest)
    writer.write_json("data/facets.json", facets)
    writer.write_json("data/coverage/ledger.json", coverage)
    writer.write_json("data/openapi.json", openapi)
    writer.write_json("data/provenance/wiki-snapshot.json", snapshot)
    writer.write_json("data/review/issues.json", register["issues"])
    writer.write_json("data/selection-contract.json", selection_contract(register))
    writer.write_text("index.html", landing_page(register, snapshot, len(records)))
    writer.write_text("site.css", landing_styles())
    writer.write_text(".nojekyll", "")
    writer.write_text(
        "index.md",
        (
            "# Explore Local Statistics API discovery OKF\n\n"
            f"{register['policy']['warning']}\n\n"
            "Open `okf-explorer.json` in OKF Explorer. Review "
            "`data/review/issues.json` before using the generated OpenAPI draft.\n"
        ),
    )
    writer.write_json("checksums.json", writer.checksum_manifest())


def directory_bytes(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and path.name != ".DS_Store"
    }


def build(output: Path, check: bool) -> None:
    output = output.resolve()
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
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    action = "verified" if args.check else "built"
    print(f"{action}: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
