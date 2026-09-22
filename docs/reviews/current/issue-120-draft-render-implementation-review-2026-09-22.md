# Issue 120 — Draft Render Implementation Review

## Decision

Accept the draft-render implementation. `chrona render` is now a typed,
non-evidence ingress to the existing review render use case.  It does not
retain the former schedule-scene SVG product, and it does not create a Context,
snapshot, revision, or output identity artifact.

## Architecture review

The presentation closure factory owns only explicit YAML ingress, contract
validation/freezing, in-memory draft identity construction, resolved Theme
derivation, and packaged font-asset declaration.  The CLI owns syntax and
output paths.  `render_review` remains the sole owner of scheduling,
projection, content normalization, measurement, Layout, Scene projection, and
renderer invocation.  The renderer receives no draft/immutable branch.

The prior generic renderer and its schedule-scene adapter had no product entry
point after this replacement.  They were removed rather than kept as a
compatibility path.  The independent federation display projection was moved
out of that retired module without changing its data boundary.

The small `asset_root` request parameter is a dependency location, not an
origin mode: immutable calls retain their Context revision root, while draft
calls select the packaged metrics root.  No geometry, layout policy, Scene
ownership, or SVG serialization policy moved across layers.

## Acceptance evidence

- Draft factory tests cover optional inputs, immutable draft identities, and
  schema-pointer diagnostics.
- CLI tests cover required syntax, default draft rendering, invalid viewport,
  and byte identity with the equivalent Controller Z immutable review render.
- Focused tests: 23 passed.
- Complete suite, run in independent terminal-sized partitions: 179 unit/CLI
  passed; 82 acceptance/integration passed; 8 skipped as configured.
- Import-direction and module-reachability checks passed.
- The ASTER, Controller Z, and three HALCYON public materializers ran in one
  batch and each matched its committed SVG bytes.  No generated SVG changed.

## Follow-on boundary

Issue #122 may replace the fixed SVG renderer with the documented target-kind
renderer seam.  It must keep both this draft closure and immutable Context
closure on the same use-case path; format selection must not reintroduce a
legacy draft renderer.
