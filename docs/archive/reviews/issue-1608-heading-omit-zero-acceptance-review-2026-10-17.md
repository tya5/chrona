<!-- chrona:literal-acceptance/v1 -->

# Issue #1608 — conditional heading parts

Heading source `fba7e5147`, face-closure correction `40380c7c1`, whole-title
omission completion `57d3e3d98`, reconciled with ready base `3e79f971a`.
Final PR head `edc88039d` passed [all PR checks](https://github.com/tya5/chrona/actions/runs/38984444157).
Its [artifact12082313818](https://github.com/tya5/chrona/actions/runs/38984444157/artifacts/12082313818)
contains 50 unchanged SVGs and 44 unchanged Scenes; six Scene changes are
provenance-only, with no added or retired primitives, routes or labels. The
exact review-containing main `8c4d17f917b29600fd72e5b514ad06d31242ca33` passed
[release38985610444](https://github.com/tya5/chrona/actions/runs/38985610444)
on all three OSes, conformance, wheel/smoke, MCP floor and newest-Python
reproduction. Issue #1608 closed at 2026-10-17 00:52:51 UTC.
[Design/architecture/implementation plan](https://github.com/tya5/chrona/issues/1608#issuecomment-6225977074)
and [frozen shared-schema integration](https://github.com/tya5/chrona/issues/1608#issuecomment-6226005448).
Ingress validates typed parts; Layout binds raw guards before measurement and
includes their late-count dependencies. No Scene or adapter policy is added.
The reviewer [accepted all three shared-design YAML declarations and disclosed
public deltas](https://github.com/tya5/chrona/pull/1621#issuecomment-6226945825).
The [integration correction](https://github.com/tya5/chrona/issues/1608#issuecomment-6226118452)
shares existing Layout fallback-run completion with measured sources and carries
those facts through independent heading and network projections. It changes no
geometry or Latin-only serialization. [Synthetic controls](../../../tests/integration/test_heading_face_closure.py)
verify the exact Japanese/Latin run identities and widths, whole/split heading
equivalence, and both network title/node producers. No fallback is selected by
Scene or an adapter.

## Literal issue acceptance

### Issue #1608

- Source: [Issue #1608](https://github.com/tya5/chrona/issues/1608)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests: a part with `omitWhenZero` is drawn at 1 and omitted at 0, and an unknown figure id is the existing figure diagnostic. | met | [Synthetic controls](../../../tests/integration/test_heading_omit_when_zero.py): all three members under whole/split heading at 0/1, no blank title placeholder, remaining member identity, premeasurement omission, literal concatenation, unknown/non-count/group-scope guards and deferred guard-only reads at 0/3. Twenty tests pass. | — |
| 2 | `--preset sunday`, `marquee` and `titlecard` on `examples/chrona-roadmap` (no groups) show no zero count, viewed as PNG. The #1582 CSV still shows `in three panels`. | met | Root rendered and viewed all four PNGs using the unchanged [roadmap Project](../../../examples/chrona-roadmap/project.yaml) and public [CSV fixture](https://github.com/tya5/chrona/issues/1582): no panels/acts/sections zero phrase remains; Sunday CSV retains `in three panels`. Local artifacts `/private/tmp/chrona-1608-visual-20261017/{roadmap-sunday,roadmap-marquee,roadmap-titlecard,csv-sunday}.png`. | — |
| 3 | Public SVG/Scene changes are listed with counts. | met | Final [artifact12082313818](https://github.com/tya5/chrona/actions/runs/38984444157): 109 before/after paths, none added/retired. All 50 SVGs and 44 Scenes are byte-identical; six Scene changes are provenance-only. No primitives, labels or routes were added or retired. [PR #1621](https://github.com/tya5/chrona/pull/1621) lists the counts; no generated evidence is authored. | — |

## Programme-level criteria (optional)

The accepted shared-design YAML was reviewed; the exact final product head and
review-containing main release passed. No acceptance item is deferred.
