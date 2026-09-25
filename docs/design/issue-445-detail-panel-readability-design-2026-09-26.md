# Design — Layout-Owned Detail-Panel Readability (#445)

**Design plan:** `issue-445-detail-panel-readability-design-plan-2026-09-26.md`  
**Programme design:** `issue-454-p0-p1-p2-remediation-architecture-design-2026-09-26.md`  
**Status:** Proposed for architecture review.

## Decision

`group-details` and `milestones` are semantic detail panels, not independent
single-line labels.  Layout must compose each into a completed measured text
block before Scene construction.  The block's line breaks, text bounds,
baselines, panel bounds, overflow record, and resulting canvas are Layout
facts.  Scene transports them; adapters serialize the supplied lines and
geometry without wrapping, clipping, or growing a viewport.

This is deliberately a narrow composition policy.  It applies to the two
Review Detail Profile panel sources only.  Notes, legends, table cells, plot
labels, annotations, and arbitrary slots retain their current separately
owned policies.

## Completed panel-block algorithm

For each occupied detail-panel slot, in stable source order
`group-details`, then `milestones`:

1. Take the resolved slot inline start and inline size as the maximum text
   inline allocation.  Reject a nonpositive allocation as an inconsistent
   Layout result, not as a renderer fallback question.
2. Format the existing source value exactly as today, select the existing
   `text` typography treatment and exact font metric, then call the existing
   Layout `wrap_text` routine using that inline allocation.  Its measured word
   and CJK permitted-boundary rules are the only break authority.
3. Emit one `TextPlacement` per semantic entry.  Its `lines` are the completed
   wrapped lines; its bounds use the greatest measured line width and
   `fontSize * lineHeight * lineCount`; its first baseline follows the panel
   cursor and subsequent line baselines are implicit in the measured line
   sequence.  The original unbroken value remains `source_content`.
4. Advance the panel cursor by the completed entry block extent.  Consecutive
   entries have no invented margin; the existing typography leading is the
   declared spacing.  Thus entries cannot overlap vertically.
5. Replace the provisional content-sized `SlotPlacement.bounds.block_size`
   with the final panel block extent.  A `blockSize: content` slot therefore
   has a meaningful completed extent, not the pre-measurement one-line
   placeholder found in the affected evidence.

The final slot rectangle is the containment rectangle for its panel entries.
For normal wrapping every text bound is inside it, with
`GEOMETRY_TOLERANCE`.  Every placement retains its slot identity,
`available_inline_start`, `available_inline_size`, selected font facts, and
normal text paint order.

## Panel-band allocation and non-overprint invariant

The two panel rectangles participate in one Layout-owned `detail-panel` band.
If their supplied inline intervals are disjoint, they retain their allocated
inline coordinates and share their declared block origin.  This is the normal
footer result, including Controller-Z Japanese.

If supplied panel intervals overlap, Layout stacks the later panel below the
previous completed panel, preserving each declared inline interval.  It does
not let their text share physical space merely because the slots happen to
have different source names.  The allocated `SlotPlacement` rectangle moves
with the block, and all text is then composed within that completed rectangle.
This produces a deterministic, visible artifact rather than adjacent-slot
overprint or a new input rejection path.

For all layouts, the following invariants are checked before Scene:

- an entry's inline and block bounds are inside its final panel rectangle, or
  the explicit finite overflow disposition below is recorded;
- group-detail and milestone-digest text rectangles do not intersect;
- each panel's final block extent contains every completed entry assigned to
  it; and
- the completed canvas contains the final panel rectangles and all panel text.

## Overflow and canvas policy

Wrapping resolves ordinary sentences, including Japanese CJK content, without
horizontal escape.  A single unbreakable unit may still be wider than the
slot.  The source slot's existing finite overflow policy decides that case:

- `ellipsize-with-source` resolves the entry with the existing measured
  ellipsis routine and preserves source content;
- `clip-optional` may use its declared optional disposition; and
- `visible-overflow` keeps the completed natural unit, expands the canvas as
  needed, and adds one `FitWarning` with code
  `W_LAYOUT_VISIBLE_OVERFLOW`, failure kind `detail-panel`, and the required
  and available inline/block extents.

Panel block growth that exceeds the requested Context viewport has the same
`visible-overflow` completed disposition: Layout expands `canvas_bounds`
downward and records one deterministic `detail-panel` `FitWarning` for the
affected panel.  A requested viewport is a minimum allocation under #449; it
is not an adapter crop and it does not silently truncate the panel.

No `diagnose` compatibility path is restored.  This design uses the #449
finite warning record and does not let Scene or an adapter choose a different
recovery behavior.

## Ownership and data flow

```text
Review Detail Profile + Layout Manifest + Theme + FontMetrics
                             |
                             v
Layout: format -> measured wrap -> panel rectangles -> completed canvas/warnings
                             |
                             v
Scene: completed Text/Slot/Canvas/FitWarning projection
                             |
                             v
SVG / PNG / Typst / TikZ: serialize completed lines and geometry
```

`review.detail` remains the semantic resolver: it selects group and milestone
records and validates their references.  It must not measure text, choose
line breaks, mutate slot bounds, or decide overflow.  `surface_composer` owns
the new helper because it already owns slot resolution, text measurement,
completed canvas construction, and `FitWarning` production.

## Whole-architecture consistency review

The decision respects the programme's Intent → Layout → Scene → adapter
direction.  It reuses `TextPlacement` rather than adding a renderer-oriented
paragraph model, and uses the existing #449 canvas/warning mechanism instead
of making a valid closure fail for fit.  It makes #445's severe side-panel
case structurally impossible without prematurely implementing #446's general
Scene containment evaluator.  That later evaluator can inspect the completed
slot and text facts here without recreating panel geometry.

No public schema changes are needed: wrapping is a presentation rule of the
existing semantically identified panel sources, while existing declared slot
overflow remains the finite exceptional policy.  This avoids a compatibility
vocabulary and keeps View/Profile semantic data independent of physical line
layout.

## Acceptance evidence

- Unit fixtures prove deterministic CJK lines, exact family/weight/asset
  propagation, slot containment, and no group-detail/milestone intersection.
- A narrow overlapping-slot fixture proves deterministic vertical stacking.
- A long-panel fixture proves expanded completed canvas plus structured
  `W_LAYOUT_VISIBLE_OVERFLOW`, without a Scene/adaptor layout decision.
- Reproduced Controller-Z Japanese executive Scene/SVG shows both panels
  legible; all affected public materializers and generated evidence are
  regenerated in one source-closure pass.
