# Implementation Plan Amendment — Current Role/Property Admission (#478 I478-3/4)

**Amends:** [original implementation plan](issue-478-declared-treatment-visibility-implementation-plan-2026-09-26.md).
**Published design authority:** [2026-09-27 correction](../../design/issue-478-role-admission-rebase-correction-2026-09-27.md),
[whole-architecture review](../../reviews/current/issue-478-role-admission-rebase-architecture-review-2026-09-27.md),
the [axis-typography amendment](../../design/issue-478-axis-typography-role-admission-amendment-2026-09-27.md)
and its [review](../../reviews/current/issue-478-axis-typography-role-architecture-review-2026-09-27.md),
the [legend fallback amendment](../../design/issue-478-legend-role-admission-amendment-2026-09-27.md)
and its [review](../../reviews/current/issue-478-legend-role-admission-architecture-review-2026-09-27.md),
Specifications 07, 33 and 39, including the schema-description alignment
published through `a7375fdd`. I478-1/2 are already accepted; their code and
public information semantics are not reopened.

**Design correction before code:** the [open-role overlap correction](../../design/issue-478-open-role-family-overlap-correction-2026-09-27.md)
and [architecture review](../../reviews/current/issue-478-open-role-family-overlap-architecture-review-2026-09-27.md),
published at `7f76bed9`, supersede the custom-axis paint negative test below.

## Literal acceptance carried forward

1. Rendering `elevated-light` under the default profile emits a diagnostic that names the dropped treatment and the profile that would paint it.
2. A Theme property on a role that cannot carry it is diagnosed at load time.
3. Suppressed plot labels are counted in an info diagnostic, or the View can ask for a visible marker on rows whose label was suppressed.

I478-3 proves row 2; I478-4 rechecks all three on current public output.

## I478-3A — Finite consumer inventory and focused admission tests

**Owners:** `src/chrona/presentation/scene/capabilities.py` (one explicit
role/property consumer projection beside the existing ceiling),
`src/chrona/presentation/color_scheme.py` (validate direct and Scheme target
applicability after effective insertion), and the existing closure error
projection only if its exact pointer is lost. Tests belong under
`tests/unit/chrona/presentation/scene/`, `tests/unit/chrona/presentation/`
and closure integration tests. The registry must distinguish Theme role,
Scene role, primitive kind, typography/geometry/paint/policy consumer and
explicit dynamic family. Test a custom View-named axis typography role with
allowed measured properties. Reject a Scheme paint target on known
measurement-only `axisMonth`/`axisQuarter`; admit a paint target on a novel
name as a potential legend Rect binding, while proving it does not paint
an axis label. Test the
bounded arbitrary legend-only Rect paint family and reject an unknown
geometry property or a known Text role's stroke even if a legend could name
that role. This replaces the original plan's unqualified “unknown role”
negative test: a novel paint-only legend role is a valid #427 producer,
while an unknown role/property pair with no consumer must fail. Test the
actual #426 axis tiers, #464 glyphs,
#465 image note, #466 annotation/group-header roles and #479 profile roles.

**Focused gate:** every supported property class on capable and incapable
roles; unknown role with a property outside both bounded open-name families;
direct `/body/roles/...` and Scheme
`/body/colorBindings/...` pointer; effective derived Theme; Draft and
immutable closure; rich-profile `planned` shadow admitted, text-only stroke
and Path gradient rejected; Text/Icon shared-role effects; nested
`annotationContainer` accepted only on the four annotation-box roles, with
existing nested shape/asset diagnostics preserved. Add structural tests
that enumerate all 24 current public Theme roots and all resolved Scheme
targets rather than asserting a stale hard-coded number. An uncovered role
or untraceable consumer is a **design stop**, not a permissive fallback.

**Publication boundary:** 3A is test/design validation inside the atomic
I478-3 product release; do not push a strict validator by itself while
public resources fail to load.

## I478-3B — Atomic source migration and public evidence

**Owners:** only affected files among `examples/*/themes/*.yaml` (17 roots)
and `src/chrona/resources/presets/bundles/*/theme.yaml` (seven roots), plus
any source-mirrored resource and generated `examples/*/generated/` evidence.
Conformance's three Theme fixtures are a separate positive/negative test
set, not migration targets. Inspect concrete consumers before removing
`baseline`, `variance-behind.strokeWidth`, `annotation.strokeWidth` or any
other declaration. Preserve all consumed treatments; no compatibility alias
for dead bindings. Theme syntax stays on the live v0.11 schema, with v0.12
derived inheritance where already declared; stop for a design correction
before any syntax/version change.

**Atomic gate:** all 24 Theme roots and their valid contexts close; every
manifest-declared slide (28 at design) materializes from source and
reproduces in one `tools/regenerate_public_examples.py --check --jobs 4`
batch after regeneration. Compare generated Scene/SVG and provenance/source
hash diffs by cause, inspect rendered SVG/PNG as a batch, and ensure
unchanged/default-profile pixels do not silently lose a supported effect.
The local project `.venv` must also install the separately packaged
`packages/chrona-fonts-noto-cjk` provider for the ja-JP public slide; an
`E_MATERIALIZER_FONT` from an absent provider is environment setup, not a
Theme admission verdict. Run focused admission/closure/Scene tests locally
in `.venv`; run conformance
and the planned three-OS full pytest/wheel/smoke plus newest-Python public
checks in CI. Publish registry, validator, Theme migrations and generated
evidence **as one coherent product commit**; check remote main immediately
before push, and inspect the complete CI run afterward.

## I478-3C and I478-4 — Reviews and issue release

After I478-3B passes CI, publish a separate implementation review recording
exact migrated paths, declarations removed or preserved, CI run, focused
commands, generated-byte classes, actual images, and a literal three-row
status table. Then I478-4 rechecks the whole design, Specification
07/08/50/63/64, #391, #400/#449, inheritance, Draft/immutable closure,
Scene/CLI info, and adapter output. Publish the final acceptance review
separately, verify its remote commit/CI state, and close #478 only if all
three literal rows are met. The current prior review count of 21 slides
does not substitute for the manifest-derived release gate.

Before **each** publication: fetch `origin/main`, inspect ahead/behind,
staged/generated diff and conflict risk. No force push; stop on unexpected
remote updates. Avoid a redundant local full pytest; use focused local
checks and the CI matrix for full release evidence. A design gap discovered
in 3A/3B requires a published design correction, architecture re-review and
plan amendment before product code continues.
