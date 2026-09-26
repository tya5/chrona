# Implementation Plan — Explicit Unfilled SVG Paint (#456)

**Design:** `issue-456-explicit-unfilled-svg-paint-design-2026-09-26.md`.
**Architecture review:**
`issue-456-explicit-unfilled-svg-paint-architecture-review-2026-09-26.md`.

## I456-1 — Correct the single SVG paint projection

**Files:** `src/chrona/presentation/renderers/v05_svg.py`, focused SVG
adapter tests, a committed-SVG artifact checker and its focused test.

Make the common paint formatter emit exactly one explicit fill for each
drawable: resolved solid/gradient, completed pattern URL, or `none` when the
Scene fill is absent. Preserve Path, marker, icon, and clipPath semantics.
Reject implicit-fill drawables in committed SVGs outside clipPath geometry.

**Acceptance:** stroke-only Rect and Symbol are unfilled, a patterned Rect
retains its pattern, and the artifact checker detects an omitted drawable
fill. No Theme or Scene value is changed by this slice.

## I456-2 — Regenerate and inspect public evidence

**Files:** affected `examples/*/generated/*.svg`; only source or generated
Scene files proven necessary by the diff. The five example manifests are the
public materializer authority. `docs/diagnostics/presentation-contrast.md`
remains checked evidence.

Regenerate the SVGs as one batch. Review the diff by primitive purpose and
confirm only the explicit fill serialization changes. Run all declared public
materializer byte checks, the #431 contrast report check, and the SVG
artifact checker. Rasterize the README hero, a closed-day corpus slide, and
the print-theme milestone slide; inspect them and a representative PNG.

**Acceptance:** all three literal #456 criteria hold across committed
evidence; Theme outline values remain intentional and visible; Scene bytes
remain unchanged unless independently justified.

## I456-3 — Release review

Run focused adapter/artifact tests locally, conformance, and the planned CI
three-OS full pytest/wheel/smoke and newest-Python materializer gate after
the material publication. Record exact commit and run, generated diff scope,
visual findings, architecture boundaries, and every literal issue criterion
in an English acceptance review. Re-review #431's visible-output criterion
against corrected SVG/PNG before closing either issue.

Publish implementation and acceptance phases serially. Fetch remote `main`,
inspect ahead/behind and staged diff, and stop on unexpected remote updates.
