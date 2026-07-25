---
type: "Governance Finding"
title: "The API is internal/private and unstable"
description: "The bundle must not imply that the API is public, supported for third parties, stable, or usable cross-origin from browsers."
tags: ["review-finding","usage-boundary","critical-boundary"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-07-25T12:17:29Z"}
sources: [{"id":"els-wiki","resource":"https://github.com/ONSdigital/explore-local-statistics-app/wiki","title":"Explore Local Statistics application wiki","last_modified":"2026-07-20","pinned_commit":"3da822e28d775f1213d328573da34aba8278d79f"},{"id":"els-application","resource":"https://github.com/ONSdigital/explore-local-statistics-app/tree/795eaf204f47986f6be248a63f857a42afe4fdf2","title":"Explore Local Statistics application source review","last_modified":"2026-07-17","pinned_commit":"795eaf204f47986f6be248a63f857a42afe4fdf2"}]
finding_kind: "usage-boundary"
severity: "critical-boundary"
wiki_evidence: "Home"
source_evidence: null
recommendation: "Keep execution opt-in and obtain an ONS-supported contract before depending on the service."
snapshot_mode: "frozen"
live_status: "not-checked"
---

# Finding

The bundle must not imply that the API is public, supported for third parties, stable, or usable cross-origin from browsers.

# Evidence

* Wiki evidence: Home
* Application source evidence: not supplied

# Recommendation

Keep execution opt-in and obtain an ONS-supported contract before depending on the service.

# Evidence boundary

This finding records a comparison of the pinned wiki snapshot and pinned application source review. It has not been rechecked against current upstream or a live service.
