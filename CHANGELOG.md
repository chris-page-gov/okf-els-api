# Changelog

## Unreleased — standards references

- Link the central current and historical OKF standards register and public bundle catalogue.


All notable changes to the repository publication method are recorded here.

## Unreleased

### Added

- Migrated the normative Markdown concept tree to OKF Core 0.3 while retaining
  every original concept path and draft/unverified status.
- Added an anchored, source-linked complex-question guide, diagram and bounded
  copyable AI handoff from frozen source registers.
- Added a responsive HTML guide with visible evidence links and bounded prompt.
- Added a worked date/geography answer with exact-path citations to the recorded
  parameter defaults, preserved conflicts and evidence gaps.

- Added `okf.publication.json` and `okf.semantic.json` to distinguish the
  publication lifecycle from the semantic meaning of the frozen ELS review.
- Added local publication-contract and documentation-lockstep checks, with
  regression tests and a plain-English method guide.

### Changed

- Regenerated the deterministic bundle, Core 0.3 conformance report and
  publication metadata without refreshing the pinned upstream sources.

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
