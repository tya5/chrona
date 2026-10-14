# Issue #871 — period-role variants (living design and implementation plan)

**Baseline:** READY `6ab07ba83c52de19a5757ebd9fd4db6abf89761a`; plan selected in
[issue status](https://github.com/tya5/chrona/issues/871#issuecomment-6159401246).
The main branch already meets the reviewer-added literal criteria: "the View override
sets the period-label text"; "absent an override, the output is byte-identical";
"Marquee adopts it"
([acceptance review](../../reviews/current/issue-871-period-label-override-acceptance-review-2026-10-09.md)).
The numbered optional successors are not new quotations or acceptance rows. This
record selects only item 1 (period variants) for its first independently reviewable
slice; edge treatments and a period legend entry remain later, separately designed
slices. Other issue-body items remain unselected.

## Selected behavior and architecture

`View.body.periods[]` gains optional `variant`, using the existing
`common-v0.1.$defs.slug` grammar. No variant retains the unsuffixed role selection.
A variant selects `period-band:<slug>` and, when a drawable label request is
consumed, `period-label:<slug>`. There is no fallback to the base role or another
variant. A selected period still requires its band role even when it clips out or
uses `backgroundTreatment: none`, preserving the existing selection-time rule; a
label role is required at the existing label-consumption boundary (a label whose
period has no drawable extent must not create a request or a new failure). Missing
roles are `E_THEME_ROLE_REQUIRED` at the exact selected Theme role pointer.

Theme inheritance and closed role-property contracts remain authoritative. Only the
two period role families recognize suffixes, with the base band's pattern,
background-treatment and opacity properties and the base label's text,
ink and contrast properties. Layout receives resolved selected roles and uses them
consistently for band paint/background checks and label measurement. It records the
selected role on `ShapePlacement.visual_role` and the label's `TextPlacement` role;
pattern completion, Scene projection, contrast and target-capability checks consume
those completed roles. The band/label purpose, period `sourceRef`, and existing
placement/Scene identity do not change. `period-label-chip` remains shared. No
general dynamic-role mechanism, Project rule, edge treatment, legend-entry policy,
or example edit is introduced. The two suffix namespaces become reserved semantic
roles; a pre-existing arbitrary axis/legend alias using them must be renamed or
satisfy the new contract. This is intentional alpha incompatibility, not a reason
to retain an open-role fallback. Other valid unvaried resources retain their output.

This preserves the existing separation: Project owns dates, View selects and
names the presentation variant, Theme owns tokens, Layout owns measurement and
geometry, Scene carries completed primitives/roles, and adapters serialize without
role lookup or substitution.

## Implementation plan and evidence

1. Add `variant` to `schemas/view-v0.28.schema.yaml` as an optional reference to
   the common slug; normalize it in `src/chrona/presentation/contracts/resources.py`
   and carry it on the selected period projection. Run
   `python -m tools.schema_equivalence --base-rev
   origin/main` and record the additive result.
2. Extend only `period-band:<slug>` and `period-label:<slug>` in
   `src/chrona/presentation/scene/capabilities.py`, role-consumer/pattern
   recognition and required-role validation. Keep exact role-property validation
   and diagnostic pointers. Update `surface_periods.py`, completion and Scene
   projection so the selected role is carried and used by every relevant paint,
   measurement, contrast and capability path.
3. Focused tests: schema/slug rejection; no-variant Scene/SVG byte identity;
   two variants on one View with different band paint/pattern and label typography;
   missing band and label roles with exact pointers; base-role non-fallback;
   selected band role required for out-of-window and `none` treatments; an
   out-of-window label creates no request; stable period purpose/source/identity;
   and selected-role contrast/pattern/capability checks. Run named-period tests,
   Theme role consumer/capability tests, Scene contract tests, conformance and the
   public materializer. Inspect the derived snapshot as a batch; existing unvaried
   evidence must remain byte-identical. CI supplies the planned release matrix.

Affected owners/files: View schema and resource contract; period projection;
Theme role capability, consumer, token and closure checks; Layout period completion;
Scene builder/semantic-role provenance; Specifications 06, 07, 08 and 50; focused
View/theme/period/Scene tests. No examples or generated files are hand-edited.
Before code, review whether Theme token reads, pattern admission, background opacity
and rank validation, text measurement, Scene contrast and target capability all
use the selected role rather than silently retaining the base role.

Architecture review (dev A): accepted for this slice against Specs06/07/08/50,
Spec56 optional-member rules and the existing582/497 boundaries. The current
`compose_period_bands` validates band treatment before clipping, while
`period_label_requests` creates requests only from completed drawable extents;
the selected missing-role timing above preserves both boundaries. Semantic
overlay rank and the shared label chip remain unchanged. Selected-role propagation
must include background validation, catalog patterns, Theme contrast admission and
Scene capability checks; these are implementation gates, not new policy owners.

## Variant-slice implementation evidence (partial; issue remains open)

Implementation and synthetic tests are committed locally at
`1ab5febc` (`feat: carry View-selected period variants through completed placements`),
not yet published to `main`. The focused command
`./.venv/bin/python -m pytest -q tests/integration/test_named_periods.py tests/unit/chrona/presentation/test_color_scheme.py tests/unit/chrona/presentation/test_role_admission.py tests/unit/chrona/presentation/scene/test_capabilities.py tests/unit/chrona/presentation/model/test_semantic_registry_contrast.py`
passes: **158 passed**. It covers two simultaneously selected variants with
distinct band paint, opacity and order; label font size and letter spacing
changing completed bounds, baseline and Scene TextLayout; selected-role contrast
floors; background collision behavior; catalogue-pattern admission; unsupported
property pointers; default output identity; and missing-role timing.

Schema equivalence against `origin/main` passes L1 with `additive=1, equal=37`
for the optional common-slug View member. Six merged #1341 L1 expected-delta
records were mechanically retired after proof against their landing commit and
first parent; all L2/L3 records were preserved. The stale-entry pruner could not
rewrite these block-style mappings because its rewrite loop parses a single
top-level line as a whole YAML record (`E_EQUIV_DELTAS_ENTRY:{'layer':'L1'}`).
After retiring only the proven-stale records,
`python -m tools.schema_equivalence --base-rev origin/main --prune-stale`
exits successfully; no schema-gate tooling was changed.

This evidence is limited to the selected variant slice and local focused tests;
the final CI/public-derived batch is pending publication. Edge treatments and
the period legend entry remain unimplemented, separately selected follow-ups.
