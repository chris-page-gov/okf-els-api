---
type: "Governance Finding"
title: "measure is listed but not explained"
description: "Allowed values and interaction with indicator and status fields are not documented."
tags: ["review-finding","documentation-gap","medium"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-07-25T12:17:29Z"}
sources: [{"id":"els-wiki","resource":"https://github.com/ONSdigital/explore-local-statistics-app/wiki","title":"Explore Local Statistics application wiki","last_modified":"2026-07-20","pinned_commit":"3da822e28d775f1213d328573da34aba8278d79f"},{"id":"els-application","resource":"https://github.com/ONSdigital/explore-local-statistics-app/tree/795eaf204f47986f6be248a63f857a42afe4fdf2","title":"Explore Local Statistics application source review","last_modified":"2026-07-17","pinned_commit":"795eaf204f47986f6be248a63f857a42afe4fdf2"}]
finding_kind: "documentation-gap"
severity: "medium"
wiki_evidence: "measure appears in the data parameter table without a subsection."
source_evidence: "The reviewed handler accepts measure and defaults it to all."
recommendation: "Add semantics, examples and a link to discover valid measure codes."
snapshot_mode: "frozen"
live_status: "not-checked"
---

# Finding

Allowed values and interaction with indicator and status fields are not documented.

# Evidence

* Wiki evidence: measure appears in the data parameter table without a subsection.
* Application source evidence: The reviewed handler accepts measure and defaults it to all.

# Recommendation

Add semantics, examples and a link to discover valid measure codes.

# Evidence boundary

This finding records a comparison of the pinned wiki snapshot and pinned application source review. It has not been rechecked against current upstream or a live service.
