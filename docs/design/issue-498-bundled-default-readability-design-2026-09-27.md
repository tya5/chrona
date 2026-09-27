# Bundled Default Readability — Selected Design (#498)

**Status:** selected design for architecture review; no implementation is authorized by this document.
**Issue:** [#498](https://github.com/tya5/chrona/issues/498) and [owner decision](https://github.com/tya5/chrona/issues/498#issuecomment-5852117933).
**Baseline:** design plan published at `add15e4d486562c9f5721f8bb5de4b46441660da`; product behavior audited against its predecessor `90306256219a1888fb674bf8677d28739eca244d`.
**Plan:** [design plan](../planning/active/issue-498-bundled-default-readability-design-plan-2026-09-27.md).
**Review:** [whole-architecture review](../reviews/current/issue-498-bundled-default-readability-architecture-review-2026-09-27.md).

## Decision

Keep the Editorial visual language as the bundled default, but give that default its own readable View and Theme resources. The named `editorial` catalogue preset and `13-gallery-editorial` remain reference-faithful and unchanged. The default View places member names in both table and plot, requests end placement with start then suppress fallback, and alternates row grounds. Reuse the existing Editorial Scheme, Layout, and Detail Profile. Do not introduce a hairline rule or schema change in this C-depth slice.

The exact resource topology is:

| Preset role | View | Theme | Scheme | Layout | Detail |
|---|---|---|---|---|---|
| Bundled default | New `editorial-readable-default` | New `editorial-readable-default` | Existing `editorial` | Existing `editorial` | Existing `editorial-detail` |
| Named catalogue Editorial | Existing `editorial` | Existing `editorial` | Existing `editorial` | Existing `editorial` | Existing `editorial-detail` |

Add package resources at `src/chrona/resources/presets/bundles/editorial-readable-default/{view.yaml,theme.yaml}` and byte-identical corpus mirrors at `examples/halcyon-1/views/editorial-readable-default.yaml` and `examples/halcyon-1/themes/editorial-readable-default.yaml`. Update only the bundled `src/chrona/resources/presets/default.yaml` selection to reference those resources while retaining its existing Scheme/Layout/Detail references and preset identity. Do not copy or edit the Editorial Scheme: its `category:default` warm color is the tint source. Do not alter the Editorial bundle, `library.yaml`, or slide 13.

## Behavior and ownership

The default View declares `labels.placement: both`, title-only plot label content, `side: end`, `fallback: [end, start, suppress]`, and `backgroundDecoration.rows: alternate`. Table name columns stay as they are; plot labels add names at bars' ends, and only candidates rejected by Layout are suppressed. Alternation paints every other row; the unpainted rows remain visually delimited by the adjacent tinted rows. The literal “every bar a row guide” criterion is therefore assessed per row as a continuous alternating row-ground pattern, not as one Rect primitive per row. Existing #488 behavior owns per-object row bounds, fitting, candidate placement, and suppression facts. The View expresses intent; it does not position text or draw row guides.

The default Theme is an Editorial-derived variant. It preserves all existing text, axis, category, paper, and column-role bindings except the row-band presentation: bind the row-band fill to the existing `category:default` warm palette slot and expose row-band opacity as a dedicated Theme token. A temporary feasibility candidate used opacity `0.12` and produced fill `#EFE7DE` at that opacity. Treat this as a starting value only: final tuning is unresolved until the implementation acceptance batch is inspected side by side at useful scale and the repository `starter-perceptibility` gate passes. Do not claim the tint is accepted from the prototype alone.

The current semantic role registry maps member labels to the existing `text` role. In this candidate that means Noto Sans regular, 14 px, navy `#293E56`, the Editorial body treatment. No separate smaller member-label role exists in the present Theme contract. The selected C-depth design reuses that role; implementation review must judge legibility and fit. If “small navy type” requires a distinct size, return to design for a scoped contract change rather than adding a hidden special case.

`View` owns row alternation intent, `Theme` owns tint/color tokens, `Layout` owns completed row and label geometry, `Scene` carries completed primitives and paint relationships, and SVG/other adapters serialize Scene. This change is resource selection and test coverage, not a change in CLI default resolution, layout algorithms, or Scene semantics.

## Baseline and feasibility evidence

Read-only renders were made against the baseline in an isolated worktree. The local editable install resolved the `examples` namespace as a multiplexed path, so the baseline CLI harness supplied a runtime-only `default_preset_root` pointing to the current worktree's HALCYON corpus. No repository source was changed. The temporary candidate was passed as an explicit resource path. This is a harness caveat; rerun with the project virtual environment/official tooling before treating counts as release evidence.

| Render | Rows | Row-band guides | Visible plot member labels | Suppressed labels |
|---|---:|---:|---:|---:|
| Bare bundled default, HALCYON-1 | 26 | 0 | 0 | 0 |
| Bare initialized starter | 3 | 0 | 0 | 0 |
| Temporary candidate, HALCYON-1 | 26 | 13 alternate bands | 23 | 3 |
| Temporary candidate, starter | 3 | 2 alternate bands | 3 | 0 |

The candidate HALCYON Scene and SVG each contain 13 row-band rectangles and 23 plot member-label text primitives; three names are suppressed and the existing aggregate suppression fact is present. The starter Scene/SVG contain two bands and three labels. Candidate labels were navy and visually legible in the inspected HALCYON raster. The warm bands were visible but extremely faint; exact opacity and perceptibility remain an implementation gate. The serialized Scene evaluator reported zero errors for the candidate. This is not a successful run of the official `starter-perceptibility` script; that script could not run cleanly under the editable namespace-path environment and must be rerun in the intended project environment.

The temporary candidate retained Editorial Scheme, Layout, Detail, and all non-row-band Theme bindings. It confirms current YAML grammar can express the proposed View and Theme without a schema change. It does not establish final visual acceptance or prove every placement geometrically: implementation tests must map each visible label's Scene bounds to its own row, establish that the label is at bar end or start, and account for every suppressed label. Rendered SVG and side-by-side images remain required evidence.

## Compatibility, migration, diagnostics

Existing users selecting the bundled default will intentionally receive plot labels and alternate row grounds. Users selecting named `editorial` continue to receive the reference-faithful table-only/no-row-ground presentation. The package and corpus copies of the two new resources must be byte-identical, and the default manifest must resolve them through the existing preset identity/resource mechanism. No migration of project files is needed; `chrona init` should inherit the new bundled selection. Explicit preset/resource selections remain unaffected.

The change must preserve Layout's suppression diagnostics and avoid turning suppressed labels into hidden Scene text. It must preserve the current palette, typography system, and axis behavior through reuse of Editorial Theme bindings and Scheme. The regenerated HALCYON-1 and starter default artifacts are committed as evidence and compared with `13-gallery-editorial` in the acceptance review.

## Acceptance and implementation gates

All four literal criteria remain verbatim in the [published plan](../planning/active/issue-498-bundled-default-readability-design-plan-2026-09-27.md). In particular, implementation must verify bare HALCYON-1 rendering, `chrona init` starter rendering without presentation flags, per-row guide coverage, end/start-or-suppressed label disposition, and the required side-by-side artifacts. Focused tests must exercise the actual bundled default rather than only the pinned `default-draft` resources. Run `starter-perceptibility` in the intended environment; inspect Scene and actual SVG; compare generated images with `13-gallery-editorial`; record exact artifact diffs and CI/public-materializer evidence.

Do not add a hairline row-rule enum/property to View v0.26. If alternate bands are demonstrably too heavy after proper visual/perceptibility review, document a B-depth successor and obtain approval before broadening scope. If current Layout cannot satisfy row-local fallback/suppression, pause and design the missing behavior before implementation.

## Related records

- [#483 readable-defaults design](issue-483-readable-defaults-design-2026-09-26.md) and [acceptance review](../reviews/current/issue-483-readable-defaults-acceptance-review-2026-09-26.md).
- [#488 row-band label design](issue-488-member-label-row-band-design-2026-09-27.md) and [acceptance review](../reviews/current/issue-488-member-label-row-band-acceptance-review-2026-09-27.md).
- [#429/#383 preset catalogue design](issue-429-383-preset-catalogue-design-2026-09-27.md), [#425 Editorial reference](https://github.com/tya5/chrona/issues/425).
- [#466 shared-obstacle prerequisite](../planning/active/issue-466-shared-obstacle-prerequisite-implementation-plan-2026-09-26.md) and [#467 lane-row plan](../planning/active/issue-467-collision-aware-lane-rows-implementation-plan-2026-09-26.md).
