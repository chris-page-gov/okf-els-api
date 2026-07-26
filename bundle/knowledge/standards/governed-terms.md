---
type: "Standards Term Registry"
title: "ELS OKF governed metadata terms"
description: "Validated identifiers, authoritative provenance and bounded application meanings for standards and Explorer UI terms."
resource: "/data/standards/terms.json"
tags: ["standards","vocabulary","validation","provenance"]
status: "draft"
generated: {"by":"process:okf-els-api-build","at":"2026-07-25T12:17:29Z"}
sources: [{"id":"dcat-3","resource":"https://www.w3.org/TR/vocab-dcat-3/","title":"Data Catalog Vocabulary (DCAT) Version 3"},{"id":"dcterms-2020","resource":"https://www.dublincore.org/specifications/dublin-core/dcmi-terms/2020-01-20/","title":"DCMI Metadata Terms"},{"id":"foaf-2014","resource":"http://xmlns.com/foaf/spec/20140114.html","title":"FOAF Vocabulary Specification"},{"id":"hydra-core","resource":"https://www.hydra-cg.com/spec/latest/core/","title":"Hydra Core Vocabulary"},{"id":"prov-o-2013","resource":"https://www.w3.org/TR/2013/REC-prov-o-20130430/","title":"PROV-O: The PROV Ontology"},{"id":"openapi-3.1.0","resource":"https://spec.openapis.org/oas/v3.1.0.html","title":"OpenAPI Specification 3.1.0"},{"id":"okf-explorer-v1","resource":"/data/standards/terms.json","title":"OKF Explorer bounded projection vocabulary"},{"id":"okf-explorer-ui-v1","resource":"/data/standards/terms.json","title":"OKF Explorer reader-facing metadata terms"}]
validation_report: "/data/standards/term-validation.json"
snapshot_mode: "frozen"
live_status: "not-checked"
---

# Validation model

The register separates recognition of an identifier from the correctness of its application. Every emitted compact term must have a declared namespace, primary specification provenance, term kind, bounded-use explanation and validated application status.

# Trust boundary

The validation is a deterministic closed-world check against the checked-in curated register. It is machine-confirmed publication evidence, not human review, live vocabulary verification or a claim that the upstream API conforms to every referenced standard.

See the [machine-readable validation report](/data/standards/term-validation.json).
