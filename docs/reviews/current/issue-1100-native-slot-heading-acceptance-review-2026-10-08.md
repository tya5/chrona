<!-- chrona:literal-acceptance/v1 -->

# Release Review — Native Slot Headings

## Literal issue acceptance

### Issue #1100

- Source: [Issue #1100](https://github.com/tya5/chrona/issues/1100).
- Observed: 2026-10-08
- Current design and implementation plan: [Status](https://github.com/tya5/chrona/issues/1100#issuecomment-6041732444).
- Implementation: `24097f4c`, following natural-prefix `92887b8e` and candidate-demand `bb5cdc8a`. Local behavior verified; public snapshot and exact-main release remain pending. **Do not close yet.**

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `block: header-row` centres the caption in the whole axis band; the approved mock puts NOTES on the baseline of the upper axis tier. A tier-aligned variant needs the axis tier geometry (`surface_axis`). | met | [Actual SVG baseline and fallback tests](../../../tests/integration/test_slot_heading_copy.py); [native tier geometry](../../../tests/unit/chrona/presentation/layout/test_surface_axis_tier_geometry.py). | — |
| 2 | A View-level override of the caption copy (today a Context overrides it through a derived Layout Profile `overrides`). | met | [Actual SVG copy, immutable default, node identity and exact-pointer tests](../../../tests/integration/test_slot_heading_copy.py); Spec06 §7.5. | — |
| 3 | Headings on `group-details`, `milestones`, `observations` (and the `title`, `table`, `timeline`, `timeline-axis`, `network` sources, which reject a heading today because other rules own their block). | met | [All eight native sources in actual SVG and validated serialized Scene](../../../tests/integration/test_native_slot_headings.py); [all-source/derived profile admission](../../../tests/unit/chrona/presentation/layout/test_slot_heading_profile.py). Timeline/detail and network PNGs visually inspected. | — |
| 4 | A content-sized slot whose source is empty keeps the caption's block in its measurement though no caption is drawn. | met | [Empty/full summary, consumed notes and empty legend SVG comparisons](../../../tests/integration/test_empty_slot_heading.py); [shared detail presence](../../../tests/unit/chrona/presentation/layout/test_slot_heading_placement.py). Empty selected content neither draws nor measures a suppressed caption. | — |

## Programme-level criteria (optional)

### Architecture and verification

- View selects copy; Theme owns typography/paint; Layout closes exact-candidate natural prefix and final geometry; Scene/adapters only project/serialize. Native axis guards remain strict. Primary Scene table-reference closure is unchanged; auxiliary observation purposes retain their own attribution and state paints (Specs28/08).
- Candidate finite/auto renders and width-change lane preflight: [integration](../../../tests/integration/test_surface_candidate_demand.py), [natural closure](../../../tests/unit/chrona/presentation/layout/test_surface_natural_geometry.py). No fill-expanded measurement or previous-candidate preflight.
- Focused results: engine/allocation/flow 51 passed; axis/natural/allocation/empty-source 66 passed; copy/render handoff 13 passed; admission/native SVG/serialized Scene/observations/contrast 78 passed. Optional observation header-paint fixture 4 passed. Schema equivalence against `origin/main`: PASS (two declared optional schema deltas); import direction 11 packages/37 inward edges; reachability 192 modules/no orphans.
- Six unheaded bundled/default-or-explicit-lane SVG/Scene/slot comparisons against pre-connection `bb5cdc8a` were exact. These are synthetic checks, **not** the public corpus release gate. Broad legacy render-usecase tests stopped in route search after 8 passed/163.54s; the complete suite is delegated to CI, not claimed passed locally.
- PNG visual evidence: `/tmp/chrona-1100-native-visual.0SYR8U/{timeline,network}.png`, produced by the real CLI; transient local evidence only. Caption/title/table/axis/detail and network contents are legible and nonoverlapping. The floating-point-only observation overflow finding is covered with shared geometry tolerance and unchanged enclosing bounds.
- Independent non-monotone extent defect remains [#1214](https://github.com/tya5/chrona/issues/1214), with experimental code and unsuppressed repros publicly preserved. No generic least-height repair or waiver is claimed here.

## Publication gate — pending

One coherent PR must provide a reviewed shared public SVG/Scene snapshot and per-slide side-effect counts (including restored observation text and retired heading-source rejection). The exact review-containing main must pass three-OS pytest/conformance/wheel-smoke, MCP and newest-Python materializers before release acceptance and closure. No generated or `examples/**` edits are authored.
