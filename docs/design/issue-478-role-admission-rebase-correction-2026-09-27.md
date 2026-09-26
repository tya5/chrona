# Design Correction — Current Role/Property Admission Boundary (#478)

**Axis-role amendment:** the [View-named typography rule](issue-478-axis-typography-role-admission-amendment-2026-09-27.md)
adds a bounded producer family for arbitrary axis-tier measurement roles; it
does not admit arbitrary Scene paint.

**Amends:** [declared-treatment design](issue-478-declared-treatment-visibility-design-2026-09-26.md).
**Plan:** [rebase design plan](../planning/active/issue-478-role-admission-rebase-design-plan-2026-09-27.md).
**Scope:** I478-3 admission, resource migration and evidence only. I478-1/2
information semantics and the three literal acceptance criteria do not change.

## Published baseline and migration census

At `eff9780e`, the repository contains **17** example Theme YAML roots under
`examples/*/themes/`, **seven** packaged preset Theme roots under
`src/chrona/resources/presets/bundles/*/theme.yaml`, and **28** slide targets
declared by `examples/*/manifest.yaml`. The previous design's 15 Themes and
21 slides are historical counts, not the I478-3 acceptance set. All 24 Theme
roots must pass effective closure with their declared resources. The three
`conformance/presentation/themes/` files include an intentionally invalid
undefined-token fixture; they remain positive/negative tests, not public
migration targets. A Theme root unused by a manifest is still in the admission
sweep; a manifest slide is still in the output sweep. The implementation plan
derives both sets from tracked paths/manifests at verification time and records
their observed counts, so later additions cannot be silently omitted.

## One admission authority, distinct consumer contracts

`color_scheme.resolve_theme` remains the common **effective Theme** boundary:
base/derived inheritance is completed before it, Scheme bindings are inserted
there, and both Draft and immutable closures call it. A finite role/property
projection of `scene/capabilities.py` decides applicability after Scheme
insertion and before returning the resolved Theme. It must validate **each
direct declaration** and **each Scheme target**, not merely the resulting map,
so provenance remains exact even when a target overwrites an inherited value.
The role/property relation is explicit data, tested against actual consumers;
it is not inferred from current YAML spelling or accepted on an unrestricted
prefix match. The only parameterized family is a declared producer/consumer
family (such as `group:<value>` for finite group colour encoding) with a
documented grammar and source; arbitrary unknown roles fail.

There are distinct consumer families:

- Layout typography/metric roles (`text`, `heading`, `axis`, `axisMonth`,
  `axisQuarter`, `groupHeader`, `legend`, annotation text, summary/metric and
  their selected variants) may carry only measured typography and the paint
  actually projected for their Text/Icon kinds. A role used by both Text and
  Icon cannot promise outer shadow/gradient until both projections serialize
  them, or an explicit kind-conditional contract is designed.
- Completed Rect/Symbol marks, Path/line relations, Text, Icon, canvas and
  decoration roles admit only the treatments their Scene primitive families
  and adapters carry. Geometry, contrast, background, marker, symbol and
  scale properties have their declared Layout/Scene/closure consumers; they
  are not inferred from a similarly named paint property. New #426 axis
  cells/tiers, #464 glyph variants, #466 group-header bands and annotation
  roles, and #465 image notes must be included in the inventory.
- `annotationContainer` is a **Layout geometry** property on the four
  annotation box roles: `annotation-callout-box`,
  `annotation-highlight-box`, `annotation-note-box`, and
  `annotation-arrow-box`. The composer calls the same token accessor for
  each. It is not a Scene paint effect. Its finite token
  value (`rectangle`, `balloon`, or `image`) is type/shape checked by Theme
  schema and `ThemeTokenView`; image catalog reference pinning and nine-slice
  content geometry remain with closure/Layout under #465. The image form's
  `fill` is a representative content-area colour used by contrast. Admission
  checks whether that role may bind the **top-level** property; it does not
  duplicate nested token parsing. Existing nested shape/type/asset errors
  retain their exact `/body/.../annotationContainer/...` pointers. A Scheme
  cannot insert an `annotationContainer` token because its target grammar is
  colour-only.

The diagnostic is `E_THEME_ROLE_PROPERTY_UNSUPPORTED` with a direct
`/body/roles/<role>/<property>` pointer or a Scheme
`/body/colorBindings/<role>.<property>` pointer. Derived Theme provenance must
point at the effective declaration or inherited source according to the
existing closure pointer contract; it must never collapse to `/`. Syntax or
token-value errors retain their existing codes rather than being relabeled as
applicability errors. The selected visual profile is **not** consulted at
load time. Thus `planned` shadow remains a valid rich-profile capability,
while a text-only `strokeWidth` remains an error.

## Atomic migration, release and failure behavior

The validator and every affected example/bundle Theme correction are one
publication unit. Before deleting an apparent orphan such as `baseline` or
`variance-behind.strokeWidth`, trace the actual Layout/Scene/adapter consumer
and Scheme target. Keep consumed declarations even if no current manifest
slide exercises them. Do not add compatibility aliases for dead behavior.
No public Theme or context may become temporarily unmaterializable. Record
the exact migrated paths, generated provenance/source-hash changes, Scene
diagnostics and rendered SVG/PNG changes. Run the 28 current public slides as
one batch, and use the manifest-derived count as the actual release gate.

If the census reveals a role with no selected consumer rule, or inherited
pointer provenance cannot be preserved, stop I478-3 and publish another
design correction. Do not solve either gap by widening a family or by an
adapter conditional.
