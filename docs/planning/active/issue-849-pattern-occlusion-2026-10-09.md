# Issue #849 — pattern occlusion work record

## Baseline and literal acceptance

Source: [#849](https://github.com/tya5/chrona/issues/849), observed 2026-10-09.
Published ready base: `b06897db78492fd070bed249d601001c11dee0b7`
(derived-main run 37869675074 passed). This contains reviewer source `e09c93b3`.

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

## Selected design

Use cases are general ordered knockouts and outlined circles, including
overlapping concentric scales. The source/catalog carry geometry and paint
channel identities, never colours. Theme/Scheme complete substrate and ink;
Layout completes repeat phase and region/clip; Scene carries the completed
ordered stack; adapters serialize it. Analysis must see the same final stack.

Extension: circle `fillChannel: ink | substrate | none` (omitted:
ink) and optional positive ink `strokeWidth`. Fill precedes stroke within a
circle, and list order is painter order. `none` requires a positive stroke.
A substrate channel requires the
existing opaque completed pattern substrate. No-ink results retain the
declared density/perceptibility refusal rather than becoming silent decoration.

Select one tile-boundary rule: clip each tile's ordered primitives before
repeating, matching actual SVG and existing Scene contact. Density measures
the final visible ink on the existing 128×128 centre grid with half-up rounding,
not the union of hidden ink or translated neighbouring shapes.

Contact does not use the density grid as a visibility oracle. The two production
sparse-contact callers (`contrast_policy._frame_tinted` and `surface_overprint`)
only admit fill-less patterns. Substrate operations require an opaque substrate,
so paint completion rejects them on ink-only roles before returning a Scene.
Opaque patterned hosts retain the existing conservative two-colour contrast
policy, not a new point-local policy. Final positive density ensures ink survives;
no surviving ink is refused, rather than retaining hidden ink in reported density.

Sparse patterns therefore remain unions of ink shapes. Extend their exact contact
only for circle strokes: a clipped convex query polygon's radial-distance range
must intersect `[max(0,r-width/2), r+width/2]`. Minimum distance is zero if the
centre is inside, otherwise the minimum edge distance; maximum is over vertices.
Filled ink plus stroke is the outer disk. Keep inverse phase/rotation, closed
boundary contact, existing path/cap/join rules and the 4096-copy bound. A substrate
operation reaching the sparse observer is an unsupported-geometry failure,
never invisible ink. A general boolean-geometry arrangement is not needed by
any admitted paint path.

## Architecture review and migration decision

- Specs 08/46: opaque hosts have two role colours; sparse contact only concerns
  fill-less overlays/textures. Rejecting missing substrate is the existing paint
  contract, not a project/role exception. Density and pairwise contrast now see
  the completed visible result. No contrast floor or candidate geometry changes.
- Spec 64 explicitly gives v0.1 sources/v0.4 catalogues periodic-union density.
  Use source v0.2, catalogue v0.5 and normalization profile v0.2 for the corrected
  clipped painter-order contract; do not reinterpret v0.1/v0.4 in place. Retire
  their current authoring readers after atomic first-party pin migration. Keep
  the independently supported icon-only v0.3 Material catalogue unchanged.
- Scene v0.7 gains optional circle channel/width fields: omission still means
  filled ink. `densityBasisPoints` remains the completed intrinsic ink fraction;
  the current producer supplies verified post-composition coverage, not source
  policy or a second density field. No catalog/profile identity crosses to Scene.
- New schema properties reference one shared graphics definition. Existing
  circle coordinate/radius rules, arc/control-point bounds and path observers
  stay unchanged. Density uses 16 quadratic chords; contact uses eight.
- Spec 64's pinned catalogues are immutable. Publish successor source/catalog/
  manifest identities, update Context/library pins, and regenerate mirrors with
  normal tools. All 15 current package density numbers remain unchanged. Retire
  superseded live resources without overwriting their published identities.
- Source normalization owns finite channel composition, Layout geometry/phase,
  Scene complete geometry/paint relations, observers inspection and adapters
  serialization. No dependency, new layer, authored colour, mask or scheduling
  policy is introduced. Catalog SVG definition identifiers may change as their
  completed primitive representation evolves; disclose these nonvisual diffs.

Resource selection: successor starter, target-parts and annotation-parts IDs
use `v2026-10-09`, retaining their set names and notices. Add the exact nine-circle
`seigaiha` to target-parts; Yuya selects `chrona-target-parts:seigaiha` instead
of the retained starter approximation. This is the issue's required target
evidence, not compensation for a core side effect. Keep all other target
styling unchanged. The reference's per-circle opacity 0.9 is not a new asset
channel: the exact geometry uses the existing opaque pattern contract.

## Implementation and release planning boundary

Finalize owned files and schema/resource migrations only after this reviewed
design and the normative specification updates are published. Expected seams: source/catalog/Scene
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

Status: reviewed design; publish with normative specifications before finalizing
the implementation plan. No #849 product implementation or acceptance claim.
