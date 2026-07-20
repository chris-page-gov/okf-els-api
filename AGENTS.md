# ELS API OKF repository guide

## Purpose

This repository publishes a metadata-only Open Knowledge Format bundle for the
internal/private Explore Local Statistics API documentation.

## Non-negotiable contracts

- Preserve the upstream warning that the API is not intended for non-ONS web
  applications, may change without notice, and blocks browser cross-origin
  requests.
- Never store observation values, postcode lookups, coordinates, credentials,
  cookies, or personal information in the bundle.
- Keep documented claims separate from facts verified against application
  source. Preserve conflicts instead of silently choosing one.
- Never claim that an endpoint is stable, public, supported, or live-verified.
- Generate all public output under `bundle/` deterministically from checked-in
  source registers.

## Validation

Run before publishing:

```bash
python3 scripts/build_bundle.py
python3 scripts/build_bundle.py --check
python3 -m unittest discover -s tests -v
```
