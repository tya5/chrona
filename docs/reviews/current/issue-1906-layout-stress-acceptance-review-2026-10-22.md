<!-- chrona:literal-acceptance/v1 -->

# Issue 1906 — layout stress acceptance review

**Functional acceptance evidence is complete; release acceptance is a separate gate.**
Keep issue1906 open until successful final-head CI and the three-OS run on the
exact review-containing main are recorded in its closing comment.
PR [1914](https://github.com/tya5/chrona/pull/1914), head1275ccda3, passed
[CI39865857613](https://github.com/tya5/chrona/actions/runs/39865857613) and merged
at2d10bb5da6bab2cf7b58aa3d45c67d371a04f5e5.
The live-progress residual is published at
[e075a1e5a](https://github.com/tya5/chrona/commit/e075a1e5a), after its
pre-code specification [d28b3ba37](https://github.com/tya5/chrona/commit/d28b3ba37);
its current publication/release receipt is maintained in the issue work record.

Authority: [current work record](https://github.com/tya5/chrona/issues/1906#issuecomment-6332734477),
[progress correction](https://github.com/tya5/chrona/issues/1906#issuecomment-6352889826),
[Spec33](../../specification/33-intent-oriented-layout.md), Specs06/07/24/44/50,
and ADR0032. Layout owns measurement, placements, routing and typed crossing
evidence; Scene/adapters remain projection. Progress is ephemeral observation,
never an artifact input. No project data/date/text or bot-owned outputs were edited.
Reviewer [6352487967](https://github.com/tya5/chrona/pull/1914#issuecomment-6352487967)
accepted the restored cards/leaders and Sunday height and lifted HOLD.

## Literal issue acceptance

### Issue #1906

- Source: [Issue #1906](https://github.com/tya5/chrona/issues/1906)
- Observed: 2026-10-23

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
|1|at any viewport every drawn swatch has a non-empty label and both lie inside the legend box; when they do not fit, the legend wraps or grows, and a diagnostic names the real cause.|met|Measured legend closure and narrow/wrap controls; official50 audit:266 nonempty labels and572 contained legend primitives. Current SundayC2/C4 retain5 keys at requested1024/900 widths. [Controls](../../../tests/unit/chrona/presentation/layout/test_legend_measurement_closure.py).|—|
|2|no text of one header slot intersects another slot; a title that does not fit wraps, or the header row grows.|met|Current SundayB actual SVG has4 full title lines,325.148px wide inside328px allocation;22.852px clearance to kicker/subtitle and38px to the next section. [Controls](../../../tests/unit/chrona/presentation/layout/test_heading_inline_budget.py).|—|
|3|every note box lies inside its slot and frame, or the overflow is diagnosed with the note named.|met|YuyaB en/ja: all3 full cards contained in annotations slot and board frame; final English card ends exactly at slot bottom684. Official51 box hulls are canvas-contained; declared text overflow remains named, not hidden. [Controls](../../../tests/integration/test_annotation_card_fallthrough_1906.py).|—|
|4|notes in a side panel stack in the vertical order of their anchors (ties by View order); every rail note card retains its declared leader to its target. Use a clear route where available; otherwise draw the declared hairline across, with a diagnostic naming what it crosses. Plot callout bodies and tails retain strict mark clearance. Design note first (spec change).|met|[Owner amendment](https://github.com/tya5/chrona/pull/1914#issuecomment-6351461724); Spec33/44 correction493449e66 preceded code1551440a0. All4 HAL rail designs retain3 cards/3 leaders/0 lists; exact painted crossings are named, including tilt extension, without false own-card crossings. Anchor/View ties and strict plot/body/tail controls pass. [Controls](../../../tests/integration/test_annotation_card_fallthrough_1906.py).|—|
|5|with an explicit viewport width, wrappable text wraps before the page widens; the page widens only for content that cannot wrap, and says which.|met|Current TitlecardB en/ja1600px; C2 en/ja1024px; C4 en/ja900px; MarqueeC4 900px. Current TitlecardA4 en/ja1123px with all117 Scene texts matching SVG. Height may grow with an explicit overrun warning. Frozen old A4 declarations lack the required list fallback and need migration; they are not current-design evidence. [Controls](../../../tests/integration/test_group_header_source_demand_1906.py).|—|
|6|every placed callout has a tail touching its anchor and covers no other object's mark; when no such spot exists, the note goes to the panel/list the design declares. Design note first: the fallback target.|met|Current SundayA/E/C4 actual SVG+Scene:4/3/2 integrated balloons; all9 tips touch their mapped source mark at painted stroke width, with zero unrelated-mark tail-edge hits. B emits0 balloons and3 declared list rows. HAL Sunday remains900px; roadmap925 reflects an actual list, not empty reservation. [Tail geometry controls](../../../tests/unit/chrona/presentation/layout/test_annotation_search.py), [exhaustion controls](../../../tests/integration/test_annotation_plot_overflow.py).|—|
|7|every drawn group shows its name somewhere readable; a group label is never reduced to zero characters (fall back to a horizontal header or a key).|met|235 official group headers nonempty. Current YuyaB SVG shows full owner names, including Maximiliana Konstantinopoulou-Oyelaran; D retains all en/ja names and horizontal fallback for Unassigned. Twelve preexisting Sunday ellipses are not empty labels. [Controls](../../../tests/integration/test_group_header_identity_1906.py).|—|
|8|note-leader placement reuses one obstacle index per surface instead of rebuilding it per candidate, and `--progress` reports that phase. (Profile-first; record before/after.)|met|Provisional bodies use read-only query overlays on each surface trial's shared index, not whole-index copies per candidate. Hosted before/after profile below. e075a1e5a forwards uncounted work starts through nested buffers; actual target-bA stderr shows annotation-leaders start while render remains live.12 model/12 CLI controls plus35 adjacent closure/wiring tests pass; accepted counts stay buffered and quiet/progress SVG/stdout identity holds. [Controls](../../../tests/unit/chrona/presentation/model/test_render_progress.py), [actual CLI](../../../tests/integration/test_render_progress_cli.py).|—|

## Programme-level criteria (optional)

Exact-head official [artifact12463429020](https://github.com/tya5/chrona/actions/runs/39865857613/artifacts/12463429020)
at1275ccda3 has100/100 before and100/100 after SVG/Scene files byte-identical to
reviewed e5cc artifact12463482648 and2ec artifact12461966278.
Artifact digest: `sha256:8ae7e61521052eeb7b5d556c9e449b19af09cb37b3572a7e68171467c0faa1f1`.
The PR's50-slide ledger records primitives10675→10665 (+3/−13/~1514),
545 logical dependencies/574 paths/29 paired stubs unchanged,629 rows unchanged,
and367 member names unchanged. Scene/SVG text agrees;122 intentional blank table
cells remain. Logical annotation slot metadata alone is not physical containment
proof; actual boxes/frames and named overflow were checked.

Targeted replays use unchanged public [trial17 inputs](https://github.com/tya5/chrona/tree/cbc183f6b/trial-17),
current product1275ccda3 (or source-identical64cb960), with input/source hashes in
batch receipts. Seven Sunday/Yuya cases, two current SundayA/E cases and nine
width cases were checked; the two frozen A4 failures were separately rerun with
only the original A4 size applied to current resources. No corpus data was
changed to obtain success. ControllerZ's two declaration-only fallback migrations
were explicitly authorized by reviewer6335461637.

Hosted [run39864595102](https://github.com/tya5/chrona/actions/runs/39864595102)
and [artifact12464740027](https://github.com/tya5/chrona/actions/runs/39864595102/artifacts/12464740027):
one serial cProfile pair, identical A-en inputs/Python3.13.16 and common dependency
versions, before820688585 → aftere5cc70efb. Wall301.91→472.57s; CPU301.72→472.50s.
**This pair is slower (+56.5% wall), not a speedup claim.** Annotation completion
runs1→2 times, candidate trials1797→1910, orthogonal routing calls502→556 and
index collision calls5.63M→8.94M. The second completion is consistent with source
closure; these observations do not establish the cause of the entire delta.
Profiling overhead and fixed before/after order prevent a general causal estimate.
The benchmark branch is verification-only and must never merge.

That same artifact exposed467s of CLI silence because accepted-trial counts were
buffered. d28b3ba37/e075a1e5a distinguish immediate attempted-work observations
from accepted completion counts; no timers, routing budgets or geometry changes.
Independent review found no defect in this boundary. This does not claim a
periodic heartbeat during one declaration's search.

Previous CI39859932981 failed only the obsolete list-on-routing-failure test;
64cb96090 instead forces genuine card-body exhaustion (50 focused passes).
No rollback, golden edit or clearance waiver was used.
Separate highlight/leader contract issue [1935](https://github.com/tya5/chrona/issues/1935)
is explicitly reviewer-parked after RC, outside this issue.

Release rule: the issue closing comment must cite successful final implementation
and progress-follow-up CI, plus the exact review-containing-main three-OS
pytest/conformance/wheel-smoke and newest-Python materializer evidence.
Snapshot identity is not a release gate.
