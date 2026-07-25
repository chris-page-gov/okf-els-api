---
type: "Governance Finding"
title: "Related-area includeNames parameter is undocumented"
description: "Clients cannot discover a useful payload-size and shape control from the wiki."
tags: ["review-finding","source-only-capability","medium"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-07-25T12:17:29Z"}
sources: [{"id":"els-wiki","resource":"https://github.com/ONSdigital/explore-local-statistics-app/wiki","title":"Explore Local Statistics application wiki","last_modified":"2026-07-20","pinned_commit":"3da822e28d775f1213d328573da34aba8278d79f"},{"id":"els-application","resource":"https://github.com/ONSdigital/explore-local-statistics-app/tree/795eaf204f47986f6be248a63f857a42afe4fdf2","title":"Explore Local Statistics application source review","last_modified":"2026-07-17","pinned_commit":"795eaf204f47986f6be248a63f857a42afe4fdf2"}]
finding_kind: "source-only-capability"
severity: "medium"
wiki_evidence: "The related, parents, children, siblings and similar sections omit includeNames."
source_evidence: "Each reviewed handler accepts includeNames and defaults it to true."
recommendation: "Document includeNames consistently for related-area operations."
snapshot_mode: "frozen"
live_status: "not-checked"
---

# Finding

Clients cannot discover a useful payload-size and shape control from the wiki.

# Evidence

* Wiki evidence: The related, parents, children, siblings and similar sections omit includeNames.
* Application source evidence: Each reviewed handler accepts includeNames and defaults it to true.

# Recommendation

Document includeNames consistently for related-area operations.

# Evidence boundary

This finding records a comparison of the pinned wiki snapshot and pinned application source review. It has not been rechecked against current upstream or a live service.
