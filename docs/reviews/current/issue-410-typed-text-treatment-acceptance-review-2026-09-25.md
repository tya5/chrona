# Acceptance Review — #410 I410-1 Typed Text Treatment

**Design:** `dafcb31f`; **architecture review:** `e756208b`; **implementation
plan:** `2e74c89f`.

## Accepted scope

I410-1 atomically replaces the live Theme contract with Theme v0.11 and gives
every public text role explicit neutral treatment values: `0em`, `none`, and
`proportional`.  `ThemeTokenView` now exposes one typed `TextTreatment`; no
production caller reads the former partial typography tuple.  Public Theme
v0.10 is rejected at the resource boundary, with no compatibility reader.

Layout applies the finite Unicode transform before every source, table, axis,
label, annotation, relation, legend, summary, and network measurement.  It
carries resolved tracking, transform, numeric-spacing intent, painted lines,
and the selected font asset through `TextPlacement` and `TextLayout`.  Scene
is still a transport/projection boundary: its serializer owns those fields,
and delivery-owner coverage rejects an unowned public Scene field.

SVG, Typst, and TikZ serialize the completed tracking value; they do not
measure, transform, or choose a font.  Default treatment emits no extra SVG
attributes, preserving the public SVG corpus byte-for-byte.  Scene evidence
changes only for the Theme resource content identities, as required by the
immutable provenance contract.

## Deliberate deferrals

`numericSpacing: tabular` is represented but has no public selection in this
slice.  I410-2 will add metric-v3 tabular advances and reject a selected face
without them.  Text orientation and draft system-font resolution remain the
separate I412-1 and I411-1 slices.

## Evidence and verification

* All 21 public materializer Scene records were regenerated from the migrated
  Themes; no generated SVG changed.
* Focused treatment, Scene builder, adapter, contract, materializer, and
  delivery-owner tests passed.
* `python conformance/run_conformance.py` passed.
* `pytest -q -n 4` passed: **831 passed, 19 skipped**.
* `tools/check_scene_primitive_delivery.py` reports 20 Scene dataclasses and
  141 explicitly owned fields.

## Architecture result

The implementation preserves the reviewed authority chain: Theme selects a
finite treatment; Layout owns painted text and geometry; Scene transports the
completed result; adapters serialize it.  No adapter-local fitting, font
fallback, transform selection, or legacy Theme dispatch was introduced.

I410-1 is accepted as the merged prerequisite for I410-2, I412-1, and I411-1.
