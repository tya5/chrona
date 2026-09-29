# Implementation amendment — context-specific wallboard allocation (#504, #502)

Amends the [R1–R5 implementation plan](issue-504-501-readable-default-implementation-plan-2026-09-29.md) after the [design correction](../../design/issue-504-502-context-specific-wallboard-design-correction-2026-09-29.md) and [architecture review](../../reviews/current/issue-504-502-context-specific-wallboard-architecture-review-2026-09-29.md). It supersedes the shared-wallboard instruction in the [#530 amendment](issue-504-502-lane-table-allocation-implementation-amendment-2026-09-29.md); that record remains historical and must not be followed for this migration.

## Literal issue acceptance retained

These are the literal #504 and #502 acceptance criteria; this amendment changes only the Layout resource migration and adds evidence needed to protect unaffected contexts.

| Issue | Literal acceptance criterion |
| --- | --- |
| #504 | “The bundled default and the `chrona init` starter keep an informative table under lanes. Where a lane holds one item, the lane label is that item's name. Otherwise the default View does not use lanes. Either way, no table column is empty on every row. The #498 gate is extended to assert this.” |
| #504 | “Lane height can grow into available plot height for stagger rows before a name is suppressed, as a declared Layout policy, for example with `rowDistribution: fill` (#434). A name is suppressed only when the lane cannot grow. On 02, the suppression count is reported in the acceptance review, and every suppressed name is attributed to a lane that could not grow.” |
| #504 | “The lane table does not repeat the group header's text on the group's first lane, and it never shows an empty label next to a count.” |
| #504 | “A mechanical check over committed lane slides: the ratio of shown to packed names is reported in the corpus coverage, so a regression is visible.” |
| #502 | “Select a meaningful declared table policy for group-less lane Views (for example `label: lane`, or an explicitly omitted lane table); do not infer a title from an arbitrary member.” |
| #502 | “The public 03 SVG/Scene shows that policy, with unchanged lane/member IDs and relation routes unless separately attributed.” |
| #502 | “Focused View/resource tests, regenerated public evidence, and affected CI gates pass; unrelated automatic output stays byte-identical.” |

The later #504 comment further says: “The first acceptance row should also cover this: the host of attached points keeps a visible name, in the lane label or in the plot.” Keep that as a first-row acceptance check, as already directed by the R1 plan.

## Resource migration and pinning

Add a complete `examples/halcyon-1/layouts/wallboard-programme-board.yaml` profile by copying the current `layouts/wallboard.yaml`, preserving its node IDs and all policy except `table.inlineSize`, whose minimum becomes `{fixed: 300}` inside the existing `minmax` maximum `{fr: 2}`. Set profile ID to `wallboard-programme-board`. Do not edit `layouts/wallboard.yaml` and do not use `extends`.

Change only the Layout references in `contexts/02-programme-board.yaml` and `contexts/12-glyph-gates.yaml` to `id: wallboard-programme-board`, kind `layout-profile`, address `layouts/wallboard-programme-board.yaml`, provider `local`, store identity `halcyon-1-example`, and revision token `example-v1`. Keep each Context's other references and content unchanged. Keep contexts 04/07/15 pinned to `wallboard`, `layouts/wallboard.yaml`, and `example-v1`; their Context bytes and generated Scene/SVG/raster evidence must remain byte-identical. Context resource `contentIdentity` remains omitted as in existing HALCYON Contexts (it is optional in Render Context v0.16); let the public materializer compute the new profile/context closure content identities from exact source bytes, and verify the emitted SHA-256. Do not reuse the original wallboard hash or manually patch generated identities.

`extends` is explicitly deferred: the resolver's optional `bases` argument is not supplied by `render_review.py`, Context closure currently loads only the top-level Layout, and the materializer does not recursively copy Layout bases. The future inheritance slice must design and test that complete runtime/pinning path before any Context uses it.

## Focused execution and acceptance gate

1. Add/adjust resource tests to validate the standalone profile as a full v0.9 root resource and assert its `table` minimum and stable node IDs. Assert contexts 02/12 reference only the new profile and 04/07/15 retain the exact original Layout references.
2. Keep R1 View tests and #502/#504 semantics intact: meaningful table cells; no repeated group header/empty label; attached host visibly named; unchanged lane/member IDs and relation routes; record shown/suppressed counts and the #504 per-lane suppression attribution for 02.
3. Regenerate the affected public materializer set as one batch after all R1/R2/R3 changes that are ready. Inspect Scenes and SVGs for 02/12 and the #502 public 03 evidence; inspect raster evidence wherever paint changes. Confirm table/timeline geometry and completed `bustest-integration` route on 02, no unexplained relation-quality diagnostics, and the expected policy in public Scene/SVG.
4. Compare generated outputs against the pre-change `origin/main` baseline. Contexts 04/07/15 (and all unrelated automatic outputs) must be byte-identical. Review every changed generated file as a batch, then run `tools/regenerate_public_examples.py --check --jobs 4` and the focused View/resource/layout tests. CI supplies the planned full matrix and newest-Python materializer gate.

Do not treat these checks as issue closure: publish a review row for every literal criterion above, with direct test/artifact evidence and `met`, `deferred`, or `not met`; keep #504/#502 open until their respective acceptance reviews and required review-bearing main CI pass.
