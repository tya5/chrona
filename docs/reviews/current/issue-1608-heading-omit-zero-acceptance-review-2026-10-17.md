<!-- chrona:literal-acceptance/v1 -->

# Issue #1608 — conditional heading parts

Source `fba7e51474bdd5d30db5ebaeb3bbcfe9b0e2c21c`, ready base `6bb56c205`.
[Design/architecture/implementation plan](https://github.com/tya5/chrona/issues/1608#issuecomment-6225977074)
and [frozen shared-schema integration](https://github.com/tya5/chrona/issues/1608#issuecomment-6226005448).
Ingress validates typed parts; Layout binds raw guards before measurement and
includes their late-count dependencies. No Scene or adapter policy is added.
Proposed three-design YAML adoption awaits the reviewer's acceptance in the PR.

## Literal issue acceptance

### Issue #1608

- Source: [Issue #1608](https://github.com/tya5/chrona/issues/1608)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests: a part with `omitWhenZero` is drawn at 1 and omitted at 0, and an unknown figure id is the existing figure diagnostic. | met | [Synthetic controls](../../../tests/integration/test_heading_omit_when_zero.py): whole/split heading 0/1, premeasurement omission, literal concatenation, unknown/non-count/group-scope guards and deferred guard-only reads at 0/3. Ten tests pass. | — |
| 2 | `--preset sunday`, `marquee` and `titlecard` on `examples/chrona-roadmap` (no groups) show no zero count, viewed as PNG. The #1582 CSV still shows `in three panels`. | met | Root rendered and viewed all four PNGs using the unchanged [roadmap Project](../../../examples/chrona-roadmap/project.yaml) and public [CSV fixture](https://github.com/tya5/chrona/issues/1582): no panels/acts/sections zero phrase remains; Sunday CSV retains `in three panels`. Local artifacts `/private/tmp/chrona-1608-visual-20261017/{roadmap-sunday,roadmap-marquee,roadmap-titlecard,csv-sunday}.png`. | — |
| 3 | Public SVG/Scene changes are listed with counts. | not met | Official CI before/after artifacts and per-output counts remain required; no generated evidence is authored. | — |

Validation: 46 heading/count/closure integration tests passed before adding the
additional deferred-zero case; all ten new controls then passed. Legacy focused
heading/contracts/count-format/content batch: 239 passed. Schema equivalence:
two explicitly reviewed widened sites, 36 equal schemas, 576 documents and 739
probes; L2+L3 20.6 seconds within its 60-second gate. Original shared definitions
remain frozen. Full CI and exact review-containing main three-OS release remain
open; this is not issue-release acceptance.
