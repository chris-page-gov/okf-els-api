---
type: "API Endpoint"
title: "List indicator metadata"
description: "Return metadata for indicators filtered by topic, geography and year."
resource: "https://www.ons.gov.uk/explore-local-statistics/api/v1/metadata/indicators"
tags: ["api","get","metadata","internal-private-unstable"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-11-25T00:00:00Z"}
sources: [{"id":"wiki-page","resource":"https://github.com/ONSdigital/explore-local-statistics-app/wiki/Requesting-metadata","title":"Requesting metadata","pinned_commit":"3da822e28d775f1213d328573da34aba8278d79f","revision_at":"2026-07-20T12:17:57+01:00","last_modified":"2026-07-20","sha256":"ae20497f3249b5aa57fa13c7eece79201c9c075933c696ec234d2eb859be3682"},{"id":"route-handler","resource":"https://github.com/ONSdigital/explore-local-statistics-app/blob/795eaf204f47986f6be248a63f857a42afe4fdf2/src/routes/(api)/api/v1/metadata/indicators/[...indicator]/+server.ts","title":"Reviewed application route handler","pinned_commit":"795eaf204f47986f6be248a63f857a42afe4fdf2","revision_at":"2026-07-17T09:35:03+01:00","last_modified":"2026-07-17"}]
method: "GET"
path_template: "/api/v1/metadata/indicators"
documented_path_template: "/api/v1/metadata/indicators"
snapshot_mode: "frozen"
live_status: "not-checked"
execution_included: false
---

# Route

`GET /api/v1/metadata/indicators`

Parameters represented by the bounded review: `topic`, `indicator`, `hasGeo`, `hasYear`, `excludeMultivariate`, `fullDims`, `asLookup`.

# Parameter evidence

* `topic`: One or more comma-separated topic or sub-topic codes, or all. Recorded default: `all`.
* `indicator`: One or more comma-separated indicator slugs, or all.
* `hasGeo`: Return indicators that include a geography level or GSS code. Recorded default: `all`.
* `hasYear`: Return indicators that contain the specified YYYY year. Recorded default: `all`.
* `excludeMultivariate`: Exclude multivariate indicators unless explicitly selected. Recorded default: `false`.
* `fullDims`: Include all available dimension values. Recorded default: `false`.
* `asLookup`: Return an object keyed by identifier instead of an array. Recorded default: `false`.

Source page: [Requesting metadata](../documents/Requesting-metadata.md).

# Preserved review findings

* No registered issue is attached to this operation.

# Usage boundary

The upstream wiki says this API is internal/private, is not intended for non-ONS web applications, may change without notice, and prevents cross-origin browser requests. This concept is descriptive and does not authorise execution.
