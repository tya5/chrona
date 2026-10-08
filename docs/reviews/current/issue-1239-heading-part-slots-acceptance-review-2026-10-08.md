# Heading part slots acceptance review

<!-- chrona:literal-acceptance/v1 -->

Implementation through `224ea2ce9874e18b14616944c25cd010c9555a82`, based on
ready main `d5bdf0be26c128b76baf87d59b80189b7d87b3cb`.
Split runs retain numeric spacing through native block measurement; placements
consume the closed stack baseline and baseline-minus-font-size bounds.
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

Combined focused heading/profile/source/network, Layout/Scene boundary,
module ownership, vocabulary, text-stack and allocation tests: 354 passed.
Schema equivalence L1/L2/L3,
schema annotations, role-consumer and semantic reachability checks passed.
Whole-title composition, legacy network title placement and routes remain on
their existing paths. Split placements consume closed measured bounds/baselines;
Scene only projects identities, ownership and paint. No examples or generated
outputs were authored. Unallocated copy does not require unused typography.
CI run 37778346231 exposed nine generic allocation fixtures claiming `title`
repeatedly and one incomplete vocabulary assertion. The fixtures now use an
ordinary source; all four approved source values are registered and compared
without splitting dotted names. Duplicate-heading validation remains strict.
