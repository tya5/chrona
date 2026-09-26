<!-- chrona:literal-acceptance/v1 -->

# Release Review — Published Approved Design Targets (#462)

**Design:** [publication design](../../design/issue-462-design-target-publication-design-2026-09-26.md).
**Architecture:** [review](issue-462-design-target-publication-architecture-review-2026-09-26.md).
**Implementation plan:** [slices](../../planning/active/issue-462-design-target-publication-implementation-plan-2026-09-26.md).

## Literal issue acceptance

### Issue #462

- Source: [Issue #462](https://github.com/tya5/chrona/issues/462)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | PR #461 is merged. | met | [PR #461](https://github.com/tya5/chrona/pull/461) merged at `4f6407c16a481ca8787956dff75b40b4ead5ab13`; all fourteen directories have README, HTML source and PNG on `main`. | — |
| 2 | Target B's generator and rendered images are on `main` outside `examples/`. | met | [generator](../../research/presentation/halcyon-1-target-design-2026-09-21/render_mocks.py), [target B PNG](../../research/presentation/halcyon-1-target-design-2026-09-21/board/02-programme-board.png), and [research README](../../research/presentation/halcyon-1-target-design-2026-09-21/README.md) published at `1a3ae77dc9422017f89258416a093d71bcb426fd`. | — |
| 3 | #453 links to target B on `main`. | met | [Issue #453](https://github.com/tya5/chrona/issues/453) body now links to the exact `main` PNG; the GitHub contents API returned its `352bab2b3fa2dbf803f2e5815706b57febb45470` blob. | — |

## Programme-level criteria (optional)

All fourteen PR #461 target directories remain documentation only. The B
release carries three proposals times three views, each with original PNG
and SVG plus the original generator. No new corpus slide, runtime resource,
schema or public materializer was introduced.

## Verification and artifact review

- PR #461's 42 files and four green jobs were checked before merge; a local
  merge-tree check found no conflict with the then-current `main`.
- The B generator and all eighteen moved PNG/SVG files have the same Git
  blob IDs as public branch `design/halcyon-1-target`; the README alone was
  edited for its new path. The generator reproduces all nine SVGs byte-for-
  byte. Target B PNG was inspected visually and is a research mock, visibly
  labelled `target mock · not renderer output`.
- `tools/check_example_reachability.py` and `tools/example_inventory.py`
  pass; full `conformance/run_conformance.py` passes. No generated Scene/SVG
  corpus file changed. #453 remains open as its owner-maintained gap map.
- [Target B commit CI](https://github.com/tya5/chrona/actions/runs/36220370687):
  **PASS** on Ubuntu, macOS and Windows (full pytest, conformance and wheel
  gates), with newest-Python public-materializer reproduction also passing.

## Architecture conclusion

The research-versus-product example boundary is intact. Source and rendered
reference artifacts are together in `docs/research/presentation`; #453 points
to the released B image without treating it as a materializer product. No
Theme, Layout, Scene or adapter responsibility changed. All literal criteria
are met. The review commit's own release gate remains to be checked before
issue closure.
