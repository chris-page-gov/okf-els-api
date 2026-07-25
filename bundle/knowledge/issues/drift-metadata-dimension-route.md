---
type: "Governance Finding"
title: "Dimension-values route differs"
description: "Following the documented route can address the wrong optional-rest route instead of the dimension handler."
tags: ["review-finding","wiki-source-conflict","high"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-07-25T12:17:29Z"}
sources: [{"id":"els-wiki","resource":"https://github.com/ONSdigital/explore-local-statistics-app/wiki","title":"Explore Local Statistics application wiki","last_modified":"2026-07-20","pinned_commit":"3da822e28d775f1213d328573da34aba8278d79f"},{"id":"els-application","resource":"https://github.com/ONSdigital/explore-local-statistics-app/tree/795eaf204f47986f6be248a63f857a42afe4fdf2","title":"Explore Local Statistics application source review","last_modified":"2026-07-17","pinned_commit":"795eaf204f47986f6be248a63f857a42afe4fdf2"}]
finding_kind: "wiki-source-conflict"
severity: "high"
wiki_evidence: "/api/v1/metadata/indicators/{indicator}/{dimension}"
source_evidence: "/api/v1/metadata/indicators/{indicator}/dimensions/{dimension}"
recommendation: "Update the wiki or implementation and add a route contract test."
snapshot_mode: "frozen"
live_status: "not-checked"
---

# Finding

Following the documented route can address the wrong optional-rest route instead of the dimension handler.

# Evidence

* Wiki evidence: /api/v1/metadata/indicators/{indicator}/{dimension}
* Application source evidence: /api/v1/metadata/indicators/{indicator}/dimensions/{dimension}

# Recommendation

Update the wiki or implementation and add a route contract test.

# Evidence boundary

This finding records a comparison of the pinned wiki snapshot and pinned application source review. It has not been rechecked against current upstream or a live service.
