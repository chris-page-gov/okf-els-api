---
type: "Governance Finding"
title: "hasGeo default differs"
description: "The omission behaviour is ambiguous."
tags: ["review-finding","wiki-source-conflict","medium"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-07-25T12:17:29Z"}
sources: [{"id":"els-wiki","resource":"https://github.com/ONSdigital/explore-local-statistics-app/wiki","title":"Explore Local Statistics application wiki","last_modified":"2026-07-20","pinned_commit":"3da822e28d775f1213d328573da34aba8278d79f"},{"id":"els-application","resource":"https://github.com/ONSdigital/explore-local-statistics-app/tree/795eaf204f47986f6be248a63f857a42afe4fdf2","title":"Explore Local Statistics application source review","last_modified":"2026-07-17","pinned_commit":"795eaf204f47986f6be248a63f857a42afe4fdf2"}]
finding_kind: "wiki-source-conflict"
severity: "medium"
wiki_evidence: "The data page states a default of all."
source_evidence: "The reviewed data handler defaults hasGeo to any."
recommendation: "Define and test the documented semantic difference between any and all."
snapshot_mode: "frozen"
live_status: "not-checked"
---

# Finding

The omission behaviour is ambiguous.

# Evidence

* Wiki evidence: The data page states a default of all.
* Application source evidence: The reviewed data handler defaults hasGeo to any.

# Recommendation

Define and test the documented semantic difference between any and all.

# Evidence boundary

This finding records a comparison of the pinned wiki snapshot and pinned application source review. It has not been rechecked against current upstream or a live service.
