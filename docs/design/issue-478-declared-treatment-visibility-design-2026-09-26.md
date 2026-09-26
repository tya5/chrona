# Design — Declared Treatment Visibility (#478)

**Status:** accepted for implementation planning in the [whole-architecture review](../reviews/current/issue-478-declared-treatment-visibility-architecture-review-2026-09-26.md). **Predecessors:** [design plan](../planning/active/issue-478-declared-treatment-visibility-design-plan-2026-09-26.md), [reproduction](../research/presentation/issue-478-declared-treatment-visibility-reproduction-2026-09-26.md). **Related:** Specifications 07, 08, 50, 63 and 64; #400/#449's no-silent-loss rule. This issue does not make presets select a visual profile (#479).

## Use cases and accepted distinctions

1. An author selects the default baseline profile with `elevated-light`. Its group-band gradient and shadow are optional, so rendering succeeds with the declared flat fill, but the output names each omitted treatment and a same-target profile that paints it. It never silently upgrades the profile.
2. A Theme declares a property that no consumer of its role can carry (for example a stroke width on a text-only role). Resource closure fails before Layout, Scene, or an adapter starts. A valid property omitted only by the selected profile is **not** rejected at Theme load. In particular `planned` shadows are valid for its Rect/Symbol marks under a rich profile; the issue's example is a profile omission, not a mark-role incapability.
3. Layout suppresses some bar-end labels by the author's declared `overflow: suppress` fallback. It keeps each existing placement-ID diagnostic and adds a single count-bearing info fact for the completed surface. Scene does not create drawable text for those placements. The table still retains the names.

## Ownership and data flow

```text
Theme + Scheme -> resolved Theme -> role/property admission
View + Layout -> completed placements + suppression facts
placements + Theme + selected target profile -> Scene primitives + paint dispositions
Scene + dispositions -> inspection diagnostics + CLI info projection
Scene primitives -> SVG/PNG/other adapters (no Theme or diagnostic policy)
```

