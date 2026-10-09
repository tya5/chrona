# Issue #849 — pattern occlusion work record

## Baseline and literal acceptance

Source: [#849](https://github.com/tya5/chrona/issues/849), observed 2026-10-09.
Published source base: `e09c93b33c5b788f8b914edcc44267f83cb7d94f`;
its derived sync must finish before publication. The last ready base is
`510fd5f90bcc057d72e575423ec6e114dfa51837`.

1. A seigaiha tile is expressible without approximation, and the density and contrast gates see the occluded result.
2. Evidence: Yuya's launch window through YAML.

The target authority is `docs/research/presentation/yuya-target-2026-09-26/yuya-board.html`,
lines 181–183: a 20×10 clipped tile, circles centred at (0,10), (20,10),
(10,5), radii 10/7/4. Outer circles fill the substrate then stroke ink;
inner circles stroke ink only. Current filled-only circles cannot express it.
No wider arc-centre/path bounds, project-specific geometry or renderer mask is needed.

Verified discrepancy: an 8×8 tile with a width-1 line at x=0 has normalized
periodic density 1250bp, but its clipped SVG raster has 1024/16384 covered
samples (625bp). All 15 packaged pattern declarations retain their declared
density when independently measured with clipped-cell sampling. This does not
prove all user-authored boundary-crossing patterns remain compatible.

## Design plan

Use cases are general ordered knockouts and outlined circles, including
overlapping concentric scales. The source/catalog carry geometry and paint
channel identities, never colours. Theme/Scheme complete substrate and ink;
Layout completes repeat phase and region/clip; Scene carries the completed
ordered stack; adapters serialize it. Analysis must see the same final stack.

Candidate extension: circle `fillChannel: ink | substrate | none` (omitted:
ink) and optional positive ink `strokeWidth`. Fill precedes stroke within a
circle, and list order is painter order. A substrate channel requires the
existing opaque completed pattern substrate. No-ink results retain the
declared density/perceptibility refusal rather than becoming silent decoration.

Select one tile-boundary rule: clip each tile's ordered primitives before
repeating, matching actual SVG and existing Scene contact. Density measures
the final visible ink on the existing 128×128 centre grid with half-up rounding,
not the union of hidden ink or translated neighbouring shapes.

Contact must not use that density grid as a visibility oracle. Review a bounded
vertical arrangement of circle and linear observer boundaries: extrema,
vertices and pairwise intersections partition x; y-boundaries partition each
slab and event line; witness membership follows the ordered paint stack and
clipped subject. This must retain thin visible remnants and boundary contact.
Reuse the existing eight-chord quadratic observer contract, stroke bodies,
caps and joins. Prune irrelevant shapes; preserve the existing ink-only fast
path. Bound cumulative work across the existing 4096 tile-copy limit and fail
closed on exhaustion or unresolved numeric predicates, never report no ink.

## Decisions and architecture review still required

- Prove the contact arrangement and numeric/degenerate-boundary rules with
  synthetic geometry before finalizing its implementation plan.
- Specify source/catalog version evolution for the changed density boundary
  contract under Spec 56, plus Scene capability/version handling. Do not keep
  contradictory legacy density semantics implicitly when a new field appears.
- Check Specs 08/46/56, existing catalogue import, pattern placement,
  serialization/identity, perceptibility and touched-ink contrast together.
  Preserve the existing opaque channel contrast floors; geometry occlusion is
  not permission to weaken colour contrast.
- Determine atomic resource migration from the actual chosen schema changes.
  Existing package densities need no value edits; generated mirrors still
  require normal regeneration and identity verification if their contract changes.

## Implementation and release planning boundary

Finalize owned files and schema/resource migrations only after the design and
architecture review above are published. Expected seams: source/catalog/Scene
schemas, icon normalization/import, PatternTilePrimitive/placement, Scene
serialization/contact, SVG emission and relevant living specifications.
Keep one work record and one coherent product PR, with separately published
design-plan, reviewed-design and implementation-plan commits before code.

Acceptance evidence must include ordered hidden/remaining ink, multiple
erasers, fill-before-stroke, thin strokes, tile edges and rotations,
deterministic bounded failure, emitted exact circle SVG, post-occlusion density
and contrast, and Yuya YAML. Batch affected renders and public snapshot diffs;
report all unintended corpus changes rather than tuning data to absorb them.
Focused local tests precede PR S0/conformance/materializers and exact-main
three-OS release. Keep the issue open until both literal rows have direct proof.

Status: design-plan draft; no #849 product implementation or acceptance claim.
