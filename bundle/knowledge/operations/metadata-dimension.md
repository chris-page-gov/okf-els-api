---
type: "API Endpoint"
title: "List values for one indicator dimension"
description: "Return possible values for a specific dimension of a specific indicator."
resource: "https://www.ons.gov.uk/explore-local-statistics/api/v1/metadata/indicators/{indicator}/dimensions/{dimension}"
tags: ["api","get","metadata","internal-private-unstable"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-07-25T12:17:29Z"}
sources: [{"id":"wiki-page","resource":"https://github.com/ONSdigital/explore-local-statistics-app/wiki/Requesting-metadata","title":"Requesting metadata","pinned_commit":"3da822e28d775f1213d328573da34aba8278d79f","revision_at":"2026-07-20T12:17:57+01:00","sha256":"ae20497f3249b5aa57fa13c7eece79201c9c075933c696ec234d2eb859be3682"},{"id":"route-handler","resource":"https://github.com/ONSdigital/explore-local-statistics-app/blob/795eaf204f47986f6be248a63f857a42afe4fdf2/src/routes/(api)/api/v1/metadata/indicators/[...indicator]/dimensions/[...dimension]/+server.ts","title":"Reviewed application route handler","pinned_commit":"795eaf204f47986f6be248a63f857a42afe4fdf2","revision_at":"2026-07-17T09:35:03+01:00"}]
method: "GET"
path_template: "/api/v1/metadata/indicators/{indicator}/dimensions/{dimension}"
documented_path_template: "/api/v1/metadata/indicators/{indicator}/{dimension}"
snapshot_mode: "frozen"
live_status: "not-checked"
execution_included: false
---

# Route

`GET /api/v1/metadata/indicators/{indicator}/dimensions/{dimension}`

Parameters represented by the bounded review: `indicator`, `dimension`.

Source page: [Requesting metadata](../documents/Requesting-metadata.md).

# Preserved review findings

* [Dimension-values route differs](../issues/drift-metadata-dimension-route.md) (high)

# Usage boundary

The upstream wiki says this API is internal/private, is not intended for non-ONS web applications, may change without notice, and prevents cross-origin browser requests. This concept is descriptive and does not authorise execution.
