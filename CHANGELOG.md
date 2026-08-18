# Changelog

All notable changes to the repository publication method are recorded here.

## Unreleased

### Added

- Added `okf.publication.json` and `okf.semantic.json` to distinguish the
  publication lifecycle from the semantic meaning of the frozen ELS review.
- Added local publication-contract and documentation-lockstep checks, with
  regression tests and a plain-English method guide.

### Changed

- Changed GitHub Pages validation to check the committed bundle before
  publication without first rebuilding over it. Pull request validation now
  uses per-ref cancellation, while protected-main publication remains serial
  and non-cancelling.
- Pinned the GitHub Actions used by the Pages workflow and added bounded job
  timeouts.

### Publication boundary

- Exact-commit real-browser verification remains migration work. Existing
  public links must not be treated as verified deployment evidence until that
  gate is implemented and passes for the deployed commit.
