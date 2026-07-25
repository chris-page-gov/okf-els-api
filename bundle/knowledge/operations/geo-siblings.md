---
type: "API Endpoint"
title: "List sibling areas"
description: "List siblings sharing an immediate or selected parent level."
resource: "https://www.ons.gov.uk/explore-local-statistics/api/v1/geo/related/{code}/siblings"
tags: ["api","get","geography","internal-private-unstable"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-07-25T12:17:29Z"}
sources: [{"id":"wiki-page","resource":"https://github.com/ONSdigital/explore-local-statistics-app/wiki/Requesting-geographic-information","title":"Requesting geographic information","pinned_commit":"3da822e28d775f1213d328573da34aba8278d79f","revision_at":"2026-07-20T12:17:57+01:00","sha256":"7eb059867836b105e6bde9aeb5eb7bf81952f6fc1c0c1ebe907c07871c388ba5"},{"id":"route-handler","resource":"https://github.com/ONSdigital/explore-local-statistics-app/blob/795eaf204f47986f6be248a63f857a42afe4fdf2/src/routes/(api)/api/v1/geo/related/[code]/siblings/+server.ts","title":"Reviewed application route handler","pinned_commit":"795eaf204f47986f6be248a63f857a42afe4fdf2","revision_at":"2026-07-17T09:35:03+01:00"}]
method: "GET"
path_template: "/api/v1/geo/related/{code}/siblings"
documented_path_template: "/api/v1/geo/related/{code}/siblings"
snapshot_mode: "frozen"
live_status: "not-checked"
execution_included: false
---

# Route

`GET /api/v1/geo/related/{code}/siblings`

Parameters represented by the bounded review: `code`, `parentLevel`, `includeNames`.

Source page: [Requesting geographic information](../documents/Requesting-geographic-information.md).

# Preserved review findings

* [Related-area includeNames parameter is undocumented](../issues/gap-geo-related-includenames.md) (medium)

# Usage boundary

The upstream wiki says this API is internal/private, is not intended for non-ONS web applications, may change without notice, and prevents cross-origin browser requests. This concept is descriptive and does not authorise execution.
