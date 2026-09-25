# Implementation Plan — Typography, Orientation, and Draft System Fonts

**Design:** `dafcb31f`; **architecture review:** `e756208b`.

## I410-1 — Typed treatment and Theme migration

Create Theme v0.11 schema/resource dispatch and migrate every public Theme in
one atomic change.  Add typed `TextTreatment`, defaults explicitly expressed
in every role, and treatment propagation through source measurement,
`TextPlacement`, `TextLayout`, Scene serialization, and SVG/typeset adapters.
Do not add numeric tabular selection or rotation in this slice.

**Acceptance:** transformed text and letter spacing have identical Layout and
adapter values; old Theme versions are rejected; all public corpus byte checks
remain stable under explicit defaults.

## I410-2 — Metric v3 and tabular numeric evidence

Add declared metrics v3 with tabular advances, importer/resource closure,
validation, and target feature projection.  Reject `numericSpacing: tabular`
for a face without measured support.  Add a HALCYON signed-days column using
the selected treatment and regenerate its public Scene/SVG evidence.

**Acceptance:** measured digit widths, ellipsis/wrap behavior, and rendered
numeric spacing agree; neutral text remains proportional; public table bytes
show the finite selected identity without a renderer fallback.

## I412-1 — Layout Profile v0.8 and completed orientation

Replace Layout Profile v0.7 with v0.8, migrate every public profile, split
`flowDirection` from finite View text-orientation intent, and carry completed
orientation/occupied bounds through Scene and every adapter.  Add a rotated
label corpus fixture plus collision, overflow, and target projection tests.

**Acceptance:** unsupported former writing-mode declarations reject; rotated
fit uses swapped bounds; SVG/PNG/PDF/typeset evidence uses the same supplied
angle and no adapter infers one.

## I411-1 — Draft-only system font resolution

Add explicit Draft CLI/workspace opt-in, injected platform resolver, generated
metrics, nonportable `DraftFontResolution`, exact-file raster handoff, and
absence/ambiguity diagnostics.  Keep it outside Context schema and Scene
serialization.  Add immutable render/materializer rejection tests and fake
resolver tests; do not add system font corpus evidence.

**Acceptance:** an installed test font can drive Draft SVG/PNG measurement and
paint without copying bytes; a missing/ambiguous request diagnoses; immutable
paths cannot consume the resolution.

## I410-3 — Programme release gate

Regenerate affected reports, vocabulary/diagnostic inventories, all affected
public materializers, and one visual review batch.  Run focused tests, full
pytest, conformance, structural gates, built-wheel isolated smoke, and
three-platform CI.  Publish an English acceptance review mapping #410/#412/#411
to public evidence; close only accepted issues.

## Publication rule

Each slice is one serial fast-forward publication.  Before each push fetch
`origin/main`, verify the exact ahead/behind range and clean worktree, then
verify the remote commit.  If implementation reveals a missing ownership or
geometry rule, stop the slice, amend design and architecture review publicly,
then resume; do not add a compatibility reader or adapter-local workaround.
