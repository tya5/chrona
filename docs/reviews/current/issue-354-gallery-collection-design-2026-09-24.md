# Issue #354 — Gallery Collection Design

**Decision:** Accepted

## Collection contract

The gallery is upgraded atomically to `chrona/design-gallery/v0.2`.  There is
no compatibility reader for v0.1.  Each entry retains its documentary source,
narrative, target assertion, and accessibility note, and adds:

```yaml
comparison:
  set: executive-status
  dimension: content
  axis: actual-versus-plan
```

`dimension` is exactly one of `content`, `composition`, `visual-grammar`, or
`appearance`.  All peers in a set must declare identical `dimension` and
`axis`; each set has at least two entries, identical pinned Project and Actual
references, and at least one different View/Theme/Scheme/Layout reference.
The target is evidence metadata, not a fifth Design Space dimension.

The catalogue may additionally contain a documentary `deferred` list. Each
item has an `id`, a proposed `dimension`, and a non-empty `blocker`. Deferred
items have no corpus slide or SVG and cannot appear in a comparison set. This
makes known collection work visible without fabricating evidence.

Some Content choices require a typed Layout companion before Scene can form
the selected primitive family. `comparison.supports` is therefore an optional,
lexically ordered documentary list of coupled owner names. It never adds a
second compared dimension. For a surface set it may contain only `layout`; the
peer page must disclose that support diff. The attempted dependency-network
Context with a table-timeline Layout failed `E_PRESENTATION_PRIMITIVE_MISSING`,
which proves this is a product contract dependency rather than gallery prose.

## Generated documentation

`tools/render_design_gallery.py` is a read-only documentation generator.  It
consumes the validated catalogue, declared contexts, committed materializer SVG
evidence, and the committed corpus coverage report.  It writes:

```text
docs/gallery/README.md          generated collection index
docs/gallery/sets/<set>.md      generated peer page
```

Each set page contains a peer table, inline relative SVG links, immutable
Context/resource provenance, and a normalized reference diff.  The diff is
limited to `view`, `theme`, `colorScheme`, and `layout`; it never reads or
prints Project/Actual facts. Generated pages are documentation, not a renderer
input and not materializer evidence.

## Initial collection

The first non-blocked collection is deliberately limited to existing, declared
evidence and new contexts over existing resources:

| Set | Dimension | Status |
| --- | --- | --- |
| Executive status | content | split from existing Controller Z pair |
| Treatment ladder | appearance | split from elevated Controller Z direction; treatment is Theme-owned |
| Two surfaces | content | Halcyon evidence with disclosed `layout` support; `surface` is View-owned Content per Specification 55 |
| Four appearances | appearance | needs two scheme-pinned Contexts |
| Programme at scale | composition | needs normalized Context pairs; overlay waits for #272 |
| Investigating a slip | content | needs normalized Context pairs |

### Corpus-resource correction

The initial issue text assumed Controller Z already contained dark and
print-mono Schemes. It does not. Halcyon-1 is the existing corpus with the
three compatible appearance resources (`mission-light`, `control-room-dark`,
and `print-mono`). The first appearance set therefore uses one fixed Halcyon
View/Theme/Layout under those three Schemes. A fourth appearance is not
invented by copying a screenshot: it remains a later, separately designed
Theme/Scheme resource slice. This correction preserves the one-axis rule and
does not make a nonexistent Controller Z resource part of the gallery contract.

The existing Controller Z elevated direction changes a Theme-owned
gradient/shadow treatment. It is therefore an `appearance` set, not a
`visual-grammar` set: visual grammar remains the View/semantic-presentation
owner. This distinction is enforced rather than narrated around.

### Layout-composition correction

The existing Halcyon `briefing` View/Theme cannot be re-pinned under the
existing `wallboard` Layout: it first rejects unknown layout tokens, and with
the wallboard Theme/Scheme rejects table overflow. The present resources are
therefore not composable peers. `Programme at scale` remains deferred pending a
dedicated responsive View/Layout design that proves all peer contexts valid;
it must not be satisfied by changing Theme, Scheme, View, and Layout together.
The gallery index records this as a design backlog alongside #272 rather than
claiming a one-axis Composition comparison that does not exist.

Slot-focused set 8 and encoding set 7 require their own View/Layout or
encoding prerequisites and remain subsequent slices. CJK set 9 is blocked by
#351. Multi-target set 10 requires a new evidence contract and is not a Design
Space set.

## Validation and diagnostics

The inventory validator owns stable gallery diagnostics:

- `E_DESIGN_GALLERY_DIMENSION` for absent/unknown/mixed dimension;
- `E_DESIGN_GALLERY_AXIS` for absent/mixed axis;
- existing provenance, pair, target, and accessibility diagnostics for all
  other contract edges; and
- `E_DESIGN_GALLERY_EVIDENCE` for a declared slide missing its generated SVG.

Validation remains documentation-only.  It has no import path into render,
Layout, Scene, adapters, public materialization, or scheduling.

## Architecture review

This design fulfills Specification 58's one-way evidence flow and
Specification 55's four selectable dimensions. It consumes #355's report as
backlog data without turning coverage into a gate. It does not revive the
deferred package/acquisition design, add raw SVG source authority, or make the
Color Scheme comparison CLI into a gallery resolver.
