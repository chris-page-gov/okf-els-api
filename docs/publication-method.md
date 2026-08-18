# Build and publication method

This repository publishes a frozen, metadata-only review of the Explore Local
Statistics API documentation. It does not call the API and does not make the
internal/private service public, supported, stable or live-verified.

## What the two contracts mean

[`okf.semantic.json`](../okf.semantic.json) records what the generated graph
means, which inputs are authoritative for it and what the Explorer projection
preserves. [`okf.publication.json`](../okf.publication.json) records the
separate lifecycle that takes reviewed source registers through generation,
checks and GitHub Pages publication.

The publication contract is data, not a script. Its command strings must be
reviewed against `AGENTS.md` and the repository code before anyone runs them.

## Source, projections and checks

The four JSON files under `source/` are the frozen source family. Running
`scripts/build_bundle.py` creates all files under `bundle/` deterministically.
Those generated files are committed so a pull request can show the exact bytes
that would be published.

For a source change:

1. Review the pinned source evidence and the internal/private API boundary.
2. Run `python3 scripts/build_bundle.py` once to update `bundle/`.
3. Inspect the generated diff. Do not hand-edit generated files.
4. Run the checks listed in `AGENTS.md`, including the documentation and
   changelog lockstep check.
5. Commit source, generated projections, relevant documentation and
   `CHANGELOG.md` together.

CI starts from a clean checkout and runs `scripts/build_bundle.py --check`
without a preceding build. This makes a stale committed projection fail instead
of allowing a build step to hide it. The checked and tested `bundle/` directory
is then uploaded as the Pages candidate; the deployment job does not rebuild
it.

## Concurrency and publication

Pull request runs have a per-ref concurrency group, so a newer revision can
cancel an obsolete validation for the same pull request without interfering
with another branch. Protected-main runs are non-cancelling, and the deployment
job uses a separate `pages-publication` group so publication candidates are
promoted one at a time.

## Current limitation

The repository does not yet produce an exact-commit real-browser receipt after
deployment. Until that is integrated and passes, the public Pages URLs are
useful discovery entry points but are not proof that a particular commit and
journey were verified. A failed future live check must report the failure; it
must not trigger an unreviewed rebuild.
