---
type: "Governance Finding"
title: "Area-name parameter name and default conflict"
description: "Clients following the prose can send an invalid parameter or assume the wrong payload shape."
tags: ["review-finding","wiki-internal-conflict","high"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-07-25T12:17:29Z"}
sources: [{"id":"els-wiki","resource":"https://github.com/ONSdigital/explore-local-statistics-app/wiki","title":"Explore Local Statistics application wiki","last_modified":"2026-07-20","pinned_commit":"3da822e28d775f1213d328573da34aba8278d79f"},{"id":"els-application","resource":"https://github.com/ONSdigital/explore-local-statistics-app/tree/795eaf204f47986f6be248a63f857a42afe4fdf2","title":"Explore Local Statistics application source review","last_modified":"2026-07-17","pinned_commit":"795eaf204f47986f6be248a63f857a42afe4fdf2"}]
finding_kind: "wiki-internal-conflict"
severity: "high"
wiki_evidence: "The parameter table and example use includeNames with default true; prose says names are excluded by default and refers to geoNames."
source_evidence: "The data handler accepts includeNames and defaults it to true."
recommendation: "Use includeNames consistently and state one tested default."
snapshot_mode: "frozen"
live_status: "not-checked"
---

# Finding

Clients following the prose can send an invalid parameter or assume the wrong payload shape.

# Evidence

* Wiki evidence: The parameter table and example use includeNames with default true; prose says names are excluded by default and refers to geoNames.
* Application source evidence: The data handler accepts includeNames and defaults it to true.

# Recommendation

Use includeNames consistently and state one tested default.

# Evidence boundary

This finding records a comparison of the pinned wiki snapshot and pinned application source review. It has not been rechecked against current upstream or a live service.
