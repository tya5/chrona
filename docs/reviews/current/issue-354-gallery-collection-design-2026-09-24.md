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
| Treatment ladder | visual-grammar | split from elevated Controller Z direction |
| Two surfaces | composition | Halcyon existing evidence |
| Four appearances | appearance | needs two scheme-pinned Contexts |
| Programme at scale | composition | needs normalized Context pairs; overlay waits for #272 |
| Investigating a slip | content | needs normalized Context pairs |

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
