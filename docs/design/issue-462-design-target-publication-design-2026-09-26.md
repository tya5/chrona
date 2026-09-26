# Design — Stable Publication of Approved Visual Targets (#462)

## Use case and decision

A contributor evaluating #453, or a later preset, must be able to open every
approved target from the current `main` without access to private previews,
unmerged branches or a closed PR. The images are comparison targets, not
Chrona-generated corpus slides. Keep them under
`docs/research/presentation/`, with source beside rendered evidence:

- Keep PR #461's fourteen `<direction>-target-2026-09-26/` directories exactly
  as reviewed: one HTML drawing source, one PNG board render and a README each.
- Publish the PR #45 HALCYON-1 source at
  `docs/research/presentation/halcyon-1-target-design-2026-09-21/render_mocks.py`.
  Put its three proposal directories below that directory, each with the
  three existing PNG and SVG views. `board/02-programme-board.png` is target B.
  Preserve source bytes and image bytes from the public branch. Update only
  README paths/instructions to describe their new location and generation.
- Link #453 directly to the `main` B PNG path. Its former `examples/` path
  remains historical but is not the live yardstick.

## Ownership and boundaries

`docs/research` owns aspirational design references and generator scripts;
`examples/` owns reachable, materializable product examples. A research PNG
does not become a public materializer or imply that its underlying style is
implemented. The README must explicitly distinguish hand-drawn reference
from Chrona output. Issue #453 owns its mutable gap map and should link to
the stable repository location, not duplicate image bytes.

## Data, resource and failure model

No View, Theme, Layout, Scene, adapter, schema or Context data changes.
Image identity is the original Git blob byte identity, checked for every
copied PNG/SVG. Generator identity is likewise preserved. If a PR becomes
unmergeable, CI red or the source blobs unavailable, stop publication; do not
substitute a redrawn approximation. A moved research path is intentional:
historical PR #45 references continue to resolve at that PR, while `main`
and #453 use the new path.

## Alternatives and extension

Keeping B in `examples/` was rejected because #441's reachability rules
reserve that tree for reproducible examples. Only copying the B PNG was
rejected because the approved direction includes three proposals and source
needed for audit. Future targets should follow the same `docs/research`
source-plus-render convention; adding a target does not expand runtime
resource ingress or gallery preset syntax.
