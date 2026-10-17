<!-- chrona:literal-acceptance/v1 -->

# Issue #1610 — on-demand member-label repair

Final ready base `8fc5364c3022676b680268005417239eb094a5ca`; [PR #1623](https://github.com/tya5/chrona/pull/1623) merged as `340b9e708b4047eb02f83295427e2756aa56a50d`. The ready derived-main tip is `fa262ebab648229138eb34c33bf6a821f6450e96`.

## Literal issue acceptance

### Issue #1610

- Source: [Issue #1610](https://github.com/tya5/chrona/issues/1610)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Trace posted; a synthetic twin of the crossing case. | met | [Trace](https://github.com/tya5/chrona/issues/1610#issuecomment-6225778103); [same-inventory obstruction controls](../../../tests/unit/chrona/presentation/layout/test_member_label_route_obstruction.py), [one-retry and full-placement preservation twins](../../../tests/unit/chrona/presentation/layout/test_surface_route_label_plan.py), and [actual stroke checks](../../../tests/unit/chrona/presentation/layout/test_surface_route_label_stroke.py). | — |
| 2 | The two presets on the #1582 CSV draw no label crossed by a route or the as-of line, viewed as PNG. | met | Both final PNGs were viewed: [CSV](https://github.com/tya5/chrona/issues/1582) render; checkout screens and Customer dashboard remain visible. The actual-width audit finds 0 intersections: default 13 names/14 dependency primitives; executive-light 11 names/13 dependency primitives. No first-pass visible label is lost. | — |
| 3 | Public SVG/Scene changes listed with counts. | met | Exact PR run [39002549459 artifact 12090006524](https://github.com/tya5/chrona/actions/runs/39002549459/artifacts/12090006524): 109 paths, 0 added/retired; SVG 32 changed/18 identical; Scene 34 changed/16 identical. All 109 after-paths match the previously inspected artifact; no dependency primitive was removed. | — |

PR checks passed, including `derived-ready`, at `9ff8b12a8a932b09d1c6a7be9ada154c77b84ad0`. The exact-main three-OS release run `39003719153` is still live; this review does not treat it as green or close the issue.

## Programme-level criteria (optional)

Layout uses one coordinator: the ordinary completed plan remains the reference; at most one repair pass may replace it, preserving text identity/content, notes, relation status, and connected annotations with the same known ladder and a valid non-later rung. The repair considers route-only obstruction against each name's preceding inventory, reserves retained labels as hard obstacles, and revalidates every name. Only repair-obstacle identities enable the bounded channel supplement. It adds no Scene/adapter placement policy, project-specific branch, extra trial, or selective release.

The #1582 CSV audit reports default 13 names/14 dependency primitives and executive-light 11/13, with Checkout and Customer dashboard visible in both. The accepted architecture retains its single on-demand retry and first-index preservation.

Remaining disclosed output changes: DVT uses its declared exterior fallback rather than its former black inside position; HALCYON 01/03 and the programme-board family include label losses or exchanges. Firmware's summary remains. These are not represented as zero-diff outcomes or hidden by example edits.

The sequential HALCYON profile cost is material: routing 0.546s on main versus 9.955s on product; total profile 3.096s versus 12.778s (wall 3.153s versus 13.019s). This is disclosed as a cost, not a performance improvement. The exact-main release remains pending, so issue closure is also pending.
