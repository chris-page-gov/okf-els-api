---
type: "API Endpoint"
title: "List geographic areas"
description: "List names, codes and selected metadata for geographies represented in ELS."
resource: "https://www.ons.gov.uk/explore-local-statistics/api/v1/geo/list"
tags: ["api","get","geography","internal-private-unstable"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-11-25T00:00:00Z"}
sources: [{"id":"wiki-page","resource":"https://github.com/ONSdigital/explore-local-statistics-app/wiki/Requesting-geographic-information","title":"Requesting geographic information","pinned_commit":"3da822e28d775f1213d328573da34aba8278d79f","revision_at":"2026-07-20T12:17:57+01:00","last_modified":"2026-07-20","sha256":"7eb059867836b105e6bde9aeb5eb7bf81952f6fc1c0c1ebe907c07871c388ba5"},{"id":"route-handler","resource":"https://github.com/ONSdigital/explore-local-statistics-app/blob/795eaf204f47986f6be248a63f857a42afe4fdf2/src/routes/(api)/api/v1/geo/list/+server.ts","title":"Reviewed application route handler","pinned_commit":"795eaf204f47986f6be248a63f857a42afe4fdf2","revision_at":"2026-07-17T09:35:03+01:00","last_modified":"2026-07-17"}]
method: "GET"
path_template: "/api/v1/geo/list"
documented_path_template: "/api/v1/geo/list"
snapshot_mode: "frozen"
live_status: "not-checked"
execution_included: false
---

# Route

`GET /api/v1/geo/list`

Parameters represented by the bounded review: `geo`, `geoExtent`, `year`, `indicator`, `asLookup`, `groupByLevel`, `includeParents`, `includeChildren`, `includeDates`, `includeLevel`.

# Parameter evidence

* `geo`: One or more comma-separated geography-level keys or GSS codes. Recorded default: `all`.
* `geoExtent`: Parent GSS code used to constrain returned geographies. Recorded default: `all`.
* `year`: Geography validity year or all/latest where supported. Recorded default: `latest`.
* `indicator`: One or more comma-separated indicator slugs, or all. Recorded default: `all`.
* `asLookup`: Return an object keyed by identifier instead of an array. Recorded default: `false`.
* `groupByLevel`: Group returned areas by geography level. Recorded default: `false`.
* `includeParents`: Include parent GSS codes. Recorded default: `false`.
* `includeChildren`: Include child GSS codes. Recorded default: `false`.
* `includeDates`: Include area start and end dates. Recorded default: `false`.
* `includeLevel`: Include the geography-level code. Recorded default: `false`.

Source page: [Requesting geographic information](../documents/Requesting-geographic-information.md).

# Preserved review findings

* No registered issue is attached to this operation.

# Usage boundary

The upstream wiki says this API is internal/private, is not intended for non-ONS web applications, may change without notice, and prevents cross-origin browser requests. This concept is descriptive and does not authorise execution.
