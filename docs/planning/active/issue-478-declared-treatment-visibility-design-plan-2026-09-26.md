# Design Plan — Declared Treatment Visibility (#478)

**Public base:** `8153f729` on `main` (Issue #476 implementation; its CI is pending at plan creation). **Source of truth:** [Issue #478](https://github.com/tya5/chrona/issues/478), Specifications 08, 50 and 63, the current Theme v0.11/Scene v0.6 contracts, and the #400/#449 no-silent-loss policy. **Related:** #470 preset tuning; #479 owns declarative preset visual-profile choice and is not part of this issue.

## Published baseline, inference, and unverified facts

- Published: `elevated-light` declares a `decorative-optional` group-band gradient and shadow. `scene/paint.py` permits optional omission under the baseline profile without recording the dropped role/property or the profile that could paint it. The resulting Scene contains completed flat paint, but no omission fact.
- Published: Theme v0.11 permits gradient/shadow/stroke-finish bindings on generic semantic roles. `color_scheme.resolve_theme` copies role bindings into the resolved Theme. Scene paint resolution is invoked for emitted primitives, not every declared Theme role; a binding on an unused or non-paintable role can therefore escape evaluation.
- Published: Layout already records individual `W_LAYOUT_LABEL_SUPPRESSED:<placement-id>` facts in Scene diagnostics. This is partial visibility, not the requested aggregate info count or a per-row visible marker. The #470 acceptance explicitly permits those diagnostics.
- Inferred, **not yet proved**: the reported `planned` shadow is omitted because the render uses the baseline profile, rather than because marks categorically cannot carry shadows. The SVG adapter applies a completed shadow to Rect/Symbol/Path paint; a rich-profile reproduction must separate profile omission from an unsupported role/primitive.
- Unverified: the exact CLI/Scene diagnostic projection path, diagnostic severity vocabulary, role-to-primitive capability registry, inheritance handling, and affected public materializer bytes. These must be established before selecting a design.

## Literal issue acceptance ledger

1. “Rendering `elevated-light` under the default profile emits a diagnostic that names the dropped treatment and the profile that would paint it.”
2. “A Theme property on a role that cannot carry it is diagnosed at load time.”
3. “Suppressed plot labels are counted in an info diagnostic, or the View can ask for a visible marker on rows whose label was suppressed.”

## Use cases and decisions to close

1. A user copies `elevated-light`, renders with the default visual profile, and receives a stable, actionable omission fact without a profile upgrade or a false layout failure. Decide diagnostic identity, severity, role/property path, supported-profile suggestion, deduplication, and whether it is emitted once per declaration, surface, or primitive.
2. A Theme author binds a treatment to a role that will never serialize it. Define a closed role/property capability inventory and the earliest common load-time boundary for direct, inherited, packaged, draft, and immutable Themes. Distinguish an unsupported role/property from a supported role whose effect is merely omitted by the selected profile, and from an unused-but-valid role.
3. A reader sees a plot label suppressed by a declared View policy. Choose the issue's aggregate info diagnostic or a View-selected visible marker. Preserve individual placement evidence and the invariant that a suppressed TextPlacement never becomes a Scene text primitive. Define count scope, stable ordering, relation to CLI output, and how table labels remain available.

## Responsibility and architecture review questions

- Theme/Color Scheme own declaration and value typing. Which shared registry can validate role/property applicability without knowing the selected View, Layout coordinates, target adapter, or rendering profile? Does schema validation alone suffice, or is a semantic role check required after inheritance and Scheme resolution?
- Scene owns completed paint and target-profile disposition. How will omission facts be carried into `InspectionScene.diagnostics` without teaching the SVG/PNG adapters Theme semantics or making Scene choose geometry?
- Layout owns label-fit and suppression facts. Can it emit one aggregate diagnostic with a count while keeping the existing per-placement facts for inspection, or is a separate structured diagnostic required? How do #400/#449's visible-fallback rules and Specification 50's non-drawable suppressed placement invariant remain intact?
- Check Specifications 06/08/50/63/64, the Theme and Scene schemas, diagnostic inventory, CLI behavior, preset catalogue, and relevant ADRs for ownership or migration conflicts. Record any intentional incompatibility; do not preserve silent behavior for compatibility.

## Ordered design slices and acceptance evidence

1. **D478-1 — Reproduce and classify:** render copied `elevated-light` under baseline and rich SVG/PNG profiles, including a mark shadow; inspect exact resolved Theme, Scene paint, diagnostics, and adapter output. Inventory a genuinely non-paintable role/property example and current label suppression counts. Publish findings as design evidence, not speculative code.
2. **D478-2 — Complete contract:** choose omission diagnostic and profile suggestion, closed role/property admission, and suppression count policy. Specify identity/path/severity, failure behavior, layer connections, inheritance and package implications, generated-output migration, and exact tests. Update living specifications or an ADR where normative ownership/semantics change; publish the design.
3. **D478-3 — Whole-architecture review:** compare the contract with Theme/Scheme, View, Layout, Scene, adapters, CLI, schemas, portability and #400/#449. Resolve every design gap and publish a separate review.
4. **D478-4 — Implementation plan:** split the approved design into independently testable/publishable slices: diagnostic closure, load-time role validation, suppression aggregation, and public evidence. For each name code/schema/resource owners, focused tests, public materializers, rendered SVG/PNG checks, CI gates, and acceptance rows. Publish before product code.

Implementation must then follow the approved plan. Each slice receives focused tests; issue acceptance needs all 21 public materializers as one batch, relevant before/after images, the CI three-OS/full/conformance/wheel/newest-Python gate, and a separate acceptance review with a row for each literal criterion. Publish serially after checking remote `main`; close #478 only when all three rows have direct public evidence.
