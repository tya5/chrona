# Issue #365 — Draft Content Extent and Actionable Overflow Design Plan

## Problem and public basis

At public `main` `48b8653`, the default draft viewport is fixed at 1600×900.
The table-timeline minimum row height can make ordinary multi-row Drafts reject
with `E_LAYOUT_REQUIRED_OVERFLOW`, while the diagnostic omits the measured
requirement and a suggested viewport. The View's `layoutIntent.compactness`
enum is accepted but has no runtime consumer.

This is a Layout/ingress problem, not a Scene or renderer recovery problem.
Scene must continue to consume completed placements; immutable Context evidence
must remain viewport-pinned.

## Design work

### D365-1 — Typed draft viewport extent

Define a Draft-only viewport grammar that permits a fixed inline size and a
block `auto` request (CLI spelling `WIDTHxauto`). Establish where intrinsic
block extent is measured, how a finite resolved viewport is produced before
Layout/Scene, and the maximum/diagnostic behavior for unbounded or invalid
content. Immutable `render-context/v0.14` stays fixed and does not gain an
implicit `content` viewport alias.

### D365-2 — Layout diagnostic payload and rendering boundary

Define structured required-overflow facts—node/source, required and available
logical extent, row/tracks where applicable, and deterministic minimum draft
viewport hint. Ensure engine, row composition, flow, and alignment causes have
distinct actionable detail without leaking renderer coordinates or making
adapters calculate layout recovery.

### D365-3 — Compactness contract correction

Review whether compactness can be a closed View semantic input without
duplicating Theme/Layout authority. If no coherent normalized policy exists,
remove the inert v0.12 syntax and migrate all first-party Views atomically; do
not retain a compatibility no-op.

### D365-4 — Scale evidence and curriculum

Define a public 30-row/100-row scalable Draft curriculum or corpus evidence
that exercises fixed-overflow diagnostics and `auto` extent without adding an
unreviewable giant default corpus artifact. It must use declared metrics and
the public CLI, not a test-only construction.

### D365-5 — Whole-architecture review

Review Context → Layout → Scene → adapter ownership, target semantics, manifest
identity, existing Design Space contracts, and #58 placement boundaries. Decide
whether auto extent is a pre-layout Draft resolution pass or a Layout manifest
mode; reject any design that asks Scene/adapter to resize the canvas.

## Publication and implementation sequence

Publish the design and architecture review, then an implementation plan with
independent slices for contract/diagnostics, Draft auto extent, compactness
migration, and scale evidence. Each slice must be reviewable and tested before
the next. Final acceptance requires focused tests, full suite, conformance,
public materializers, generated SVG review, wheel smoke, and three-OS CI.
