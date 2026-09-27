# Architecture Review — Bundled Default Readability (#498)

**Status:** selected design reviewed; implementation remains gated on the evidence and tuning questions below.
**Design:** [#498 selected design](../../design/issue-498-bundled-default-readability-design-2026-09-27.md).
**Plan:** [published design plan](../../planning/active/issue-498-bundled-default-readability-design-plan-2026-09-27.md).
**Issue/owner decision:** [#498](https://github.com/tya5/chrona/issues/498), [decision comment](https://github.com/tya5/chrona/issues/498#issuecomment-5852117933).

## Decision and scope

The selected topology is structurally sound: a default-owned Editorial-derived View and Theme, while reusing the exact Editorial Scheme, Layout, and Detail Profile. `default.yaml` alone selects the two new resources; no Scheme copy is needed because the row tint reuses the existing warm `category:default` value. The named `editorial` catalogue bundle and `13-gallery-editorial` stay on their existing resources and are not mutated. This preserves the catalogue/reference identity while resolving the owner-selected bundled-default behavior.

The intended slice is C-depth YAML/resource changes plus a regression test correction. It does not modify schemas, renderer code, CLI resolution, Layout behavior, the library catalogue, or gallery source. No normative specification change appears necessary: this composes existing View intent, Theme paint tokens, Layout placement, and preset identity contracts. If implementation discovers that row-local fallback, palette reuse, or output identity cannot be achieved with those contracts, pause and publish a design amendment before changing code.

## Cross-architecture consistency

| Contract or adjacent work | Review finding |
|---|---|
| Spec 06, View | `placement: both`, title plot content, end/start/suppress fallback, and alternating rows are declarative presentation intent. An alternate band on every other row guides both painted and neighboring unpainted rows as a continuous row pattern; the acceptance check must verify the whole pattern rather than count one primitive per row. No literal geometry or color is placed in View. |
| Spec 07 and Spec 34/60, Theme and color bindings | Warm row-band fill and opacity belong in Theme. Existing `category:default` is a valid warm slot and is reused; Scheme remains unchanged. All non-row-band type/axis/palette bindings remain Editorial-derived. |
| Spec 08, Layout | Layout continues to measure and place complete labels and row bounds. The selected design adds no geometry algorithm or adapter responsibility. |
| Spec 38, View identity and row ownership | View selection does not redefine Layout row geometry or imply lane/collision changes. Row-alternate intent feeds the current row-band mechanism. |
| Spec 50, presentation pipeline | The design respects View → Theme → Layout → Scene → adapter boundaries; serialized artifacts must prove the visible result. |
| Spec 62 and #429/#383 preset/catalogue architecture | Default resource identity is separated from the named catalogue identity through explicit resource references, not by mutating the Editorial entry. Package/corpus mirrors need identity/byte checks. |
| #425 Editorial reference and slide 13 | Editorial reference remains table-ground/no-row-ground. Readable default is a distinct variant, so reference fidelity and first-run readability are not conflated. |
| #483/#488 | The default regression test must use the actual bundled default. #488's end/start/suppression behavior is precedent, not acceptance proof until exercised through this new View and visible SVG. |

The change intentionally affects output only for consumers who select the bundled default (including `chrona init` starter). Existing explicit named Editorial selection remains stable. Reusing Scheme/Layout/Detail also avoids unnecessary identity forks and keeps axis/palette behavior tied to the reference system.

## Evidence and limitations

Baseline and temporary-resource feasibility renders at `90306256` show the bare default missing plot row guides and member labels in both HALCYON-1 and an initialized starter. A temporary candidate produced 13 alternate row-band primitives, 23 visible labels and 3 suppressions for 26 HALCYON rows; the starter produced 2 bands and 3 labels for 3 rows. Candidate SVG mirrored Scene counts. The candidate Scene perceptibility evaluator had zero errors. Raster inspection showed legible navy labels and extremely faint warm bands at the trial opacity `0.12`.

These counts came from a read-only temporary candidate and a runtime-only resource-root harness workaround for an editable `examples` namespace collision. They are feasibility evidence, not checked-in artifact acceptance. The official `starter-perceptibility` script did not complete in that environment. Also, the inspected output confirms counts and visual appearance but not an independently automated proof that every visible label lies at its own bar's end/start and within its own row. These are explicit implementation gates, along with a clean-environment rerun and side-by-side comparison with `13-gallery-editorial`.

## Required implementation gates / unresolved review points

1. **Tint tuning:** opacity `0.12` is only a prototype. In the intended environment run the actual `starter-perceptibility` check, inspect starter and HALCYON images alongside `13-gallery-editorial`, and establish the band is just perceptible and well below the column ground. If it is too heavy, do not add a hairline schema here; obtain approval for a B-depth successor.
2. **Geometry proof:** structurally test full row-guide coverage and each visible label's row membership and end/start placement. For every non-visible selected name, assert a corresponding suppression disposition/diagnostic and no hidden text primitive. Inspect actual SVG as well as Scene.
3. **Small type contract:** current member-label semantic mapping reuses Editorial body `text` styling (Noto Sans regular, 14 px navy), not a separate smaller label role. Review visual fit against the owner's “small navy type” phrase. Any requirement for an independently tunable label size is a scope/design question, not permission for a local special case.
4. **Identity/mirrors:** verify package resource and HALCYON corpus mirrors byte-identical; default selects the new View/Theme; catalogue Editorial and gallery slide 13 remain unchanged and reference-faithful.
5. **#466/#467 boundary:** the selected issue slice relies on current row-local #488 behavior and requires no lane-row/shared-obstacle work. Recheck current published merge/status before implementation; do not depend on an in-progress branch. If the selected test cases expose a genuine dependency, amend the plan/design first.

Before acceptance, implement focused bare-default and initialized-starter tests, regenerate and commit both artifact sets, compare them side by side with slide 13, run public materializers and the planned CI matrix, and provide a row for each of the four literal issue criteria. A passing unit/Scene test alone is insufficient.

## Publication sequence

1. Publish this selected design and review as separate documentation units.
2. Publish an implementation plan with exact owned resource/test/artifact files and gates above.
3. Implement only the approved resource and test slice; inspect changed bytes, Scene, SVG, and rendered images.
4. Publish acceptance evidence/review; keep #498 open until every literal criterion and release gate is directly evidenced.

No implementation is approved by this review document alone; open evidence gates remain binding.
