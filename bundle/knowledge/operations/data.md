---
type: "API Endpoint"
title: "Filter and download statistical data"
description: "Filter one or more indicators by topic, geography, time, dimensions and measures."
resource: "https://www.ons.gov.uk/explore-local-statistics/api/v1/data.{format}"
tags: ["api","get","data","internal-private-unstable"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-11-25T00:00:00Z"}
sources: [{"id":"wiki-page","resource":"https://github.com/ONSdigital/explore-local-statistics-app/wiki/Requesting-data","title":"Requesting data","pinned_commit":"3da822e28d775f1213d328573da34aba8278d79f","revision_at":"2026-07-20T12:17:57+01:00","last_modified":"2026-07-20","sha256":"f15cc3eddb662a7b3e578a68cf7ce644ae8c2d8a39f06a047d7580f36d8643b7"},{"id":"route-handler","resource":"https://github.com/ONSdigital/explore-local-statistics-app/blob/795eaf204f47986f6be248a63f857a42afe4fdf2/src/routes/(api)/api/v1/data.[format]/+server.ts","title":"Reviewed application route handler","pinned_commit":"795eaf204f47986f6be248a63f857a42afe4fdf2","revision_at":"2026-07-17T09:35:03+01:00","last_modified":"2026-07-17"}]
method: "GET"
path_template: "/api/v1/data.{format}"
documented_path_template: "/api/v1/data.{format}"
snapshot_mode: "frozen"
live_status: "not-checked"
execution_included: false
---

# Route

`GET /api/v1/data.{format}`

Parameters represented by the bounded review: `format`, `topic`, `indicator`, `excludeMultivariate`, `time`, `timeNearest`, `geo`, `geoExtent`, `geoCluster`, `hasGeo`, `dimension_{code}`, `measure`, `includeNames`, `includeStatus`.

# Parameter evidence

* `format`: Path value for format.
* `topic`: One or more comma-separated topic or sub-topic codes, or all. Recorded default: `all`.
* `indicator`: One or more comma-separated indicator slugs, or all. Recorded default: `all`.
* `excludeMultivariate`: Exclude multivariate indicators unless explicitly selected. Recorded default: `false`.
* `time`: latest, earliest, all, one date, or a comma-separated inclusive range. Recorded default: `latest`.
* `timeNearest`: Fallback behaviour when the selected date is outside an indicator's range. Recorded default: `none`.
* `geo`: One or more comma-separated geography-level keys or GSS codes. Recorded default: `all`.
* `geoExtent`: Parent GSS code used to constrain returned geographies. Recorded default: `all`.
* `geoCluster`: Statistical cluster in grouping_cluster form. Recorded default: `all`.
* `hasGeo`: Return indicators that include a geography level or GSS code. Recorded default: `any`.
* `dimension_{code}`: Dynamic non-time, non-geography dimension filter. Replace {code} with an indicator dimension code. Recorded default: `all`.
* `measure`: One or more measures. The wiki lists this parameter but does not define its semantics. Recorded default: `all`.
* `includeNames`: Include human-readable area names where supported. Recorded default: `true`.
* `includeStatus`: Include observation-level status identifiers where available. Recorded default: `true for json and xlsx; false otherwise`.

Source page: [Requesting data](../documents/Requesting-data.md).

# Preserved review findings

* [hasGeo default differs](../issues/drift-data-hasgeo-default.md) (medium)
* [Area-name parameter name and default conflict](../issues/drift-data-includenames.md) (high)
* [measure is listed but not explained](../issues/gap-data-measure.md) (medium)
* [Response and error contracts are incomplete](../issues/gap-response-schemas.md) (medium)

# Usage boundary

The upstream wiki says this API is internal/private, is not intended for non-ONS web applications, may change without notice, and prevents cross-origin browser requests. This concept is descriptive and does not authorise execution.
