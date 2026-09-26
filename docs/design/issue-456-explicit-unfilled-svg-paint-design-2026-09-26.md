# Design — Explicit Unfilled SVG Paint (#456)

**Design plan:** `issue-456-outline-paint-design-plan-2026-09-26.md`.

## Contract and decision

`ScenePaint.fill = absent` means that a drawable primitive has no fill. SVG's
initial `fill` is black, so the SVG adapter must serialize an explicit
`fill="none"` whenever it projects a stroke-only completed paint. This is a
target encoding of an existing Scene fact, not a new Theme or Scene policy.

All drawable SVG shapes carry one effective fill attribute. The adapter's
common paint formatter owns that attribute for canvas, Rect, Text, Symbol,
and Path. A patterned Rect passes its completed pattern URL as the explicit
fill override; a solid or gradient paint passes its completed fill; a
stroke-only paint passes `none`. Marker and icon path formatters already emit
an explicit fill and retain their separate finite asset/marker contracts.
ClipPath geometry is structural and excluded from the drawable-shape check.
The PNG path consumes this corrected SVG unchanged.

The formatter must emit one fill attribute, never a pair whose later value
silently wins. It may format a completed gradient/pattern reference but may
not infer a colour, opacity, or treatment from a semantic role.

## Closed-day appearance choice

The nine public Theme source files currently declare `calendar-closed` as an
outline with a named stroke and width, and opacity 1. The #431 Scene report
measures the declared stroke against the canvas at or above its 1.10:1 floor.
Preserve that explicit outline treatment for all nine appearances in this
correction. Their former black fill was never an intended tint. Review the
regenerated SVG and PNG, including the README hero, before accepting this
choice. A later change from outline to fill would be a separate Theme design
decision with a new corpus contrast measurement, not an adapter workaround.

The print Theme's outline milestone stays a hollow Symbol using its declared
stroke. No mark geometry or Layout allocation changes.

## Artifact-level invariant

A repository check scans every committed public SVG. Each drawable `rect`,
`path`, `circle`, `ellipse`, or `polygon` outside a `clipPath` must have an
explicit fill attribute. The check does not inspect SVG pixel colour or
override the Scene contrast policy. It catches a future serializer branch
that accidentally falls back to SVG's initial black fill. The same fixture
also checks stroke-only Rect and Symbol projection and a patterned Rect, so
the non-black fix cannot erase pattern paint.

For release acceptance, compare the corrected SVGs against the committed
versions, rasterize the README hero, one closed-day corpus slide, and the
print milestone slide, and inspect representative pixels/appearance. Verify
the #431 contrast report still passes and that the public materializer
reproduces every changed SVG byte.

## Architecture and migration

Scene continues to carry renderer-neutral completed channels. Layout owns
geometry; the SVG adapter owns only faithful target serialization. The
correction makes the adapter obey the already published completed-paint
contract in specification 46. No Scene schema version or Theme migration is
required. Generated public SVG bytes change intentionally; generated Scene
bytes should not change for this correction.
