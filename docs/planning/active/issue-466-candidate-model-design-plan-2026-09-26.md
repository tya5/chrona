# Design Plan — Candidate Placement, Plot Notes and Balloon Treatment (#466)

**Issue:** [#466](https://github.com/tya5/chrona/issues/466). **Published base:** `e2c75976` accepts the shared-obstacle prerequisite after [green three-OS CI](https://github.com/tya5/chrona/actions/runs/36233066182); its [acceptance review](../../reviews/current/issue-466-shared-obstacle-prerequisite-acceptance-review-2026-09-26.md) leaves rows 2–7 open. The earlier [general placement design](../../design/issue-466-general-placement-design-2026-09-26.md) expressly leaves candidate syntax, nearest-free and tail treatment unresolved. This plan completes those contracts before any new product code.

## Published facts, inference and unverified questions

Published View v0.22 has a global `visibility.fallback.annotations` rung ladder and per-annotation `placement.side/alignment`; normalization creates `AnnotationIntent` from View-authored `text`. HALCYON 02's three visible notes instead come from Project `annotations` and are laid out as plain `notes` slot text. They are **not** currently View presentation annotations and lack a selected facet/endpoint. Thus the acceptance example cannot be achieved merely by changing an annotation search function. It is inferred that a View reference to a selected Project annotation is needed to avoid copying Project narrative text into View. Verify intended source identity and selection behavior against Specifications 06/08 and current resource closure before approving that model.

## Literal #466 acceptance ledger

1. One obstacle set is computed per surface and used by every placement and leader route. A committed test shows a note beside a dependency line no longer covers it.
2. Placement candidates are declared as region, search, obstacles and connector. The existing rung names expand to candidates, and all committed evidence is unchanged by that refactor.
3. A nearest-free search exists. With candidates plot → nearest-free → tail and no rail slot, HALCYON-1 `02-programme-board` places all three notes without covering a mark, a label or a dependency path, and without crossing the as-of line.
4. The same slide with candidates plot → nearest-free first, then rail, falls back to the rail when the plot is made too crowded, with a diagnostic naming the candidate used.
5. Placement is deterministic and bounded. The placement decision records the candidate chosen and the search count.
6. A Theme can draw the tail and balloon outline. A Theme without it renders as today.
7. The specification describes the model once, and no longer as a list of per-rung behaviours; `06-view-model.md` and `44-usable-explicit-rows-and-annotation-rail.md` point at it.

Row 1 is an O2 prerequisite, not proof of the other rows. Row 2 requires a byte-identical normalization-only publication against the accepted O2 baseline. Rows 3–6 need separate focused/public/adapter gates; row 7 closes the normative documentation.

## Design decisions to finish before code

1. **Source and identity.** Decide whether View presentation annotations may reference a Project annotation by stable ID, how text and object anchor are inherited, how View supplies facet/endpoint and purpose without duplicating semantic facts, and how the old `notes` slot is omitted for a plot-balloon target without losing Project note provenance. Define missing/filtered reference diagnostics and deletion behavior.
2. **Resource ownership and migration.** Select a versioned View candidate grammar (likely successor to v0.22), decide whether candidate lists belong per annotation or in a reusable Layout profile, and define exact normalization of legacy `rail/above/below/start/end/suppress` rungs. Preserve legacy bytes in the normalization-only slice; document intentional resource migrations and no compatibility shim that compromises clean ownership.
3. **Closed candidate contract.** Specify typed `region`, `search`, `obstacles`, `connector` fields, ordered IDs, slot/plot/content/intersection geometry, allowed obstacle classes and mandatory plot safety, explicit as-of barrier, endpoint/attachment, candidate-specific connector topology, and no-rail layout behavior. Define when a resource is invalid versus when a valid dense layout completes visible fallback or explicit suppression.
4. **Nearest-free algorithm.** Select measured box sizing, finite lattice origin/step/bounds, ordering/ties, joint box+tail fit, as-of partition, search-count unit, diagnostics and determinism across writing mode/locale/metrics. Do not use renderer font measurements or an unbounded retry.
5. **Theme/Scene/adapter treatment.** Choose versioned Theme tail/balloon tokens, renderer-neutral outline/tail Path geometry, source identity, text containment, fill/stroke order, SVG/typeset/PNG parity, and exact plain-Theme fallback behavior. A tail is not a semantic dependency or post-Layout adapter rule.
6. **Whole-architecture review.** Check Project → View → Theme → Layout → Scene → adapters, Specs 06/07/08/33/44/50, #413 purpose-independent ladder, #449 visible fallback, #467 lane dependency and public HALCYON/controller examples. Correct living specifications or add an ADR for new source-reference semantics before implementation planning is final.

## Design slices and publication

1. Publish this plan and a baseline characterization of View v0.22, HALCYON 02's three Project notes, Theme treatments and O2 evidence.
2. Publish source-reference/candidate grammar design plus normative schema/spec changes and architecture review. No product code in this phase.
3. Publish measured nearest-free and connector/balloon design with SVG/typeset/PNG treatment, whole-architecture review and migration evidence. Amend any prior design rather than silently rewriting it.
4. Publish an implementation plan with independent public slices: legacy-rung candidate normalization/byte parity; Project-note reference and no-rail plot input; strict nearest-free/rail fallback and diagnostics; tail/balloon Theme/Scene/adapters; literal acceptance/CI review. Each slice names files, generated artifacts, focused tests and public materializers. Do not split a schema/preset migration from the code that keeps affected contexts materializable.

No new candidate implementation starts until the O2 CI/review gate and this full design/review/plan sequence are published. #466 remains open until all seven literal rows are met.
