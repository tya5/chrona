# Issue #1088 — retire the content-box edge accent

Phase: design and whole-architecture review complete; implementation follows
this publication. Baseline: ready main `28d7f664`; #1130 is merged before code.
Source: [#1088](https://github.com/tya5/chrona/issues/1088). Predecessor: #1049.

## Published baseline and literal acceptance

#1061 has merged: target-B already uses `border.start {width: 3, paint: kind}`.
Two active content-accent declarations remain: Controller Z `annotation-kinds`
and HALCYON `wallboard-annotation-kinds`. Artwork/viewer-fit retain unused edge
values. First-party resources: 55 authored v0.11/v0.13, two derived v0.12.

| Literal acceptance | Required evidence |
| --- | --- |
| no corpus Theme declares edge | Parse all first-party Themes, including unused tokens and packaged resources |
| the accent branch of the kind frame is gone | No edge token/role member or accent measurement/placement path; border-only synthetic coverage |
| S0 gate and corpus diff reviewed | Schema-equivalence, grouped Scene/SVG and rendered image review, full release gate |

## Selected design and architecture review

Use only `annotationContainer.border.<side> {width, paint: kind}` for kind
accents. Preserve `annotation-kind-accent.fill` and its Scheme kind-color
resolution: this is border ink, not a second geometry declaration. Border
Layout owns the full outer edge, mitres/rounded outlines, border-plus-inset
measurement and tilt. Kind-frame Layout owns header/bar/stamp only; remove
its accent fields/insets/import/placement rather than retaining zero-valued
compatibility members. Scene/adapters continue serializing completed geometry.
Shared `side_strip` stays where borders consume it.

Migration is intentionally not byte-equivalent on the two active accent
Themes: the strip moves from inside the content inset to the full outer edge.
Keep its declared side/width and kind paint; do not compensate with spacing,
resource tuning or restored old geometry. Target-B receives only the same
mechanical version migration as other Themes, not presentation edits.

Spec 56 §§3.1–3.2 requires an incompatible successor: authored Theme v0.15
and derived v0.16 (whose complete base/effective schema is v0.15). Migrate all
first-party authored/derived resources, synthetic fixtures and references,
re-pin both derived base identities, then retire v0.11/12/13/14 registrations
and archive their schemas. Inventory removal formerly assigned to #496 is
completed here. Old standalone/copied Themes receive the existing unsupported
version diagnostic; no silent upgrade, dual renderer path or compatibility shim.
No external immutable Theme Store is required by this corpus.

Consistency review: Specs 07/33 retain Theme declaration → measured Layout →
passive Scene/adapter ownership; Specs 08/46 retain kind ink and contrast;
Spec 56 controls version/retirement. Existing border, stamp, tilt, inheritance
and consumer contracts remain authoritative. No new layer or generic solver.

## Implementation plan and publication boundaries

1. Publish this design/review and its Spec 07/56 migration contract before code.
2. One atomic implementation: v0.15/v0.16 schemas, registry/inheritance/colour
   resolution; first-party version migration and derived pins; two active
   border migrations and unused-value removal; remove kind-frame accent path.
   Update synthetic helpers/tests, packaged resource checks and schema inventory.
3. Focused schema/unsupported-version/inheritance and header/border/stamp/tilt
   tests; S0 `python -m tools.schema_equivalence --base-rev origin/main`,
   conformance, package mirrors and content identities. No full local pytest.
4. Publish implementation and a short literal acceptance table in the same PR.
   CI supplies one 64-context snapshot; batch-review changes and SVG/PNG images,
   disclose intentional effects in the PR, require unchanged unrelated output.
   Merge the green ready-base head, then cite the exact published review-containing
   three-OS/reproduction release run before closing. No generated hand edits.
