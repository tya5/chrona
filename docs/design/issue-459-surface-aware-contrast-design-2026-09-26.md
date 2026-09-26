# Design — Surface-Aware Contrast (#459)

**Plan:** [design plan](../planning/active/issue-459-surface-contrast-design-plan-2026-09-26.md).
This corrects the canvas-only ground rule in the #431 design; the earlier
record remains historical evidence, not current normative policy.

## Use cases and selected contract

A reviewer must see a late finish delta and the marks carrying planned or
actual work, including on a raised panel. The completed Scene, not a Theme
guess or raster adapter, is the authority for the effective ground.

1. `variance-behind` is always `required` at 4.5:1. Both Theme closure and
   completed-Scene checking enforce it. Any old `deemphasized` declaration is
   invalid for this role; migrating the current light-family amber is an
   intentional appearance change, not a compatibility fallback.
2. The finite mark class includes the Scene roles `planned`, `actual`,
   `snapshot`, `scenario`, `missing-actual`, `summary-bar`, `progress-fill`,
   and `network-node`; milestone point symbols sharing these roles are covered.
   A mark's visible fill or stroke must reach 3.0:1 against its actual ground.
   When both channels exist, the higher-contrast channel may carry the outline;
   the report records which channel was used. This is a project visibility
   floor for data marks, not a claim that all backgrounds are text.
3. A classified primitive's sample is the centre of its completed bounds.
   Consider only earlier painted, opaque, flat-filled Rects whose completed
   bounds contain that point. The highest `(paintOrder, primitive index)` wins;
   otherwise the opaque canvas wins. Record the ground primitive id (or
   `canvas`), its colour, and the evaluated channel in each finding. A
   translucent/gradient host is not silently treated as opaque: an unsupported
   overlapping host is a diagnostic requiring an explicit future policy.
   Stroke-only hosts do not supply a filled ground. A mark with no drawable
   flat channel is a diagnostic, not a passing mark.
4. The checked report retains its per-role summary and adds per-primitive
   rows with Scene path, primitive id, ground identity/colour, channel, ratio,
   and floor. The report is evidence, never a repainting mechanism.

## Responsibilities and migration

Theme/Scheme declare the paint and state-text treatment. Scene projection
preserves completed geometry, paint and order. A pure Scene analysis evaluates
classified roles against completed earlier paint; it never changes placement
or colour. Adapters serialize the completed Scene unchanged. Update all
affected light Themes/Schemes in one implementation slice with materialized
Scene/SVG and checked report; no partial release that breaks public contexts.

Bounds-centre sampling is deliberate finite evidence, not a general pixel or
glyph contour proof. The public SVG inspection must separately check that
visible adapter output agrees for the affected planned bars. Gradients,
shadows, and images under classified marks require a later explicit contract.
