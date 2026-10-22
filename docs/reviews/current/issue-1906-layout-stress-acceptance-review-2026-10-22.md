<!-- chrona:literal-acceptance/v1 -->

# Issue 1906 — layout stress acceptance review

**Not release-accepted. PR #1914 remains draft/HOLD; keep issue1906 open.**
Implementation: [477373fc0](https://github.com/tya5/chrona/commit/477373fc0).
[Current design/architecture/implementation record](https://github.com/tya5/chrona/issues/1906#issuecomment-6332734477).
Normative authority: [Spec33](../../specification/33-intent-oriented-layout.md), with Specs06/07/24/44/50 and ADR0032.
Public design119a885f8 preceded the corrective core implementation.

Reviewer [6340416247](https://github.com/tya5/chrona/pull/1914#issuecomment-6340416247) rejected the prior green artifact12423766881: styled cards became bare lists and Sunday reserved unused height. The correction shares exact Theme card measurement, reserves ordered suffix capacity, and closes completed legend/annotation source use through normal Layout reflow. Scene/adapters remain passive. No project data/date/text edits, safety waivers or manually authored derived outputs.

## Literal issue acceptance

### Issue #1906

- Source: [Issue #1906](https://github.com/tya5/chrona/issues/1906)
- Observed: 2026-10-22

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
|1|at any viewport every drawn swatch has a non-empty label and both lie inside the legend box; when they do not fit, the legend wraps or grows, and a diagnostic names the real cause.|deferred|Shared measured legend closure; source trials refilter the full inventory and size only completed entries. Both actual Sunday contexts draw the realized keys. Final official snapshot review pending.|— (keep issue open)|
|2|no text of one header slot intersects another slot; a title that does not fit wraps, or the header row grows.|deferred|Bounded heading and source-sizing controls pass. Recheck actual header/legend intersections in the new official snapshot; prior artifact is not final evidence.|— (keep issue open)|
|3|every note box lies inside its slot and frame, or the overflow is diagnosed with the note named.|deferred|Four rail-first designs preserve a full Theme card before explicit list exhaustion. Actual HALCYON/roadmap Titlecard retain3/2 cards and0 lists; unequal-height, exact decimal shared-edge, tilt and icon controls pass. Final snapshot containment review pending.|— (keep issue open)|
|4|notes in a side panel stack in the vertical order of their anchors (ties by View order), no two leaders cross, and no leader passes through a bar. Design note first (spec change).|deferred|Physical anchor order and View ties retained. Suffix capacity reserves later full frames without weakening box/connector collision validators; fresh per-trial state and accepted-only progress tested. Final rendered route audit pending.|— (keep issue open)|
|5|with an explicit viewport width, wrappable text wraps before the page widens; the page widens only for content that cannot wrap, and says which.|deferred|Explicit viewport/wrapping and strict authored-cap contracts retained. Four actual materializations remain1600px wide; existing width/legend/source controls pass. Final stress replay review pending.|— (keep issue open)|
|6|every placed callout has a tail touching its anchor and covers no other object's mark; when no such spot exists, the note goes to the panel/list the design declares. Design note first: the fallback target.|deferred|Declared terminal lists remain explicit; plot-first notes reserve no unconditional footer. Actual HALCYON Sunday is900px with3 callouts and no footer. Roadmap Sunday is925px with a real17.55px list ending897px plus28px authored bottom padding; not an empty95px reservation. Owner comparison pending.|— (keep issue open)|
|7|every drawn group shows its name somewhere readable; a group label is never reduced to zero characters (fall back to a horizontal header or a key).|deferred|Prior frozen/current-A4 full-name evidence is linked from the living record and assets-1906; no new group policy was introduced. Final candidate group-name/painted-text review remains required, including roadmap marked-run headers.|— (keep issue open)|
|8|note-leader placement reuses one obstacle index per surface instead of rebuilding it per candidate, and `--progress` reports that phase. (Profile-first; record before/after.)|deferred|Shared surface index/query overlay and annotation-leaders phase retained; quiet/progress byte identity and joint count/source accepted-progress tests pass. Controlled serial/idle before/after target-b A timing remains outstanding; prior loaded measurements are not valid timing evidence.|— (keep issue open)|

## Verification and remaining release gates

Focused local groups passed:311 source/legend/port tests;160 adjacent legend/annotation tests;31 joint count/source tests;28 card/tilt integration tests;37 source/precision/planner tests. These groups overlap and are not additive. Import direction and module reachability pass; the float accumulation guard passes, retaining Decimal source demand and explicit completed-float geometry domains. A delegated broad layout run was stopped after2520 passes; it is not a completed suite or release evidence.

Four materializers ran with write=False, allowing only E_MATERIALIZER_MISMATCH after writing temporary evidence: HALCYON sunday/titlecard and roadmap-sunday/roadmap-titlecard. Actual Scene/SVG and PNG inspection confirms card presentation and occupied footer geometry described above; output mismatches are expected source changes, not golden updates. The exact-main three-OS full suite remains CI-owned.

Required next: new official artifact and per-slide delta ledger (HALCYON02/21–25 and five roadmap designs first), reviewer/owner comparison, controlled idle timing or an explicit approved alternative, current ready-main reconciliation/landing queue, and successful three-OS release on the exact main commit containing this review. Old green CI39773281648 and historical assets are preliminary evidence only.
