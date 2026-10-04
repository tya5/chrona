# Issue #1130: complete numbered annotation list (work record)

**Public base:** `cc6baa905325620cb0f47761e0717c7b0a252f2a` (`origin/main`).
**Status:** design and architecture reviewed; implementation not started.
This record selects issue option (a). It supersedes no other issue and changes
normative behavior in Specifications 33 and 46; implementation waits for publication.

## Baseline and literal acceptance

View order assigns stable numbers before Layout. Layout composes each numbered
entry in the annotation rail, then independently places its optional plot index;
an index failure emits `W_LAYOUT_NOTE_INDEX_SUPPRESSED` and keeps accepted
entry text and leader (Spec 33; #466 index/leader correction). A separate
annotation fit-ladder `suppress` can omit the whole callout with
`W_LAYOUT_ANNOTATION_SUPPRESSED`.

The published `controller-z/annotations` Scene on this base has rail text
numbers 1, 2, 3, 5; plot indexes 3 and 5; index-suppression diagnostics for
`architecture-callout` (1) and `evb-highlight` (2); and whole-callout
suppression for `firmware-slip` (4). Thus the cited missing “4” in the rail is
caused by whole-callout suppression, not index-only suppression. Existing
#1074 deliberately suppresses that actual-facet arrow. The issue's cited crop
is not published in this checkout; this Scene is direct public evidence. The
chosen complete-list rule covers both paths so it addresses the visible gap;
the synthetic acceptance must keep them distinct.

Literal #1130 acceptance:

| Criterion | Planned evidence |
| --- | --- |
| With one of four indexes suppressed, list and plot agree under chosen rule. | Synthetic four-annotation case: stable complete list, one explicit not-on-plot status, other three indexes present. |
| Suppression diagnostic is still reported. | Assert exact `W_LAYOUT_NOTE_INDEX_SUPPRESSED:<id>` in Scene. |
| When nothing is suppressed, output is byte-identical. | Compare Scene and SVG bytes with the pre-change result for the same synthetic input. |

## Selected design

In a declared `annotations` slot, each numbered View annotation contributes exactly one ordered list entry with
its original number. When only the plot index is suppressed, retain the
accepted annotation note text and append a visible `index not shown on plot`
status; keep its required leader connected and the existing index-suppression diagnostic.
When the callout box/leader is suppressed, retain a compact numbered summary
entry with distinct `callout not shown on plot` status; keep the existing
whole-callout diagnostic and do not invent a box, plot index, or leader. Thus
the missing `firmware-slip` #4 becomes an explicit list entry without undoing
#1074's intended arrow suppression. Status is derived Layout presentation, not
a Project/View fact, schema field, or adapter lookup. Fully realized entries
render exactly as today.

The list summary and plot callout/index are separate Layout outputs. Layout
must complete index/callout visibility decisions before finalizing list status,
preserve View order/number identity, and measure final list text before
committing geometry. If sequencing requires a structural phase split,
implement that instead of post-hoc Scene edits. The list uses the existing
`annotations` slot and Theme roles; no new authoring resource or schema is
introduced. Compact summaries may increase rail demand; visible overflow
remains explicit and must be included in review. Number renumbering (option b)
is rejected: it changes stable View numbering and requires remeasurement after
a Layout decision.
Without that slot, preserve plot-only behavior: Layout cannot invent a slot.
Suppression-only summaries/status may reflow the rail in View order. Recomplete
affected boxes and required leaders atomically; never move only their text.
No-suppression geometry stays exact; suppressed plot callouts stay suppressed.
Reflow suppression is monotone for both indexes and callouts; retry only on
strict growth of suppressed identities. Revalidate still-visible outputs;
never restore a suppressed index or leave its status stale.

## Architecture and migration

View continues to own selection, source order and stable ordinal. Layout owns
fit decisions, list status/summary, text measurement, and geometry. Scene
carries the completed list text, indexes, and diagnostics; SVG/other adapters
serialize those outputs unchanged. No Theme, View, Project, schema, or
generated example edit is expected. The intentional compatibility change is
limited to suppressed annotations: index-only failures annotate the existing
entry; whole-callout failures add a compact numbered summary with the distinct
status. Existing diagnostics remain; #1074's arrow remains absent from plot.

Specification 33 defines the independent list and plot-index contract;
Specification 46 states numbered annotations keep their View ordinal and
links to the Layout status rule. Tests are synthetic and include index-only
suppression, whole-callout suppression, both suppressions in one run, and the
no-suppression byte-identity control. Corpus `controller-z/annotations` is
review evidence only, not the test oracle; preserve #1074's intentional
callout-suppression diagnostic and do not edit reviewer-owned resources.

## Implementation plan and publication boundary

1. **Design publication (this slice):** this record and Specs 33/46 only;
   review contract and sequencing before product changes.
2. **Layout implementation:** `src/chrona/presentation/layout/surface_annotations.py`
   plus the smallest needed Layout result/model owner. Add a bounded synthetic
   integration test, preferably `tests/integration/test_annotation_index_suppression.py`;
   retain relevant `tests/unit/chrona/usecases/test_render_review.py` coverage
   for #1074's whole-callout diagnostic. No `examples/` or generated output.
3. **Verification:** focused synthetic tests assert ordered numbers, visible
   statuses, plot-index set, both exact warning codes, and independent
   whole-callout behavior; compare Scene/SVG bytes when no suppression occurs.
   Run conformance and the public materializer check; inspect controller-z
   annotation SVG/Scene as impact evidence. Do not run the full pytest suite
   locally absent a concrete risk; CI supplies release matrix evidence.
4. **Acceptance review:** record every literal criterion above with exact
   commands, public commit/CI, and actual rendered output. Keep #1130 open
   until exact-main release evidence passes.
