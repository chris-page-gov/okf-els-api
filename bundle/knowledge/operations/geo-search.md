---
type: "API Endpoint"
title: "Search areas by name"
description: "Search area names and optionally fall back to postcode autocomplete."
resource: "https://www.ons.gov.uk/explore-local-statistics/api/v1/geo/search/{name}"
tags: ["api","get","geography","internal-private-unstable"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-11-25T00:00:00Z"}
sources: [{"id":"wiki-page","resource":"https://github.com/ONSdigital/explore-local-statistics-app/wiki/Requesting-geographic-information","title":"Requesting geographic information","pinned_commit":"3da822e28d775f1213d328573da34aba8278d79f","revision_at":"2026-07-20T12:17:57+01:00","last_modified":"2026-07-20","sha256":"7eb059867836b105e6bde9aeb5eb7bf81952f6fc1c0c1ebe907c07871c388ba5"},{"id":"route-handler","resource":"https://github.com/ONSdigital/explore-local-statistics-app/blob/795eaf204f47986f6be248a63f857a42afe4fdf2/src/routes/(api)/api/v1/geo/search/[name]/+server.ts","title":"Reviewed application route handler","pinned_commit":"795eaf204f47986f6be248a63f857a42afe4fdf2","revision_at":"2026-07-17T09:35:03+01:00","last_modified":"2026-07-17"}]
method: "GET"
path_template: "/api/v1/geo/search/{name}"
documented_path_template: "/api/v1/geo/search/{string}"
snapshot_mode: "frozen"
live_status: "not-checked"
execution_included: false
---

# Route

`GET /api/v1/geo/search/{name}`

Parameters represented by the bounded review: `name`, `year`, `limit`, `offset`, `searchPostcodes`, `groupByLevel`, `geoLevel`.

# Parameter evidence

* `name`: Area-name search string.
* `year`: Geography validity year or all/latest where supported. Recorded default: `latest`.
* `limit`: Maximum number of search results. Recorded default: `10`.
* `offset`: Zero-based result offset. Recorded default: `0`.
* `searchPostcodes`: Fall back to postcode results when no area name matches. Recorded default: `false`.
* `groupByLevel`: Group returned areas by geography level. Recorded default: `false`.
* `geoLevel`: One or more geography-level keys, such as ltla or rgn. Recorded default: `all`.

Source page: [Requesting geographic information](../documents/Requesting-geographic-information.md).

# Preserved review findings

* [includeDates is documented where handlers reject it](../issues/drift-geo-includedates.md) (high)

# Usage boundary

The upstream wiki says this API is internal/private, is not intended for non-ONS web applications, may change without notice, and prevents cross-origin browser requests. This concept is descriptive and does not authorise execution.
