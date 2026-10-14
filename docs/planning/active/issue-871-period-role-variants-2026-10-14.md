# Issue #871 — named-period follow-ups

## Published baseline and scope

Variants landed in [PR1486](https://github.com/tya5/chrona/pull/1486), source
289f91f4d29b895e18c998be8ba22f11bf5779aa, from READY68457b29.
Its 158 focused tests pass; after base adoption, 73 period/closure tests pass.
Schema L1 is additive=1/equal=37; lifecycle23 passes. All92 public Scene/SVG
files in artifact11867057879 are byte-identical. Exact-main release is pending.
Six proven-stale L1 records were retired manually because the pruner cannot
rewrite multiline mappings; no schema-gate code changed.

Board-selected scope is issue-body items1–3 only: variants, edge treatments,
period legend entries. Items4–8 are unselected optional successors.
Literal reviewer acceptance, already met on main and retained in the
[current review](../../reviews/current/issue-871-period-label-override-acceptance-review-2026-10-09.md):

- "The View override sets the period-label text."
- "Absent an override, the output is byte-identical."
- "Marquee adopts it."

## Next design and architecture review

Selected contracts are normative in Specs[06](../../specification/06-view-model.md#71-named-periods-582),
[07](../../specification/07-style-and-theme.md),
[08](../../specification/08-scene-and-rendering.md), and
[50](../../specification/50-constraint-driven-gantt-surface-quality.md).
Optional Theme/Detail Profile members preserve omission behavior and are added
in place under Spec56; no adapter/Scene schema field is introduced.
Root's consistency review accepts the boundaries below against Specs06/07/08/50,
Spec56 schema evolution, Spec63 effect geometry and the accepted glyph-outline
precedence. Publication of this design/plan is required before implementation.

Project owns period identity/dates; View selects periods/variants; Detail Profile
opts into source-bound legend entries; Theme supplies paint and rule dimensions.
Layout owns edge geometry, fit, one-list legend measurement/placement and identities.
Scene binds completed channel intent to paint, then clears it; adapters serialize.
Add a transient completed-shape channel mask, distinct from catalogue part
intent: existing glyph mode has an intentional Theme-outline precedence, not
fill-only semantics. Glyph overrides/classification remain Symbol-only.
Do not duplicate the legend pipeline or relax overlapping-period fill rank checks.
Sourced legend IDs use disjoint prefixes (legend-period / legend-period-swatch),
not pseudo-role keys that can collide with arbitrary existing role aliases.
Existing role-wide wording precedence and unsourced IDs remain unchanged.

## Implementation plan — one atomic edge/legend publication

1. Theme schema/role admission and Layout period-edge completion: selected
   single/double rules, authored gap, fill-only host or outline-only paths,
   exact pointer diagnostics and geometry derived from the completed clipped band.
   Owners: theme schema, token reader/consumer/capability checks, surface_periods,
   surface_backgrounds and surface_quality.
2. General transient shape paint channels and Scene projection; keep glyph overrides
   Symbol-only and clear intent before returned Scene. Owners: scene model/paint,
   v05_builder and layout placement types. No adapter-generated geometry.
3. Detail Profile sourceRef and one typed legend list: resolve against
   projection.periods, reject ambiguous/unknown/duplicate/mismatched sources,
   carry identity independently of visual role; reuse period edge completion,
   existing area-key dimensions, pattern/opacity and legend slot. Owners:
   detail schema/contracts, surface_content, v05_content/profile_connections,
   surface_legend/completion and Scene legend projection.
4. Synthetic tests: omitted-field Scene/SVG identity; base/variant roles;
   single/double sides and exact fit refusal; fill versus outline/none; pattern
   hosts and translucent-rank regression; legacy glyph/channel serialization;
   same-role periods plus an unsourced same-role entry with unique identities;
   source/role diagnostics, wording precedence, swatch fidelity and slot sizing.
   Run focused tests, schema equivalence and conformance locally. Inspect the CI
   public derived batch and intended deltas; CI supplies full three-OS release.

Publish this design/architecture review and plan before code; publish the
implementation and concise literal/selected-scope review together. No examples
or derived-report edits. Keep871 open until items1–3 and every literal criterion
have direct evidence plus successful exact-main containing-review release.
