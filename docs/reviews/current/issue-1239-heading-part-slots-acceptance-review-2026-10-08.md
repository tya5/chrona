# Heading part slots acceptance review

<!-- chrona:literal-acceptance/v1 -->

Implementation: `440773ca1f5af9c2ec812c8718b79aafcc5e5360`, based on
ready main `2b168a73cc04a189afa84a4cf0f3ab3576dd2413`.
[Living design, architecture review and plan](https://github.com/tya5/chrona/issues/1239#issuecomment-6059626833).
Release acceptance remains pending exact-head PR CI, shared generated-output
inspection and published-main three-OS release evidence. Do not close yet.

## Literal issue acceptance

### Issue #1239

- Source: [Issue #1239](https://github.com/tya5/chrona/issues/1239)
- Observed: 2026-10-08

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | Title and subtitle sourced by two different slots render in those slots' bounds with their own roles. | met | [Actual timeline SVG and slot-bound assertions](../../../tests/integration/test_heading_part_slots.py); [network SVG, roles and native owners](../../../tests/integration/test_network_heading_parts.py). | none |
| 2 | `source: heading` is byte-identical. | met | [Whole `heading` alias versus existing `title`: exact SVG and Scene surface bytes](../../../tests/integration/test_heading_part_slots.py). Authored resource provenance differs deliberately; legacy network ignored View copy is also byte-characterized. | none |
| 3 | A part sourced twice is a profile error at its pointer. | met | [Exact later `/source` pointers, whole/part overlap and resolved inherited claims](../../../tests/unit/chrona/presentation/layout/test_intent_profile.py). | none |
| 4 | Marquee places only the title inside the sign. | met | [Neutral real bulb-sign SVG and PNG](../../../tests/integration/test_heading_part_slots.py): title contained, kicker/subtitle outside. Both actual images inspected; SVG raster and PNG are pixel-identical. Actual #1233 adoption belongs to reviewer per board. | none |

## Programme-level criteria (optional)

Focused heading/profile/source/network tests: 67 passed; Layout/Scene boundary,
module ownership and registry tests: 9 passed. Schema equivalence L1/L2/L3,
schema annotations, role-consumer and semantic reachability checks passed.
Whole-title composition, legacy network title placement and routes remain on
their existing paths. Split placements consume closed measured bounds/baselines;
Scene only projects identities, ownership and paint. No examples or generated
outputs were authored. Unallocated copy does not require unused typography.
