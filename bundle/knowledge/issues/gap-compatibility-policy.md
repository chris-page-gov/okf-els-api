---
type: "Governance Finding"
title: "No compatibility or deprecation policy"
description: "The v1 path does not itself establish stability."
tags: ["review-finding","governance-gap","medium"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-07-25T12:17:29Z"}
sources: [{"id":"els-wiki","resource":"https://github.com/ONSdigital/explore-local-statistics-app/wiki","title":"Explore Local Statistics application wiki","last_modified":"2026-07-20","pinned_commit":"3da822e28d775f1213d328573da34aba8278d79f"},{"id":"els-application","resource":"https://github.com/ONSdigital/explore-local-statistics-app/tree/795eaf204f47986f6be248a63f857a42afe4fdf2","title":"Explore Local Statistics application source review","last_modified":"2026-07-17","pinned_commit":"795eaf204f47986f6be248a63f857a42afe4fdf2"}]
finding_kind: "governance-gap"
severity: "medium"
wiki_evidence: "The wiki says the API may change without notice."
source_evidence: null
recommendation: "Define ownership, change notification, versioning, deprecation and support expectations before external reuse."
snapshot_mode: "frozen"
live_status: "not-checked"
---

# Finding

The v1 path does not itself establish stability.

# Evidence

* Wiki evidence: The wiki says the API may change without notice.
* Application source evidence: not supplied

# Recommendation

Define ownership, change notification, versioning, deprecation and support expectations before external reuse.

# Evidence boundary

This finding records a comparison of the pinned wiki snapshot and pinned application source review. It has not been rechecked against current upstream or a live service.
