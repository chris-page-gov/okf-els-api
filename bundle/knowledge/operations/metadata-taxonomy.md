---
type: "API Endpoint"
title: "List the indicator taxonomy"
description: "Return indicators grouped into topics and sub-topics, nested or flat."
resource: "https://www.ons.gov.uk/explore-local-statistics/api/v1/metadata/taxonomy"
tags: ["api","get","metadata","internal-private-unstable"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-11-25T00:00:00Z"}
sources: [{"id":"wiki-page","resource":"https://github.com/ONSdigital/explore-local-statistics-app/wiki/Requesting-metadata","title":"Requesting metadata","pinned_commit":"3da822e28d775f1213d328573da34aba8278d79f","revision_at":"2026-07-20T12:17:57+01:00","last_modified":"2026-07-20","sha256":"ae20497f3249b5aa57fa13c7eece79201c9c075933c696ec234d2eb859be3682"},{"id":"route-handler","resource":"https://github.com/ONSdigital/explore-local-statistics-app/blob/795eaf204f47986f6be248a63f857a42afe4fdf2/src/routes/(api)/api/v1/metadata/taxonomy/+server.ts","title":"Reviewed application route handler","pinned_commit":"795eaf204f47986f6be248a63f857a42afe4fdf2","revision_at":"2026-07-17T09:35:03+01:00","last_modified":"2026-07-17"}]
method: "GET"
path_template: "/api/v1/metadata/taxonomy"
documented_path_template: "/api/v1/metadata/taxonomy"
snapshot_mode: "frozen"
live_status: "not-checked"
execution_included: false
---

# Route

`GET /api/v1/metadata/taxonomy`

Parameters represented by the bounded review: `topic`, `hasGeo`, `hasYear`, `excludeMultivariate`, `flat`.

# Parameter evidence

* `topic`: One or more comma-separated topic or sub-topic codes, or all. Recorded default: `all`.
* `hasGeo`: Return indicators that include a geography level or GSS code. Recorded default: `all`.
* `hasYear`: Return indicators that contain the specified YYYY year. Recorded default: `all`.
* `excludeMultivariate`: Exclude multivariate indicators unless explicitly selected. Recorded default: `false`.
* `flat`: Return a flattened taxonomy instead of nested topics. Recorded default: `false`.

Source page: [Requesting metadata](../documents/Requesting-metadata.md).

# Preserved review findings

* No registered issue is attached to this operation.

# Usage boundary

The upstream wiki says this API is internal/private, is not intended for non-ONS web applications, may change without notice, and prevents cross-origin browser requests. This concept is descriptive and does not authorise execution.
