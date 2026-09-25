<!-- chrona:literal-acceptance/v1 -->

# Release Review — Exact Multi-Face Font Measurement (#448)

## Literal issue acceptance

### Issue #448

- Source: [Issue #448](https://github.com/tya5/chrona/issues/448)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Every text placement's `assetIdentity` is the file declared for its `(family, weight)`. | met | [identity audit](../../diagnostics/presentation-font-identity.md); [checker](../../../tools/presentation_font_identity.py) | — |
| 2 | No weight-700 placement in corpus is measured with 400 face. | met | [identity audit](../../diagnostics/presentation-font-identity.md) reports zero weight-700 regular-face identities; [negative test](../../../tests/unit/tools/test_presentation_font_identity.py) | — |
| 3 | `chrona render --system-fonts` accepts a Theme with two weights of one installed family, and measures each with its own face. | met | [draft closure/render test](../../../tests/unit/chrona/presentation/model/test_draft_closure.py); [exact catalog implementation](../../../src/chrona/presentation/fonts/system.py) | — |

## Programme-level criteria (optional)

The checked audit has 1,272 completed text findings, including 101 weight-700
placements, and zero errors. Draft font discovery creates a finite exact
catalog before Layout; the PNG adapter receives the matching identity-pinned
file tuple.

## Architecture conclusion

Immutable and draft rendering now share the same `(family, weight)` metric
selection abstraction. Layout owns face selection before geometry, Scene
transports the completed identity, and renderers receive only a closed file
set. No regular-face default or host fallback remains in the multi-weight
draft path.
