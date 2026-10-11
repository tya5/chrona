<!-- chrona:literal-acceptance/v1 -->

# Issue #1300 — revision stability acceptance

Inspection slice: `3a2f7aa59f4d6f6f97a700c2df8fb19fa43bfbf3`;
pre-code Spec08 design: `ba4ee5fac13251aa0f01f021f918ac6a6b6efd7d`.
[Current design/architecture/implementation plan](https://github.com/tya5/chrona/issues/1300#issuecomment-6095643389).
Routing and delta-label slices remain in design; no full-issue or release acceptance.

## Literal issue acceptance

### Issue #1300

- Source: [Issue #1300](https://github.com/tya5/chrona/issues/1300)
- Observed: 2026-10-11

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A test pair: a plan and the same plan with every date shifted by the same amount (and, separately, with an unrelated object appended). The set of suppressed relations and each delta label's anchor side are equal between the two Scenes. | not met | Routing/anchor contract and implementation still pending. | — |
| 2 | A test where a critical relation has a route: it is never suppressed. Where none exists, the distinct diagnostic is emitted. | not met | Critical-route existence/completeness design still pending. | — |
| 3 | The trial's v1 → v2 pair keeps `spec-build` drawn. | not met | Trial-pair routing implementation and verification still pending. | — |
| 4 | `--emit-scene` output diffs line by line (one primitive per line), and its parsed content is unchanged. | met | [Formatter identity/diff tests](../../../tests/unit/chrona/app/test_scene_inspection.py), [real draft CLI/artifact/result/write-guard tests](../../../tests/cli/test_cli_scene_inspection.py), and the immutable Context test in [test_cli.py](../../../tests/cli/test_cli.py) pass. Actual 1000-item Scene also preserves every parsed field and all 4460 complete primitive lines. Current-head CI/release remains pending. | — |
| 5 | Do not edit `examples/**`. | met | Slice changes only CLI/helper/tests/Spec08 and this review; no authored or generated example edits. | — |

Focused tests: 15 CLI/formatter tests, 3 unchanged Scene-output characterization
cases, and 6 canonical serialization/validation tests pass. Import direction:
11 packages/37 inward edges; 228 modules reachable, none orphaned.
CLI formatting follows canonical validation; it changes no layout, Scene data,
cache identity, normal stdout, or target bytes. Public materializers retain their
canonical serializer; the eventual current-head snapshot must confirm byte scope.
