---
type: "Source Snapshot"
title: "ELS wiki and application source review boundary"
description: "Frozen evidence from six wiki pages and a bounded static review of v1 GET route handlers."
resource: "/data/provenance/wiki-snapshot.json"
tags: ["snapshot","provenance","drift"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-07-25T12:17:29Z"}
sources: [{"id":"els-wiki","resource":"https://github.com/ONSdigital/explore-local-statistics-app/wiki","title":"Explore Local Statistics application wiki","last_modified":"2026-07-20","pinned_commit":"3da822e28d775f1213d328573da34aba8278d79f"},{"id":"els-application","resource":"https://github.com/ONSdigital/explore-local-statistics-app/tree/795eaf204f47986f6be248a63f857a42afe4fdf2","title":"Explore Local Statistics application source review","last_modified":"2026-07-17","pinned_commit":"795eaf204f47986f6be248a63f857a42afe4fdf2"}]
snapshot_id: "els-wiki-2026-07-20"
snapshot_mode: "frozen"
live_status: "not-checked"
drift_scope: "pinned-wiki-versus-pinned-develop-review"
---

# Temporal boundary

* Bundle generation checkpoint: `2026-07-25T12:17:29Z`.
* Wiki snapshot: `3da822e28d775f1213d328573da34aba8278d79f` (2026-07-20T12:17:57+01:00).
* Reviewed application `develop` commit: `795eaf204f47986f6be248a63f857a42afe4fdf2` (2026-07-17T09:35:03+01:00).
* Current live/upstream state: **not checked**.

The nine drift findings compare the two pinned evidence surfaces. They do not assert the present state of the wiki, branch or deployed service.
