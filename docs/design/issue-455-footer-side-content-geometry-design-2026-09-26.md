# Design — Footer Side-Content Geometry Closure (#455)

**Design plan:** `issue-455-footer-side-content-geometry-design-plan-2026-09-26.md`.
**Status:** Proposed for architecture review.

## Problem and boundary

The footer is a physical Layout band containing independently selected content
families: group-detail blocks, milestone digest blocks, observations, legend,
and notes.  #445 completes only the two paragraph-like families.  The generic
notes loop advances by font size rather than measured text block height, while
the legend loop measures labels against an interval that includes its swatch.
Both emit a Scene that correctly projects invalid Layout geometry.

This design completes ordinary notes and legend entries without merging their
semantic resolvers or moving geometry into Scene/adapters.  It also corrects
the footer-band handoff so an expanded notes/legend slot is visible to the
existing physical `annotations` successor rule from #445.

## Ownership

```text
Review Detail / project notes / legend intent + Theme metrics + resolved slots
                                  |
                                  v
Layout: closed visual reservation, measured text, completed per-slot extent,
        footer-band extent, successor translation, warnings and canvas
                                  |
                                  v
Scene: supplied slots, lines, bounds, warnings and primitive facts
                                  |
                                  v
Adapters: stable serialization only
```

The existing group-detail/milestone helper remains the authority for their
paragraph wrapping and stacking.  A small footer-band coordinator owns only
the completed child-slot map and physical successor translation.  It does not
select content, wrap an unrelated family, or perform a global overlap repair.

## Completed composition rules

### Notes

For a populated `notes` slot, Layout composes notes in their existing stable
source order.  It places each text run using the selected `text` typography,
then advances the cursor by that completed placement's measured block extent.
The final notes slot block extent is the maximum of its declared provisional
extent and the completed cursor extent.

This uses the existing line breaks/normalization for notes.  It does not add a
new wrapping or View syntax.  If a declared note disposition permits natural
visible overflow, Layout completes its warning and canvas under #449; it never
stacks subsequent notes through an earlier measured run.

### Legend

A legend row has two closed subregions: a swatch primitive and a text interval.
`swatch_size * 1.5` is the existing leading reservation from the slot inline
start to the label start.  Layout computes:

```text
text inline start = slot inline start + leading reservation
text available size = slot inline size - leading reservation
```

The text interval, not the full slot, is passed to measurement and every
overflow disposition.  For `ellipsize-with-source`, Layout calls the existing
source-preserving ellipsis operation before `place_text`; the emitted bounds
must be contained in this interval and therefore in the slot.  The swatch
remains a separate primitive contained in the leading reserved region.

For `visible-overflow`, Layout emits the natural label, one deterministic
`W_LAYOUT_VISIBLE_OVERFLOW` fact using the text interval as `available_inline`,
and completes the canvas.  It does not silently use a full-slot measure to
avoid the warning.  `clip-optional` follows its existing completed suppression
record; no SVG clip is invented.

Legend rows retain their current deterministic vertical sequence.  The final
legend slot extent contains the actual row sequence or completes a permitted
overflow/canvas result through Layout.

### Footer-band completion and successor

The footer-band coordinator receives the resolved provisional slots and final
replacements from group-detail/milestone, notes, and legend composition.  It
derives the provisional and completed union extent over the finite footer
source set:

```text
group-details, milestones, observations, legend, notes
```

It then applies #445's source-and-geometry-constrained translation only to the
physical downstream `annotations` slot when the completed union grows.  The
translation preserves the manifest-established gap and occurs before
annotation text/box/leader composition.  A changed notes or legend height thus
cannot recreate the stale-footer overlap that #445 corrected.

## Invariants

1. Adjacent required project-note text blocks in one notes slot have no
   positive-area intersection at Layout micro-point tolerance.
2. Every `ellipsize-with-source` legend text placement is contained in its
   available text interval and parent slot; its `source_content` remains the
   unabridged source.
3. A completed footer child extent participates in the one footer-band union
   before its physical annotations successor is composed.
4. Explicit `visible-overflow` remains a successful, warned Layout result and
   may not be converted into a silent ellipse or adapter crop.
5. Scene and adapters receive only completed geometry.  No Scene evaluator,
   #446 finding, or renderer behavior is an exemption for note/legend errors.

## Compatibility and migration

No compatibility reader or legacy geometry behavior is retained.  Existing
View/Profile syntax stays unchanged; the migration is source-composition plus
all affected public generated evidence in one release slice.  #449 remains the
sole overflow-policy authority, #445 remains the paragraph-panel authority,
and #446 remains a Scene observer.

## Required evidence

- focused notes fixture with multiple lines proves measured cursor advancement,
  source order, final slot extent, and no text intersection;
- programme-board legend fixture proves swatch reservation, source-preserving
  ellipsis, final containment, and no geometry change in unrelated legends;
- footer-growth fixture proves annotations retain their old manifest gap after
  notes or legend, not only group-detail/milestone, expands;
- public materializer regeneration, tolerance-aware Scene audit, generated
  SVG/raster inspection, structural Layout/Scene boundary checks, and CI
  evidence complete the slice.
