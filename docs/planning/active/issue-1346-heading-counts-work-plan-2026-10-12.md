# Reusable heading counts (#1346)

Baseline: trusted READY `8a16dca1f4616beda7283c90ab9a4b24c70c03a2`.
[Issue and current work record](https://github.com/tya5/chrona/issues/1346#issuecomment-6112367414).
#1343 / PR1425 closes selected note identity/content; it must merge before
product implementation. No product changes or second implementation PR here.

| Literal acceptance | Evidence required |
| --- | --- |
| The three designs produce the same text on HALCYON from the template. | Disposable Title Card/Marquee/Sunday migration; real Scene and SVG text, not only formatter results. |
| On the roadmap, they show its own counts. | Same templates against the roadmap; independent selected/completed membership evidence and actual rendered text. |

Do not edit `examples/**`; permanent adoption is reviewer-owned.
Design slices, before final implementation planning:
1. Close item/group membership and ghost/combined deduplication; distinguish
   selected facts from completed narrative records. Decide whether rail-only
   notes, unconsumed notes and explicit duplicate narrative occurrences count.
2. Extend existing derived-figure grammar with shared declared digits,
   zero-padding, English cardinal and available kanji names. Close zero/range,
   capitalization, missing-table diagnostics and all three consumer ingresses.
3. Close the Layout dependency: count-dependent heading measurement can change
   note suppression. Review finite candidate-count validation (at most N+1
   complete layouts for N possible records; highest self-consistent result)
   and explicit no-solution diagnostics, rather than assume convergence or
   count selected notes as placed. Prove isolation of failed trials and work.

Architecture review: Specs03/05/06/33/44/50/56, #586/#927 and #1341/#1343.
Core accepts neutral integer facts; Projection owns selection; Presentation
owns formatting; Layout owns completed counts/measurement/placement. No Scene
recounting, adapter substitution, Project-specific names or previous-render state.
Publish selected normative behavior and whole-architecture review before code;
then finalize slices/files, synthetic suppression/cycle/format tests, disposable
three-design/roadmap evidence, batch public outputs and exact-main release gates.
