"""Dependency-free OKF 0.3 Markdown rendering and ELS producer validation."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path
from typing import Any

OKF_VERSION = "0.3"
OKF_SPEC_COMMIT = "527e81aff55992be21507e97004286789126f88c"
OKF_SPECIFICATION = (
    "https://github.com/open-knowledge-format/open-knowledge-format/blob/"
    f"{OKF_SPEC_COMMIT}/SPEC.md"
)
_ACTOR = re.compile(r"^(?:(?:human|process):[^\s:]+|[^/\s:]+/[^/\s]+)$")
_DATE_HEADING = re.compile(r"^## (\d{4}-\d{2}-\d{2})$", re.MULTILINE)


class OKFConformanceError(ValueError):
    """Raised when an ELS OKF 0.3 Markdown projection is invalid."""


def render_frontmatter(fields: Mapping[str, Any]) -> str:
    """Render deterministic JSON-valued YAML 1.2 frontmatter."""

    rows = ["---"]
    for key, value in fields.items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", key):
            raise OKFConformanceError(f"unsafe frontmatter key: {key}")
        rows.append(
            f"{key}: "
            + json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    rows.append("---")
    return "\n".join(rows) + "\n"


def render_concept(fields: Mapping[str, Any], body: str) -> str:
    """Render one Markdown concept without changing its authored field values."""

    return render_frontmatter(fields) + "\n" + body.strip() + "\n"


def parse_document(path: Path) -> tuple[dict[str, Any] | None, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None, text
    closing = text.find("---\n", 4)
    if closing < 0:
        raise OKFConformanceError(f"{path}: frontmatter is not closed")
    fields: dict[str, Any] = {}
    for line_number, line in enumerate(text[4:closing].splitlines(), start=2):
        key, separator, encoded = line.partition(":")
        if not separator or not key or not encoded.strip():
            raise OKFConformanceError(
                f"{path}:{line_number}: expected one key and JSON value"
            )
        try:
            value = json.loads(encoded.strip())
        except json.JSONDecodeError as exc:
            raise OKFConformanceError(
                f"{path}:{line_number}: frontmatter is not valid JSON-valued YAML"
            ) from exc
        if key in fields:
            raise OKFConformanceError(f"{path}:{line_number}: duplicate field {key!r}")
        fields[key] = value
    return fields, text[closing + 4 :]


def _date(value: Any, label: str) -> None:
    if not isinstance(value, str):
        raise OKFConformanceError(f"{label} must be an ISO 8601 date")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise OKFConformanceError(f"{label} must be an ISO 8601 date") from exc


def _datetime(value: Any, label: str) -> None:
    if not isinstance(value, str) or "T" not in value:
        raise OKFConformanceError(f"{label} must be an ISO 8601 datetime")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OKFConformanceError(f"{label} must be an ISO 8601 datetime") from exc
    if parsed.tzinfo is None:
        raise OKFConformanceError(f"{label} must include a timezone")


def validate_okf_bundle(root: Path) -> dict[str, Any]:
    """Validate the root declaration and generated ELS 0.3 concept layer."""

    root = root.resolve()
    markdown_paths = sorted(root.rglob("*.md"))
    root_index = root / "index.md"
    if not root_index.is_file():
        raise OKFConformanceError("bundle root index.md is required")

    concept_paths: list[str] = []
    lifecycle = {"draft": 0, "stable": 0, "deprecated": 0}
    for path in markdown_paths:
        relative = path.relative_to(root).as_posix()
        fields, body = parse_document(path)
        if path.name == "index.md":
            if path == root_index:
                if fields != {"okf_version": OKF_VERSION}:
                    raise OKFConformanceError(
                        "root index.md must declare only okf_version 0.3"
                    )
            elif fields is not None:
                raise OKFConformanceError(
                    f"{relative}: subordinate index.md must not have frontmatter"
                )
            if not re.search(r"\[[^\]]+\]\([^)]+\)", body):
                raise OKFConformanceError(f"{relative}: navigation index requires a link")
            continue
        if path.name == "log.md":
            if fields is not None:
                raise OKFConformanceError(f"{relative}: log.md must not have frontmatter")
            dates = _DATE_HEADING.findall(body)
            if not dates or dates != sorted(dates, reverse=True):
                raise OKFConformanceError(
                    f"{relative}: log.md needs newest-first ISO 8601 date headings"
                )
            for value in dates:
                _date(value, f"{relative}: log heading")
            continue

        if fields is None:
            raise OKFConformanceError(f"{relative}: concept frontmatter is required")
        if not isinstance(fields.get("type"), str) or not fields["type"].strip():
            raise OKFConformanceError(f"{relative}: non-empty type is required")
        for required in ("title", "description"):
            if not isinstance(fields.get(required), str) or not fields[required].strip():
                raise OKFConformanceError(f"{relative}: non-empty {required} is required")
        generated = fields.get("generated")
        if not isinstance(generated, Mapping) or not generated.get("by"):
            raise OKFConformanceError(f"{relative}: generated.by is required")
        if not isinstance(generated["by"], str) or not _ACTOR.fullmatch(generated["by"]):
            raise OKFConformanceError(f"{relative}: generated.by is not an OKF actor")
        _datetime(generated.get("at"), f"{relative}: generated.at")
        sources = fields.get("sources")
        if not isinstance(sources, list) or not sources:
            raise OKFConformanceError(f"{relative}: at least one source is required")
        source_ids: list[str] = []
        for index, source in enumerate(sources):
            if not isinstance(source, Mapping):
                raise OKFConformanceError(f"{relative}: sources[{index}] must be an object")
            if not isinstance(source.get("id"), str) or not source["id"].strip():
                raise OKFConformanceError(f"{relative}: sources[{index}].id is required")
            if not isinstance(source.get("resource"), str) or not source["resource"].strip():
                raise OKFConformanceError(
                    f"{relative}: sources[{index}].resource is required"
                )
            source_ids.append(source["id"])
            if source.get("last_modified") is not None:
                _date(source["last_modified"], f"{relative}: sources[{index}].last_modified")
        if len(source_ids) != len(set(source_ids)):
            raise OKFConformanceError(f"{relative}: source IDs must be unique")
        status = fields.get("status")
        if status not in lifecycle:
            raise OKFConformanceError(f"{relative}: explicit lifecycle status is required")
        if "verified" in fields:
            raise OKFConformanceError(
                f"{relative}: this frozen review contains no verification events"
            )
        if fields.get("stale_after") is not None:
            _date(fields["stale_after"], f"{relative}: stale_after")
        if not body.strip():
            raise OKFConformanceError(f"{relative}: concept body must not be empty")
        concept_paths.append(relative)
        lifecycle[status] += 1

    return {
        "schema": "okf-els-api.okf-conformance.v3",
        "specification": {"version": OKF_VERSION, "resource": OKF_SPECIFICATION},
        "entrypoint": "index.md",
        "status": "conformant",
        "conceptCount": len(concept_paths),
        "conceptPaths": concept_paths,
        "markdownDocumentCount": len(markdown_paths),
        "trustTiers": {
            "humanReviewed": 0,
            "machineConfirmed": 0,
            "unverified": len(concept_paths),
        },
        "lifecycle": lifecycle,
        "producerProfile": "okf-els-api.producer-profile.v2",
        "allConceptsRemainUnverified": True,
        "sourceSnapshotMode": "frozen",
    }
