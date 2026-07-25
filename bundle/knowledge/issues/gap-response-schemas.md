---
type: "Governance Finding"
title: "Response and error contracts are incomplete"
description: "Typed clients cannot be generated safely and agents cannot validate outputs rigorously."
tags: ["review-finding","documentation-gap","medium"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-07-25T12:17:29Z"}
sources: [{"id":"els-wiki","resource":"https://github.com/ONSdigital/explore-local-statistics-app/wiki","title":"Explore Local Statistics application wiki","last_modified":"2026-07-20","pinned_commit":"3da822e28d775f1213d328573da34aba8278d79f"},{"id":"els-application","resource":"https://github.com/ONSdigital/explore-local-statistics-app/tree/795eaf204f47986f6be248a63f857a42afe4fdf2","title":"Explore Local Statistics application source review","last_modified":"2026-07-17","pinned_commit":"795eaf204f47986f6be248a63f857a42afe4fdf2"}]
finding_kind: "documentation-gap"
severity: "medium"
wiki_evidence: "The wiki provides examples and format descriptions but no complete schemas or common error model."
source_evidence: "Handlers return 400/404 responses and apply request-size validation."
recommendation: "Publish an upstream OpenAPI 3.1 contract with response schemas, errors, limits and examples."
snapshot_mode: "frozen"
live_status: "not-checked"
---

# Finding

Typed clients cannot be generated safely and agents cannot validate outputs rigorously.

# Evidence

* Wiki evidence: The wiki provides examples and format descriptions but no complete schemas or common error model.
* Application source evidence: Handlers return 400/404 responses and apply request-size validation.

# Recommendation

Publish an upstream OpenAPI 3.1 contract with response schemas, errors, limits and examples.

# Evidence boundary

This finding records a comparison of the pinned wiki snapshot and pinned application source review. It has not been rechecked against current upstream or a live service.
