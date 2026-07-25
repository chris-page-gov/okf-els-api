---
type: "Governance Finding"
title: "includeDates is documented where handlers reject it"
description: "Documented requests using includeDates can receive HTTP 400."
tags: ["review-finding","wiki-source-conflict","high"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-07-25T12:17:29Z"}
sources: [{"id":"els-wiki","resource":"https://github.com/ONSdigital/explore-local-statistics-app/wiki","title":"Explore Local Statistics application wiki","last_modified":"2026-07-20","pinned_commit":"3da822e28d775f1213d328573da34aba8278d79f"},{"id":"els-application","resource":"https://github.com/ONSdigital/explore-local-statistics-app/tree/795eaf204f47986f6be248a63f857a42afe4fdf2","title":"Explore Local Statistics application source review","last_modified":"2026-07-17","pinned_commit":"795eaf204f47986f6be248a63f857a42afe4fdf2"}]
finding_kind: "wiki-source-conflict"
severity: "high"
wiki_evidence: "Name search, reverse lookup and postcode lookup parameter tables list includeDates."
source_evidence: "The reviewed handlers' allow-lists omit includeDates and reject unknown parameters."
recommendation: "Implement includeDates or remove it from those three tables."
snapshot_mode: "frozen"
live_status: "not-checked"
---

# Finding

Documented requests using includeDates can receive HTTP 400.

# Evidence

* Wiki evidence: Name search, reverse lookup and postcode lookup parameter tables list includeDates.
* Application source evidence: The reviewed handlers' allow-lists omit includeDates and reject unknown parameters.

# Recommendation

Implement includeDates or remove it from those three tables.

# Evidence boundary

This finding records a comparison of the pinned wiki snapshot and pinned application source review. It has not been rechecked against current upstream or a live service.
