# Explore Local Statistics API OKF

This repository turns the six-page
[Explore Local Statistics API wiki](https://github.com/ONSdigital/explore-local-statistics-app/wiki)
into a bounded, metadata-only Open Knowledge Format bundle.

The bundle catalogues 18 GET operations, their query and path parameters, six
statistical response representations, two boundary representations, source
provenance, and the differences found between the wiki and the current
`develop` branch implementation. It also emits a review-draft OpenAPI 3.1
description.

It does **not** make the API public or supported. The upstream wiki says the
API is internal/private, may change without notice, and prevents browser
cross-origin requests. The bundle stores no observation values, postcode
results, boundaries, coordinates, credentials, or personal information. It
does not call the API.

## Build

```bash
python3 scripts/build_bundle.py
python3 scripts/build_bundle.py --check
python3 -m unittest discover -s tests -v
```

The public entrypoints are:

- `bundle/okf-explorer.json` — portable OKF Explorer descriptor;
- `bundle/okf-bundle.jsonld` — semantic DCAT/Hydra/PROV descriptor;
- `bundle/data/openapi.json` — review-draft OpenAPI 3.1 description;
- `bundle/data/review/issues.json` — wiki/source drift register; and
- `bundle/checksums.json` — SHA-256 manifest.

See [REVIEW.md](REVIEW.md) for the suitability assessment and recommended next
steps.
