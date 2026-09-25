# Design Correction — Downstream Allocation After Detail-Panel Completion (#445)

**Corrects:** `issue-445-detail-panel-readability-design-2026-09-26.md`  
**Status:** Proposed before corrective implementation.

## Finding

The first #445 implementation completed `group-details` and `milestones` slot
heights but retained the Layout Manifest's provisional one-line footer height
for later root-column slots.  In `controller-z/annotations`, the annotations
rail begins at the original footer successor position and overlaps the newly
expanded group-detail block.  A Scene-wide audit found these as unhosted text
intersections; they are not intentional host relations and must not become
#446 allowlist entries.

## Corrected ownership

Detail-panel completion owns the entire footer band's final block extent, not
only its two child slot rectangles.  It derives:

```text
provisional footer band = union of content slots sharing the panel baseline
completed footer band  = union after group-details/milestones final allocation
footer growth          = completed block end - provisional block end
```

For a downstream Layout slot that begins after the provisional footer band and
physically spans the expanded panel band, Layout translates its completed
block coordinate by `footer growth`.  This preserves the pre-existing
manifest gap between footer and successor rather than inventing a new spacing
token.  The rule applies only to the Review Detail `annotations` successor;
it does not create a generic Scene collision repair or reposition timeline,
table, legend, notes, or arbitrary View content.

The translated slot is substituted into the completed `SlotPlacement` set
before annotation box/text/leader composition.  Its final bounds, all
annotation primitive bounds, any overflow warning, and the canvas are then
completed by Layout.  Scene and adapters remain pure projection.

## Invariants

1. A final detail panel cannot intersect an annotation text/box/leader rail
   merely because its provisional footer size was smaller.
2. The manifest-established successor gap is preserved exactly when nonzero;
   no hidden margin or renderer reflow is added.
3. If no completed detail panel grows, output geometry remains byte-stable.
4. A context whose annotations are not a downstream physical successor is
   unchanged; the correction is source/geometry constrained, not a global
   overlap heuristic.
5. The #446 evaluator reports the post-completion Scene facts and has no
   special exemption for this relationship.

## Evidence required

- a Controller-Z annotations fixture proves annotations begin after the final
  footer band, do not intersect group details, and preserve the previous
  footer-to-annotation gap;
- public materializer evidence is regenerated for all affected contexts;
- an audit over committed Scenes has zero unhosted group-detail/annotation
  intersections before #446 implementation resumes.
