<!-- chrona:literal-acceptance/v1 -->

# Filled annotation heading acceptance (#1347)

Implementation: `313280e0`. [Current design/architecture/implementation record](https://github.com/tya5/chrona/issues/1347#issuecomment-6099523555). Spec07 #1191/#1051 corrections `06a85b4d`/`3f38821a` were published before product code.

## Literal issue acceptance

### Issue #1347

- Source: [Issue #1347](https://github.com/tya5/chrona/issues/1347)
- Observed: 2026-10-11

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A 40-character `{subject}` in a filled note wraps. | met | [Synthetic Scene/SVG tests](../../../tests/integration/test_filled_annotation_heading.py) assert multiple completed heading lines and preserved subject text, with border/content insets, both stamp sides and tilt; body starts below the completed heading. | — |
| 2 | The canvas stays at the viewport. | met | [Actual SVG viewport and box assertions](../../../tests/integration/test_filled_annotation_heading.py) verify `0 0 1600 900`, the300px filled slot extent, heading containment and no canvas-exceeds-viewport warning. | — |
| 3 | Do not edit `examples/**`. | met | [Product commit](https://github.com/tya5/chrona/commit/313280e065b9a63323a209fa6b549c1e2808186e) touches three Layout owners and two synthetic test files; authored `git diff --name-only origin/main...HEAD -- examples` is empty. | — |

## Programme-level criteria (optional)

Release pending: final preceding-item READY integration, CI public Scene/SVG delta disclosure/current-head gates and acceptance-containing exact-main three-OS release. Local rows do not authorize closure.

Owned kind-header, fill, stamp, bar-bleed and measurement tests at `313280e0`:115 passed (145.25s). Filled-heading/measurement suite after adding non-slot isolation and short-heading byte characterization:21 passed (8.20s). After internal variant typing, selected heading, measurement-bound, maximum and tilted-fill tests:23 passed (30.84s). Import direction:11 packages/37 inward edges;214 reachable modules, none orphaned. Unbreakable words, explicit forbid and content/non-slot candidates retain natural lines; short filled headings retain whole Scene/SVG bytes.

## Architecture conclusion

Layout closes immutable per-variant heading lines in the heading's own typography and stores the completed frame alongside the selected filled variant in a typed `_NoteVariant`; corner sizing reads named frame/filled fields instead of tuple indices. Pure fill arithmetic retains its actual measurement bound, including tilted rounds, without learning kind-frame ownership. Body, kind bar and stamp policies are unchanged. Scene/adapters only project completed text; no schema, project-specific tuning, source rewriting or compatibility alias was added.
