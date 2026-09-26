# Design correction — as-of fallback collision consequence (#458)

**Predecessor:** [#458 design](issue-458-as-of-label-suppression-design-2026-09-26.md).

The first public-materializer regeneration revealed a design omission: adding
the visible as-of label to Layout's existing ordered label search changes the
obstacle set for subsequent member labels. On HALCYON 04, the visible TVAC
label switches from the base member to the scenario member; both labels retain
their stable source identities, and Layout records suppression for the other.
This is not an adapter or Scene decision.

Decision: the as-of label remains a real Layout obstacle. Ignoring it only to
preserve prior bytes would permit unreadable text overlap and violate the
shared collision policy. A candidate-rank change is allowed if no source text
is emitted against a suppression diagnostic, no new text intersection is
introduced, and the intended as-of label is beside its line. The SVG change
set is therefore the two as-of labels plus any deterministic member-label
reranking caused by their occupied geometry; it is not an unrestricted corpus
rebaseline. Review both 04 and 07 rendered output, not just Scene coordinates.
