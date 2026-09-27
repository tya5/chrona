# Architecture Review Amendment — Bundled Default Readability (#498)

**Status:** correction reviewed for the implementation-plan amendment; tint and final public-output acceptance remain open.
**Design correction:** [title and variance separation](../../design/issue-498-bundled-default-readability-design-correction-2026-09-27.md).
**Original review:** [#498 whole-architecture review](issue-498-bundled-default-readability-architecture-review-2026-09-27.md).
**Original design:** [#498 selected design](../../design/issue-498-bundled-default-readability-design-2026-09-27.md).
**Plan amendment:** [implementation-plan amendment](../../planning/active/issue-498-bundled-default-readability-implementation-plan-amendment-2026-09-27.md).
**Issue and owner decision:** [#498](https://github.com/tya5/chrona/issues/498), [owner comment](https://github.com/tya5/chrona/issues/498#issuecomment-5852117933).

## Review decision

Select title-only plot member names (`content: [title]`) and allow current Layout behavior to emit finish variance as separate semantic labels. This decision preserves navy member names, retains the established ahead, on-plan, and behind finish-variance treatments, and keeps the two facts distinct. Candidate A looked less crowded than Candidate B, where `+Nd` was appended to the navy name string. No new fallback, role, geometry, diagnostic, or adapter behavior is needed.

This decision is narrowly about composition of existing View and Layout contracts. It does not accept the row tint: the A/B render used the current Editorial Theme, whose `row-band.fill` is gray `surfaceRaised` and whose row-band opacity is `opacity.group-band` at `1`. The owner-required warm tint, opacity, and perceptibility remain implementation gates.

## Architecture and adjacent-design consistency

| Contract or adjacent work | Review finding after correction |
|---|---|
| Spec 06, View | `placement: both` retains the table title column and requests plot labels. `content: [title]` describes member-name content only. `finishDelta` is not silently folded into the title string. `rows: alternate` expresses row-decoration intent, not geometry. |
| Spec 07 and Spec 34/60, Theme and color bindings | The new Theme still owns a distinct warm row-band fill and dedicated opacity while preserving the Editorial type, palette, and axis bindings. The A/B renders do not prove this paint decision because both used the gray full-opacity Editorial row-band role. |
| Spec 08, Layout | Existing Layout code emits separate `variance:*` labels when a combined item has `finish_delta` and `finishDelta` is absent from member-label content. It uses its existing `above`, `below`, `end`, `start` candidate sequence and surface-content overflow policy. When `finishDelta` is present, it appends the fact to the member label and skips the separate variance request. The correction selects the former behavior without modifying Layout. |
| Spec 38, View identity and row ownership | Name placement remains bounded to each object's row and anchored at its bar start/end, or explicitly suppressed. Separate variance labels do not replace or alter the name disposition contract. No lane-packing or shared-obstacle work is introduced. |
| Spec 50, presentation pipeline | Layout completes label and band geometry; Scene carries member labels, variance labels, suppressions, and row bands; SVG serializes those results. Tests and acceptance must inspect both Scene and SVG. |
| Spec 62 and #429/#383 catalogue identity | The default remains a distinct resource selection. The named `editorial` catalogue and its identities remain untouched; no resource aliasing or Context mutation is introduced. |
| #425 Editorial reference | `13-gallery-editorial` remains no-row-ground and table-only. New default bands and plot names remain confined to the default-owned View/Theme. |
| #483 readable defaults | Candidate A matches the existing `default-draft` semantic split: title-only member names plus independently rendered variance labels. This precedent is supplemental; the new regression gate must still render the actual bundled default. |
| #488 row-local labels | Candidate A produced row-local labels at bar starts/ends and a suppression diagnostic for each of three non-visible names. This is feasibility evidence; the bundled-default test must directly prove those dispositions and ensure suppressed labels have no Scene/SVG text primitive. |
| #466/#467 | No dependency is identified. The candidate used published Layout behavior available at the selected baseline; it does not depend on unpublished lane-row or shared-obstacle work. Both issues were open at review time. |

## A/B evidence and acceptance limits

The correction records full commands, temporary artifact paths, and candidate definitions. Measured results are:

| Candidate/output | Rows | Bands reaching plot end | Rows guided by band edges | Visible member labels | Suppressed members | Separate variance labels | Geometry result |
|---|---:|---:|---:|---:|---:|---:|---|
| A, HALCYON-1 | 26 | 13 | 26 | 23 | 3 | 12 | All 23 visible names are row-local and at bar start/end. |
| B, HALCYON-1 | 26 | 13 | 26 | 23 | 3 | 0 | All 23 combined name/delta labels are row-local and at bar start/end. |
| A, initialized starter | 3 | 2 | 3 | 3 | 0 | 0 | All 3 visible names are row-local and at bar start/end. |
| B, initialized starter | 3 | 2 | 3 | 3 | 0 | 0 | All 3 combined labels are row-local and at bar start/end. |

Candidate A suppressions were `eps`, `detector`, and `avionics`; Candidate B suppressions were `structure`, `eps`, and `detector`. This confirms that adding delta text changes which names fit, another reason not to merge the facts. Scene and SVG member, variance, and band ID counts matched in every row. Candidate A showed twelve independent variance labels on HALCYON-1, with distinct ahead/on-plan/behind treatments; Candidate B had no separate variance labels and visually longer, more crowded navy strings.

These are temporary explicit-resource renders, not acceptance proof. They verify feasibility of current Layout behavior with these View declarations. They do not prove final package resolution, byte-identical mirrors, the default-selected render path, or the tint. The required starter-perceptibility check previously run in this worktree evaluated unchanged public artifacts and therefore does not accept a candidate Theme.

## Layer, compatibility, and normative review

The owner-facing behavior stays within declared layers: View selects names, fallback and alternation; Theme supplies the final row paint and existing text/variance bindings; Layout owns names, variance candidates, geometry and suppression; Scene records completed output; adapters serialize it. Product-code or schema work is not warranted by this evidence.

The only intended default compatibility change remains additional plot names, separate finish-variance labels, and alternating row grounds for consumers of the bundled default and `chrona init`. Explicit named Editorial output, its library entry, gallery slide 13, and immutable Contexts remain unchanged. No migration is needed.

No living specification or ADR update is required. Existing contracts already distinguish View label content from Layout-created variance labels and define layer ownership. The correction and amended tests make the selected composition explicit without changing normative semantics. Reopen architecture review if the final Theme requires a distinct typography role, if Layout fails the required direct assertions, or if the warm tint cannot satisfy both the perceptibility check and the visual relation to column ground.

## Remaining gates

1. Implement the title-only member View and separately verify the expected variance-label behavior through the actual bundled default.
2. Implement Scene and SVG assertions for all member-name dispositions, row coverage, and absence of hidden suppressed-name primitives; test the separate variance labels independently.
3. Tune the Editorial-derived row-band tint and opacity using actual HALCYON and initialized-starter images. Pass `starter-perceptibility`; inspect the band next to paper and column ground.
4. Confirm package/corpus byte identity, default-only View/Theme selection, and unchanged named Editorial resources and slide 13.
5. Commit final HALCYON and starter default render evidence; compare side by side with `13-gallery-editorial`, including palette, typography and axis.
6. Run public-materializer and three-OS CI release evidence. Complete an acceptance review row for each literal criterion; keep #498 open while any required evidence is missing.
