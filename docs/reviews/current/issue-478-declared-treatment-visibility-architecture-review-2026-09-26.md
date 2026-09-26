# Architecture Review — Declared Treatment Visibility (#478)

**Decision:** design approved for implementation planning, subject to the atomic resource migration and structural coverage gates below. **Reviewed design:** [#478 contract](../../design/issue-478-declared-treatment-visibility-design-2026-09-26.md). **Evidence:** [reproduction](../../research/presentation/issue-478-declared-treatment-visibility-reproduction-2026-09-26.md). This is a design review, not issue acceptance.

## Whole-system consistency

| Boundary | Existing authority checked | Result |
| --- | --- | --- |
| View / Project | Specifications 06 and 08; #470 and #479 | No new project field or View syntax. Preset-selected profile remains #479; no automatic profile upgrade. |
| Theme / Scheme / inheritance | Specification 07, Theme v0.11 schema, ADR-0006/0023, #378 effective Theme resolution, `color_scheme.resolve_theme` | Admission is after effective v0.11 inheritance and Scheme binding insertion, before either Draft or immutable render closure returns. The validator checks both non-color `roles` and Scheme-introduced color bindings. No adapter sees authoring resources. |
| Capability ceiling | #391 design and `scene/capabilities.py`; Specification 63 and #64 | Role/property applicability extends the one Scene-owned capability authority. It is distinct from target-profile support. A `planned` shadow is valid, but baseline optional omission is reported. Exact same-target v0.6 profile suggestion comes from profile registry, not an adapter. |
| Layout | Specification 50 and current `TextPlacement`/`SurfacePlacement` | Layout alone counts completed suppressed `memberLabel` decisions. Scene projects facts and does not invent a marker or make a suppressed placement drawable. Existing per-placement diagnostic remains. |
| Scene / adapter | Specification 08, Scene v0.6 schema, `scene/v05_builder.py`, SVG Icon/Text/Path branches | Completed paint and typed omission disposition are Scene-owned. Public Scene diagnostics remain strings; internal information is typed. Adapters only serialize completed primitives. In particular Text and Icon sharing the `text` visual role cannot justify silently accepting an effect that Icon cannot serialize. |
| CLI / diagnostics | #400/#449, #450 diagnostic aggregation design, `usecases/render_review.py`, `app/cli.py` | New facts are non-fatal `info`, separate from validation aggregation, fit warnings and perceptibility warnings. CLI projects typed completed facts and must not try to infer them from pixels or reparse Scene strings. |
| Public resources | 15 example/bundle Theme files; 21 Scene materializers | Existing dead declarations need a same-slice migration. A green load alone is not proof: admission tests must cover every declaration, and batch output comparison must prove no unintended visual regression. |

## Reviewed ambiguities and resolutions

1. The issue's planned-mark shadow example is not an intrinsically unsupported role. A rich SVG render paints it; treating all mark shadows as invalid would violate Specification 63 and the #391 ceiling. Profile omission is reported instead.
2. `W_LAYOUT_LABEL_SUPPRESSED` already exists per placement, but CLI does not surface Scene diagnostics. One aggregate info fact meets the literal acceptance without inventing new geometry or pretending suppressed text is visible.
3. The Theme schema validates field spelling, not applicability to a role. A post-inheritance/post-Scheme semantic gate is required. It must reject unknown role/property pairs by capability contract, not infer validity from current YAML usage.
4. The Scene diagnostic schema accepts strings and has no structured severity field. A typed in-memory information channel with stable string and CLI projections preserves v0.6 compatibility without making the CLI parse ad hoc strings.
5. Profile suggestions must be target-specific. The first v0.6 SVG/PNG rich profile paints gradient/shadow; the newer v0.7 icon profiles are not needed for those treatments. A baseline PDF/Typst/TikZ render has no supported same-target rich suggestion.

## Risks and acceptance gates for planning

- **Role inventory risk:** typography-only roles, alias `asOf` versus Scene `as-of`, category/scale roles, Icon/Text sharing, and mark geometry role `scenario` cannot be classified by string similarity. The implementation registry must name each producer/consumer, and structural tests must compare it with code and all public declarations. Any uncovered role is a design gap requiring correction before code continues.
- **Migration risk:** `baseline`, `variance-behind.strokeWidth`, `annotation.strokeWidth`, and other apparent no-op declarations need consumer-by-consumer verification. Remove only confirmed dead properties, and publish their source changes atomically with strict validation; all public contexts must remain materializable.
- **Evidence risk:** default-profile SVG may have no pixel diff even after a successful fix; Scene and CLI info output must be checked directly. Rich-profile marks and group bands need actual SVG/PNG inspection so Scene-only evidence cannot mask an adapter loss.
- **Identity risk:** changing Theme YAML changes content identities and generated Scene provenance. Regenerate all public materializers as one batch and inspect every changed byte class, not merely test pass/fail.

No unresolved user choice remains. The implementation plan must split typed information transport, admission plus resource migration, and public evidence into reviewable slices without exposing an intermediate state that breaks shipped contexts. Discovery of a new semantic consumer or an effect unsupported by an emitted kind requires a published design correction and another whole-architecture review before its implementation.
