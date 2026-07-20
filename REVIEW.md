# Review: an OKF bundle for the Explore Local Statistics API wiki

## Recommendation

Create a separate **API-discovery bundle**, not another statistical-dataset
catalogue. `okf-ons` already catalogues ONS and Nomis datasets and geography
products. The ELS wiki describes a service surface: routes, parameters,
representations, geography relationships, and operational caveats.

The useful connection is:

```text
okf-ons dataset selection
        ↓
ELS metadata/taxonomy discovery
        ↓
ELS data or geography request plan
        ↓
explicit user/client execution outside this bundle
```

This prototype covers the middle two stages as metadata. It deliberately does
not execute requests.

## What the bundle contains

- One DCAT `DataService` for the ELS API.
- Eighteen discoverable GET-operation records.
- Six data representations: CSV, CSVW, JSON-Stat, XLSX, row JSON and
  column-oriented JSON.
- Two boundary representations: GeoJSON and TopoJSON.
- Reusable parameter definitions, per-operation defaults and path parameters.
- Six source-document records with page hashes and a pinned wiki commit.
- Static source-verification evidence pinned to the application `develop`
  commit.
- A draft OpenAPI 3.1 document clearly marked as a review artifact.
- A machine-readable drift and documentation-gap register.
- Deterministic checksums and a build/check command.

## Why this is bounded

The source denominator is exactly six wiki Markdown pages at commit
`3da822e28d775f1213d328573da34aba8278d79f`. All six are represented in the
snapshot manifest. The application comparison is limited to the 17 route
handlers under `src/routes/(api)/api/v1` at commit
`795eaf204f47986f6be248a63f857a42afe4fdf2`.

This is complete for those declared source files, not for all ELS behaviour.
No live requests, response-schema inference, production deployment
verification, or historical compatibility analysis were performed.

## Important review findings

1. The documented dimension-values route omits the implemented
   `/dimensions/` segment.
2. The data page calls the area-name switch `includeNames` in its table and
   example, but its prose says `geoNames` and also contradicts the default.
3. The geography page documents `includeDates` for search, reverse lookup and
   postcode lookup, while the reviewed handlers reject that parameter.
4. The reviewed data handler defaults `hasGeo` to `any`; the wiki says `all`.
5. Related-area handlers support `includeNames`, but the wiki does not list it.
6. `measure` is listed for data requests but has no explanatory subsection.
7. Response schemas, error models, limits, compatibility policy and
   authentication/availability expectations are incomplete.

The generated OpenAPI uses the source-verified route when the wiki and source
conflict, and attaches `x-okf-documentation-issues` so the discrepancy remains
visible.

## Recommended next steps

1. Ask the ELS maintainers to resolve the drift register.
2. Add an upstream-maintained OpenAPI contract and validate it in application
   CI.
3. Add bounded, non-observational live probes for health and metadata routes
   only, if ONS approves them.
4. Link `okf-ons` dataset records to ELS indicator slugs using evidence-backed
   relationships; do not infer equivalence from titles.
5. Add an MCP planning adapter only after required parameters, constraints and
   response limits are machine-validated. Keep execution opt-in and outside
   the static bundle.
