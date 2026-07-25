---
type: "API Endpoint"
title: "Filter and download statistical data"
description: "Filter one or more indicators by topic, geography, time, dimensions and measures."
resource: "https://www.ons.gov.uk/explore-local-statistics/api/v1/data.{format}"
tags: ["api","get","data","internal-private-unstable"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-07-25T12:17:29Z"}
sources: [{"id":"wiki-page","resource":"https://github.com/ONSdigital/explore-local-statistics-app/wiki/Requesting-data","title":"Requesting data","pinned_commit":"3da822e28d775f1213d328573da34aba8278d79f","revision_at":"2026-07-20T12:17:57+01:00","sha256":"f15cc3eddb662a7b3e578a68cf7ce644ae8c2d8a39f06a047d7580f36d8643b7"},{"id":"route-handler","resource":"https://github.com/ONSdigital/explore-local-statistics-app/blob/795eaf204f47986f6be248a63f857a42afe4fdf2/src/routes/(api)/api/v1/data.[format]/+server.ts","title":"Reviewed application route handler","pinned_commit":"795eaf204f47986f6be248a63f857a42afe4fdf2","revision_at":"2026-07-17T09:35:03+01:00"}]
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

Source page: [Requesting data](../documents/Requesting-data.md).

# Preserved review findings

* [hasGeo default differs](../issues/drift-data-hasgeo-default.md) (medium)
* [Area-name parameter name and default conflict](../issues/drift-data-includenames.md) (high)
* [measure is listed but not explained](../issues/gap-data-measure.md) (medium)
* [Response and error contracts are incomplete](../issues/gap-response-schemas.md) (medium)

# Usage boundary

The upstream wiki says this API is internal/private, is not intended for non-ONS web applications, may change without notice, and prevents cross-origin browser requests. This concept is descriptive and does not authorise execution.
