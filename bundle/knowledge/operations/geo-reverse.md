---
type: "API Endpoint"
title: "Reverse geographic lookup"
description: "Return areas containing a longitude and latitude."
resource: "https://www.ons.gov.uk/explore-local-statistics/api/v1/geo/reverse"
tags: ["api","get","geography","internal-private-unstable"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-11-25T00:00:00Z"}
sources: [{"id":"wiki-page","resource":"https://github.com/ONSdigital/explore-local-statistics-app/wiki/Requesting-geographic-information","title":"Requesting geographic information","pinned_commit":"3da822e28d775f1213d328573da34aba8278d79f","revision_at":"2026-07-20T12:17:57+01:00","last_modified":"2026-07-20","sha256":"7eb059867836b105e6bde9aeb5eb7bf81952f6fc1c0c1ebe907c07871c388ba5"},{"id":"route-handler","resource":"https://github.com/ONSdigital/explore-local-statistics-app/blob/795eaf204f47986f6be248a63f857a42afe4fdf2/src/routes/(api)/api/v1/geo/reverse/+server.ts","title":"Reviewed application route handler","pinned_commit":"795eaf204f47986f6be248a63f857a42afe4fdf2","revision_at":"2026-07-17T09:35:03+01:00","last_modified":"2026-07-17"}]
method: "GET"
path_template: "/api/v1/geo/reverse"
documented_path_template: "/api/v1/geo/reverse"
snapshot_mode: "frozen"
live_status: "not-checked"
execution_included: false
---

# Route

`GET /api/v1/geo/reverse`

Parameters represented by the bounded review: `lng`, `lat`, `year`, `geoLevel`, `groupByLevel`.

# Parameter evidence

* `lng`: Longitude for reverse lookup.
* `lat`: Latitude for reverse lookup.
* `year`: Geography validity year or all/latest where supported. Recorded default: `latest`.
* `geoLevel`: One or more geography-level keys, such as ltla or rgn. Recorded default: `all`.
* `groupByLevel`: Group returned areas by geography level. Recorded default: `false`.

Source page: [Requesting geographic information](../documents/Requesting-geographic-information.md).

# Preserved review findings

* [includeDates is documented where handlers reject it](../issues/drift-geo-includedates.md) (high)

# Usage boundary

The upstream wiki says this API is internal/private, is not intended for non-ONS web applications, may change without notice, and prevents cross-origin browser requests. This concept is descriptive and does not authorise execution.