Theme closure is the common load-time boundary for direct, inherited, packaged, draft and immutable resources. It validates after base inheritance and Scheme color-binding insertion, and before returning a resolved Theme. The existing presentation Scene capability ceiling (#391) is extended with a closed `RolePropertyContract` projection rather than creating a second capability authority. It records each authorable role's permitted properties and consumers, including paint, typography, geometry, marker/symbol, contrast and background policy roles; a role is not registered merely because a Theme currently spells it. Parameterized role families are admitted only with an explicit producer and consumer rule (for example a category/scale role), never by an unrestricted string wildcard. Every Theme `roles` key and every `colorBindings` target is checked. Unknown roles and a known role's unsupported property fail with `E_THEME_ROLE_PROPERTY_UNSUPPORTED` at the exact `/body/roles/<role>/<property>` or `/body/colorBindings/<target>` pointer. Missing/wrong token types retain their existing diagnostics. The validator has no selected View, geometry, profile or target and cannot make a paint disposition.

The registry distinguishes an authoring role from the Scene visual role: `heading`, `axis`, `summary` and similar roles may contribute only Layout typography while their text is painted under `text`; `asOf` is a canonical authoring role while `as-of` is a Scene role; `relationSourceTerminal` and `relationTargetTerminal` provide marker geometry, not painted Scene roles. Each role/property descriptor must name its consuming stage and, for paint, the primitive family/families that can serialize it. The same registry must be exercised by a structural test covering all explicit Scheme/Theme declarations and all Scene role/kind pairs in public materializers. A declaration may be legal but unused in one View; that is not an error. A declaration with no capable consumer in any admitted surface is an error. A role shared by multiple emitted kinds may admit a property only when those kinds carry it or an explicit kind-conditional rule is documented and tested. In particular the Icon adapter currently does not serialize outer shadow/gradient paint, so shared `text` must not claim those treatments as portable for Icon until the projection and adapter support them.

Role-family paint rules are based on actual completed output, not on a role's suggestive name:

| Consumer | Portable properties | Rejected examples |
| --- | --- | --- |
| Rect/Symbol | fill, stroke, strokeWidth, dash, opacity, pattern where declared, gradient, shadow, stroke finish | text measurement tokens on a mark-only role |
| Path | stroke, strokeWidth, dash, opacity, shadow, stroke finish; declared marker endpoint geometry where applicable | fill gradient, text measurement, background placement |
| Text | fill, opacity, gradient, shadow plus an independently mapped typography role | strokeWidth/dash/stroke finish, mark geometry |
| Icon | its declared icon sizing/asset treatment and serializable icon paint only | outer shadow/gradient until Icon projection and adapters serialize them |
| Canvas | fill, opacity, gradient, shadow | strokeWidth/dash; no canvas stroke is serialized |

Conditional policy properties (`backgroundTreatment`, `backgroundPaintOrder`, `contrastTreatment`, mark dimensions/order, marker/symbol, and icon metrics) are allowed only on their owning role family. The registry is a finite public contract, not a hard-coded exception for the reproduction. Unsupported declarations in shipped Themes, including orphan `baseline` paint and text-only `variance-behind.strokeWidth`, are migrated in the same release as the validator. No public materializable context may be made transiently unmaterializable by publishing the validator separately from resource migration. If a declaration is actually consumed, preserve it; do not delete it based solely on a name search.

## Optional treatment disposition

The internal information channel is a closed immutable union:
`PresentationInfo = PaintOmission | SuppressedPlotLabels`. Each member owns its
fields and one canonical Scene-string/CLI projection. Layout may create only
`SuppressedPlotLabels`; Scene may create only `PaintOmission` and pass Layout's
member through. `SurfacePlacement`, `SceneSurface`, and `RenderedReview` carry
typed values in memory; `InspectionScene.diagnostics` retains canonical strings
under the existing v0.6 schema. The CLI reads typed values from the completed
render result, never reparses inspection strings. This is an information
channel, separate from validation errors, fit warnings and perceptibility
warnings. Its ordering is Layout facts first, then Scene paint facts.

Scene paint resolution returns a completed paint **and** zero or more typed `PaintOmission` facts. One fact contains the authoring role, treatment (`linear-gradient`, `drop-shadow`, or `stroke-finish`), exact Theme property pointer, selected profile, target kind, and the first same-target profile in the ordered profile registry that supports the treatment. The registry order chooses `v0.6-svg` or `v0.6-png` before the later icon profiles. If the target has no richer profile, the suggestion is absent, never fabricated. Required unsupported treatments keep `E_VISUAL_CAPABILITY_UNSUPPORTED` and abort before serialization. Optional omission retains the complete flat fallback specified by Specification 63 and never changes geometry, source identity, or paint order.

Scene deduplicates omissions by `(role, treatment, selected profile, target kind)`, in first primitive encounter order, including canvas. It does not warn once for every group band. The stable public inspection string is `I_VISUAL_TREATMENT_OMITTED:role=<role>;treatment=<treatment>;profile=<selected>;paintable=<same-target-profile-or-none>`; authoring role IDs and profile IDs cannot contain `;` or `=`, and fields always occur in this order. The same typed fact is projected to a CLI JSON line on stderr with `severity: info`, `code`, `role`, `treatment`, `sourceRef`, `visualProfile` and `paintableProfile`. A future structured Scene diagnostic schema may replace this encoding, but no adapter parses or creates it. If the selected target has no richer profile, `paintableProfile` is null and the Scene string says `paintable=none`; the CLI message states that target cannot paint the treatment. This is information, not a layout warning and not a failure.

## Suppressed-label count

Layout counts completed `TextPlacement` values with `semantic_id == "memberLabel"` and `overflow == "suppressed"` after all label fallback decisions. It emits one typed `SuppressedPlotLabels` fact only when the count is positive. Its source is the same completed placement set that emits per-ID `W_LAYOUT_LABEL_SUPPRESSED`; the count must equal that set's cardinality. Scene passes the fact through and serializes `I_LAYOUT_PLOT_LABELS_SUPPRESSED:surface=<surface-id>;count=<positive-integer>`; CLI projects it as an `info` line with `count` and `surfaceId`. The existing `W_LAYOUT_LABEL_SUPPRESSED:<placement-id>` facts remain for exact inspection. No new View field or visible marker is introduced in this issue: the acceptance explicitly permits an info count, and a marker would require new geometry/legend/contrast policy. The count is per completed surface, never inferred by the adapter or summed from visible Scene text.

## Migration, failure, and verification

- The Theme schema's syntactic property set remains closed, but semantic role/property validation becomes stricter. Invalid previously accepted declarations fail at the earliest common Theme closure with a stable exact source pointer. No compatibility alias retains a property whose treatment is silently absent. Resource declarations removed or corrected as part of this change must be listed in the implementation review.
- The Scene v0.6 `diagnostics` string array remains valid. New info IDs are deterministic, ordered and explicitly documented; Scene primitive and adapter schemas do not change. Existing per-ID suppression warnings remain stable.
- All bundled Themes and public examples must load; every public materializer must reproduce from its declared source. The planned byte changes are new info diagnostics and CLI stderr; deleting dead Theme declarations can also change source hashes/provenance. Public SVG pixels should remain unchanged for default-profile renders except where removing a genuinely ineffective declaration alters no output. Rich-profile treatment must remain visibly painted.
- Focused tests cover role/property validation for direct and Scheme-introduced bindings, unknown roles, typography-only/Path/Text/Icon/Rect/canvas roles, inherited Themes, baseline/rich SVG and PNG, same-target profile suggestion, deterministic deduplication, CLI projection, Layout count versus individual IDs, and no suppressed primitive. A complete public-resource admission sweep and all 21 public materializers are required; representative generated SVG/PNG images are compared as a batch. Three-OS CI full pytest/conformance/wheel and newest-Python public materializers are the release gate.

## Non-goals and adjacent design

This design does not choose a visual profile in a preset (#479), invent arbitrary SVG/image effects (Specifications 63/64), change labels' collision policy (Specification 50), or make a suppressed label drawable. It does not interpret a Theme in an adapter. If role-consumer inventory reveals a missing public capability or a conflicting Theme ownership rule, implementation pauses for a published design correction and whole-architecture re-review rather than adding an exception in code.
