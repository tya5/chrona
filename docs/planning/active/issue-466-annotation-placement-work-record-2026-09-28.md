#466 — annotation placement completion: current work record

## Published baseline and design plan

Base `main`: `bbe6734f`. #467/#494 lane acceptance is merged (eight lanes,
24 visible dependencies and no route suppression on HALCYON 02); C2's
candidate engine is published. C3/C4 and the seven issue criteria are not
accepted. The old `wip/issue-466-c3` branch is evidence of intent only: it
predates View v0.28 and has no regenerated artifacts. #505 precedes further
Scene work and is under PR #520; recheck its merge SHA before product edits.

Literal issue acceptance:

1. “One obstacle set is computed per surface and used by every placement and leader route. A committed test shows a note beside a dependency line no longer covers it.”
2. “Placement candidates are declared as region, search, obstacles and connector. The existing rung names expand to candidates, and all committed evidence is unchanged by that refactor.”
3. “A nearest-free search exists. With candidates plot → nearest-free → tail and no rail slot, HALCYON-1 `02-programme-board` places all three notes without covering a mark, a label or a dependency path, and without crossing the as-of line.”
4. “The same slide with candidates plot → nearest-free first, then rail, falls back to the rail when the plot is made too crowded, with a diagnostic naming the candidate used.”
5. “Placement is deterministic and bounded. The placement decision records the candidate chosen and the search count.”
6. “A Theme can draw the tail and balloon outline. A Theme without it renders as today.”
7. “The specification describes the model once, and no longer as a list of per-rung behaviours; `06-view-model.md` and `44-usable-explicit-rows-and-annotation-rail.md` point at it.”

Use cases: plot balloons for three Project notes without a rail, bounded
plot-first/rail-second fallback on a crowded version of the same slide, and
unchanged legacy rail/side behavior. The C3 decision is whether all three
notes fit the *current* lane geometry under the published obstacle, as-of,
search and tail rules. Old automatic-row failure does not answer this.
Measure on a clean v0.28 closure before adopting resources; if any note
fails, return to design and whole-architecture review before changing code,
not to larger limits, missing obstacles, or skipped notes.

Review boundaries: Project supplies note identity/text; View selects sources
and ordered candidates; Theme supplies balloon/contrast treatments; Layout
owns the one obstacle index, measured boxes, bounded joint box+connector
search and final route; Scene transports completed geometry/paint; adapters
serialize it. Verify current Specs 06/07/08/33/44 and the C4 contrast design
against this chain. Preserve resource identity pins and materializability
across the atomic View+Theme+evidence publication. C4's six-root note-role
contrast migration follows accepted C3, as required by its published design.

Required evidence: exact note IDs and source consumption, candidate/search
records, zero forbidden intersections/as-of crossings, crowded rail fallback
diagnostic, rendered SVG/PNG, generated Scene and public materializer diff,
contrast/perceptibility reports, focused tests and CI matrix. The next
independently publishable slice is this rebaseline design/architecture review,
then an implementation plan; product work waits for #505 merge.

## Selected design and whole-architecture review

Keep the published C2 candidate contract and deterministic Layout search;
no engine policy is authorized merely to make 02 fit. Reapply only the WIP's
three Project-note references and one balloon Theme binding to the current
v0.28 View/Theme closure. Retain lane membership, plot labels, chain/date
packing and other current fields. The three notes consume Project text once;
the no-rail target uses only plot/nearest-free/tail candidates. A separate
crowded fixture adds rail as the second candidate to prove fallback, without
weakening the public no-rail case.

Each candidate remains a typed region, search, obstacle-class set and
connector. The selected candidate ID, bounded search count and any overflow
are Layout decisions; Scene neither searches nor re-routes. Tail geometry
and representative box paint are resolved from Theme before search. The
single obstacle inventory includes completed marks, required text, rule and
dependency paths. A failure to find a valid box is not silently converted
to success: existing visible-overflow behavior must be reported, and row 3
cannot pass when it overlaps or crosses the as-of line. Missing Project note
IDs, duplicate use or stale pins fail before materialization.

Architecture check: this preserves Specs 02/06 (Project versus View intent),
07 (Theme treatment and note contrast), 08/50 (completed Scene and adapter
delivery), 33/44 (Layout-owned placement), and 38 (#467 data-only lanes).
C4 uses the already published opaque representative-ground/same-source note
pair design; its six-root Theme migration, role admission, Scene contrast
and public evidence form one atomic later slice. No new public schema or
identity rule is selected here. The living Specs 06/44 should describe the
candidate model as current, with the rail as one configuration, rather than
pointing to it as a future successor. If the three-note trial fails, that is
a new design question and this review does not authorize a local workaround.
