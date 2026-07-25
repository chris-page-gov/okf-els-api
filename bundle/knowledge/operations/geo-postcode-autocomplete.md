---
type: "API Endpoint"
title: "Autocomplete a partial postcode"
description: "Return matching postcodes and coordinates for a partial postcode."
resource: "https://www.ons.gov.uk/explore-local-statistics/api/v1/geo/postcodes/{code}/autocomplete"
tags: ["api","get","geography","internal-private-unstable"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-07-25T12:17:29Z"}
sources: [{"id":"wiki-page","resource":"https://github.com/ONSdigital/explore-local-statistics-app/wiki/Requesting-geographic-information","title":"Requesting geographic information","pinned_commit":"3da822e28d775f1213d328573da34aba8278d79f","revision_at":"2026-07-20T12:17:57+01:00","sha256":"7eb059867836b105e6bde9aeb5eb7bf81952f6fc1c0c1ebe907c07871c388ba5"},{"id":"route-handler","resource":"https://github.com/ONSdigital/explore-local-statistics-app/blob/795eaf204f47986f6be248a63f857a42afe4fdf2/src/routes/(api)/api/v1/geo/postcodes/[code]/autocomplete/+server.ts","title":"Reviewed application route handler","pinned_commit":"795eaf204f47986f6be248a63f857a42afe4fdf2","revision_at":"2026-07-17T09:35:03+01:00"}]
method: "GET"
path_template: "/api/v1/geo/postcodes/{code}/autocomplete"
documented_path_template: "/api/v1/geo/postcodes/{partial_code}/autocomplete"
snapshot_mode: "frozen"
live_status: "not-checked"
execution_included: false
---

# Route

`GET /api/v1/geo/postcodes/{code}/autocomplete`

Parameters represented by the bounded review: `code`, `limit`, `offset`.

Source page: [Requesting geographic information](../documents/Requesting-geographic-information.md).

# Preserved review findings

* No registered issue is attached to this operation.

# Usage boundary

The upstream wiki says this API is internal/private, is not intended for non-ONS web applications, may change without notice, and prevents cross-origin browser requests. This concept is descriptive and does not authorise execution.
