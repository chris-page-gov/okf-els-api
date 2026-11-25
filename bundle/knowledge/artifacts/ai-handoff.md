---
type: "Reader Guide"
title: "Bounded AI handoff for ELS API evidence"
description: "A copyable, source-bounded prompt that preserves uncertainty and forbids live execution."
resource: "/knowledge/artifacts/ai-handoff.md"
tags: ["reader-guide","ai-handoff","bounded-evidence"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-11-25T00:00:00Z"}
sources: [{"id":"els-wiki","resource":"https://github.com/ONSdigital/explore-local-statistics-app/wiki","title":"Explore Local Statistics application wiki","last_modified":"2026-07-20","pinned_commit":"3da822e28d775f1213d328573da34aba8278d79f"},{"id":"els-application","resource":"https://github.com/ONSdigital/explore-local-statistics-app/tree/795eaf204f47986f6be248a63f857a42afe4fdf2","title":"Explore Local Statistics application source review","last_modified":"2026-07-17","pinned_commit":"795eaf204f47986f6be248a63f857a42afe4fdf2"}]
snapshot_mode: "frozen"
live_status: "not-checked"
---

# Copyable AI handoff

Copy the prompt below with the exact linked bundle files available to the model.

```text
Using only these exact bundle files: knowledge/documents/Requesting-data.md; knowledge/documents/Requesting-geographic-information.md; knowledge/operations/data.md; knowledge/operations/geo-lookup.md; knowledge/issues/drift-data-hasgeo-default.md; knowledge/issues/drift-data-includenames.md; knowledge/issues/gap-data-measure.md; knowledge/issues/gap-response-schemas.md; knowledge/artifacts/selection-plan.md; knowledge/snapshots/wiki-and-source.md. Answer: When requesting indicator data, which geography and date filters can a client plan, and what evidence limits apply to an answer? Separate wiki statements from pinned application-source observations. Cite each claim with its local file and source link. Preserve contradictions and unknowns. Do not infer current behaviour, execute requests, invent response values, or treat the selection plan as permission to call the API. If a claim is not supported by these records, say that evidence is insufficient.
```
