---
type: "API Service"
title: "Explore Local Statistics internal API"
description: "Read-only statistical, metadata and geographic operations documented by the Explore Local Statistics application wiki."
resource: "https://www.ons.gov.uk/explore-local-statistics"
tags: ["api","ons","internal-private","metadata-only"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-07-25T12:17:29Z"}
sources: [{"id":"els-wiki","resource":"https://github.com/ONSdigital/explore-local-statistics-app/wiki","title":"Explore Local Statistics application wiki","last_modified":"2026-07-20","pinned_commit":"3da822e28d775f1213d328573da34aba8278d79f"},{"id":"els-application","resource":"https://github.com/ONSdigital/explore-local-statistics-app/tree/795eaf204f47986f6be248a63f857a42afe4fdf2","title":"Explore Local Statistics application source review","last_modified":"2026-07-17","pinned_commit":"795eaf204f47986f6be248a63f857a42afe4fdf2"}]
snapshot_mode: "frozen"
live_status: "not-checked"
execution_included: false
observations_included: false
---

# Scope

The upstream wiki says this API is internal/private, is not intended for non-ONS web applications, may change without notice, and prevents cross-origin browser requests.

This concept describes the bounded API discovery surface; it does not certify the service as stable, public, supported or live. See the [frozen source boundary](snapshots/wiki-and-source.md) and the [18 operation concepts](operations/).

# Execution boundary

The bundle does not execute requests. The generated selection plan only checks a proposed request's shape.
