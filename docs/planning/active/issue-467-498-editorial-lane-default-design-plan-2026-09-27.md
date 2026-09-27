# Design Plan — Editorial Reference and Lane Defaults (#467, #498)

**Published baseline:** `main` at the accepted View v0.27 L2 review `25fd9648` (the product commit is `ba8d99d0`). **Issue authority:** [#467](https://github.com/tya5/chrona/issues/467) remains open; [#498](https://github.com/tya5/chrona/issues/498) is closed with an owner decision and acceptance review. **Related implementation ladder:** [L3 publication amendment](issue-467-494-l3-lane-completion-publication-amendment-2026-09-27.md). This plan opens a bounded design decision; it does not change either issue's acceptance wording.

## Published facts and conflict

- #467's literal fifth acceptance criterion is: “New Views and the packaged presets default to lanes; `automatic` still renders exactly as today.” Its selected lane design makes the left table a group/lane summary, prohibits item-subject `tableColumns`, and requires visible plot item names.
- #498's owner decision keeps Editorial's visual language as the bundled default with row guides, bar-end/start names and table names; the `editorial` catalogue entry and `13-gallery-editorial` stay faithful to the reference, whose rows carry no ground. Its accepted public default currently uses the separate `editorial-readable-default` View.
- The eight packaged preset Views are currently `automatic`. View v0.27 admits `lanes` but public rendering fails closed until the L3 engine. The currently accepted 28 public SVGs are unchanged by L2.
- A reference-faithful Editorial catalogue View cannot itself satisfy the v0.27 lane contract: the reference has no row ground or required plot names, while lanes replace item table rows with a lane summary. Changing the catalogue entry without an explicit disposition would silently reverse #498's owner decision.

The user has been asked whether all packaged presets should move to lanes with Editorial's reference retained as a separately named gallery artifact, or whether Editorial remains an explicit exception and #467's acceptance is amended. That answer is not yet published authority. The L3a neutral allocator and L3b hidden composer/instrumentation do not depend on it; L3c default/preset activation does.

## Design work before L3c

1. Inventory every packaged preset, the bundled default selector, `chrona init` starter, catalogue aliases, `13-gallery-editorial`, immutable Contexts, and generated Scene/SVG/PNG evidence. Record which resources are reference examples versus new-View defaults, and the exact user-facing entry points.
2. Select the owner-approved identity and naming model. Specify which View resources stay reference-faithful, which become lane defaults, whether a catalogue alias migrates, and the intended incompatibilities. Keep `automatic` opt-out and immutable Context semantics explicit.
3. Define the lane default's table/group summary, plot title+delta, row guides, typography and palette so #467's lane acceptance and #498's bare-render/starter readability are both measured. Do not add item-subject table columns to lane mode or adapter-side label repair.
4. Review the result against Specifications 24, 38, 40 and 50; the #425 Editorial reference, #498 acceptance, #467 lane design, #466 route priority, #480/#481/#487 sizing, #486 attached milestones, and the v0.27 schema. Update the living specification or add an ADR if the public catalogue/default contract changes.
5. Publish a design correction in `docs/design/`, an explicit whole-architecture review in `docs/reviews/current/`, any normative update, and an L3c implementation-plan amendment before changing default or preset product resources.

## Acceptance evidence for the design

The chosen design must provide a migration map for all eight packaged presets and every affected user-facing alias; literal #467 row 5 must be either met or explicitly amended by the owner. The existing #498 bare HALCYON and `chrona init` starter checks must remain meaningful and prove row guides, in-row visible-or-reported names, Editorial palette/type/axis where that promise is retained, and a side-by-side reference comparison. Public materializer and generated image diffs must be reproducible. A Scene-only report is not visual acceptance.

Until this decision is published, no L3c resource migration or issue closure is authorized by this plan. L3a and L3b may proceed under their existing design contracts and separate verification gates.
