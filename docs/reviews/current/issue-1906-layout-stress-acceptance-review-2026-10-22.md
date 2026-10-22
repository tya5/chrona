<!-- chrona:literal-acceptance/v1 -->

# Issue 1906 — layout stress acceptance review

**Not release-accepted. PR #1914 remains draft/HOLD; keep issue1906 open.**
Table dispositions mean final acceptance is not yet proven, not that the focused controls failed.
Implementation: [f610eeaf7](https://github.com/tya5/chrona/commit/f610eeaf7).
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
|1|at any viewport every drawn swatch has a non-empty label and both lie inside the legend box; when they do not fit, the legend wraps or grows, and a diagnostic names the real cause.|not met|Shared measured legend closure; source trials refilter the full inventory and size only completed entries. Both actual Sunday contexts draw the realized keys. Final official snapshot review pending. [Focused controls](../../../tests/unit/chrona/presentation/layout/test_legend_measurement_closure.py).|—|
|2|no text of one header slot intersects another slot; a title that does not fit wraps, or the header row grows.|not met|Bounded heading and source-sizing controls pass. Recheck actual header/legend intersections in the new official snapshot; prior artifact is not final evidence. [Focused controls](../../../tests/unit/chrona/presentation/layout/test_heading_inline_budget.py).|—|
|3|every note box lies inside its slot and frame, or the overflow is diagnosed with the note named.|not met|Four rail-first designs preserve a full Theme card before explicit list exhaustion. Actual HALCYON/roadmap Titlecard retain3/2 cards and0 lists; unequal-height, exact decimal shared-edge, tilt and icon controls pass. Final snapshot containment review pending. [Focused controls](../../../tests/integration/test_annotation_card_fallthrough_1906.py).|—|
|4|notes in a side panel stack in the vertical order of their anchors (ties by View order), no two leaders cross, and no leader passes through a bar. Design note first (spec change).|not met|Physical anchor order and View ties retained. Suffix capacity reserves later full frames without weakening box/connector collision validators; fresh per-trial state and accepted-only progress tested. Final rendered route audit pending. [Focused controls](../../../tests/integration/test_surface_annotation_phase_wiring.py).|—|
|5|with an explicit viewport width, wrappable text wraps before the page widens; the page widens only for content that cannot wrap, and says which.|not met|Explicit viewport/wrapping and strict authored-cap contracts retained. Four actual materializations remain1600px wide; existing width/legend/source controls pass. Final stress replay review pending. [Focused controls](../../../tests/integration/test_group_header_source_demand_1906.py).|—|
|6|every placed callout has a tail touching its anchor and covers no other object's mark; when no such spot exists, the note goes to the panel/list the design declares. Design note first: the fallback target.|not met|Declared terminal lists remain explicit; plot-first notes reserve no unconditional footer. Actual HALCYON Sunday is900px with3 callouts and no footer. Roadmap Sunday is925px with a real17.55px list ending897px plus28px authored bottom padding; not an empty95px reservation. Owner comparison pending. [Focused controls](../../../tests/integration/test_annotation_plot_overflow.py).|—|
|7|every drawn group shows its name somewhere readable; a group label is never reduced to zero characters (fall back to a horizontal header or a key).|not met|Prior frozen/current-A4 full-name evidence is linked from the living record and assets-1906; no new group policy was introduced. Final candidate group-name/painted-text review remains required, including roadmap marked-run headers. [Focused controls](../../../tests/integration/test_group_header_identity_1906.py).|—|
|8|note-leader placement reuses one obstacle index per surface instead of rebuilding it per candidate, and `--progress` reports that phase. (Profile-first; record before/after.)|not met|Shared surface index/query overlay and annotation-leaders phase retained; quiet/progress byte identity and joint count/source accepted-progress tests pass. Controlled serial/idle before/after target-b A timing remains outstanding; prior loaded measurements are not valid timing evidence. [Focused controls](../../../tests/integration/test_placed_note_count_closure.py).|—|

## Programme-level criteria (optional)

CI [39786575213](https://github.com/tya5/chrona/actions/runs/39786575213) at b19c0bf4d failed all three pytest shards (36 failures); preview, conformance, MCP-floor and newest-Python passed. Derived-ready failed on those pytest prerequisites. Corrections address actual source-demand matching, caption double-subtraction, ordered decimal rail intervals and Theme error pointers; instrumentation now asserts phase order and fresh state per joint trial, not per complete render. The obsolete note Scene hash changed only12 slot associations after unused-source pruning; SVG bytes were unchanged. No corpus golden was authored.

The focused batch covering all failing nodes and adjacent controls passed138 tests; final finite-state/phase controls passed26. Additional legend controls passed39 (overlap). Reproduce the final controls with `.venv/bin/python -m pytest -q tests/unit/chrona/presentation/layout/test_source_use.py tests/unit/chrona/presentation/layout/test_surface_source_closure.py tests/integration/test_surface_phase_wiring.py`. Finite-state tests exclude derived advances/footprints/diagnostic deltas while retaining face, glyph and partition identity; exact witness comparisons remain strict. Import direction, module reachability, float accumulation and literal-review guards pass. These are not the full suite or release evidence.

Four materializers ran with write=False, allowing only E_MATERIALIZER_MISMATCH after writing temporary evidence: HALCYON sunday/titlecard and roadmap-sunday/roadmap-titlecard. Compared with official b19 artifact12428819425, HALCYON Titlecard is byte-identical; Roadmap Titlecard18 primitives differ only in last-digit float serialization. Sundays11/9 primitives change only legend inline placement after the caption correction. No primitives, text or routes were added/removed; all legend items remain contained, Scene/SVG text agrees, and card/footer counts and occupied extents match the literal table. The exact-main three-OS full suite remains CI-owned.

Required next: new official artifact and per-slide delta ledger (HALCYON02/21–25 and five roadmap designs first), reviewer/owner comparison, controlled idle timing or an explicit approved alternative, current ready-main reconciliation/landing queue, and successful three-OS release on the exact main commit containing this review. Old green CI39773281648 and historical assets are preliminary evidence only.
