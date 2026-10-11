<!-- chrona:literal-acceptance/v1 -->

# Issue #1300 — revision stability acceptance

Inspection slice: `3a2f7aa59f4d6f6f97a700c2df8fb19fa43bfbf3`;
pre-code Spec08 design: `ba4ee5fac13251aa0f01f021f918ac6a6b6efd7d`.
[Current design/architecture/implementation plan](https://github.com/tya5/chrona/issues/1300#issuecomment-6095643389).

Independent critical-priority slice: pre-code Spec50 `7acdee7c`, code `f5e42d04`.
Layout's typed ordering helper processes critical facts first while preserving
within-class arrival/tie/cycle order and original declaration indices. Actual
scheduler→Layout calls and Scene/SVG declaration order are verified; ordinary
safety/quality/search predicates are unchanged. Priority/normalization/delta
batch84 PASS1.67s; priority/fan-in/node-approach/terminal/reduction batch77
PASS2.83s; imports and Layout float checks PASS. This does not establish
protected existence, enable quality fallback or satisfy literal rows1–3.
Public WIP: `7afdfc86d523701d1801ee92176d0c850db06909`, containing trusted
READY `fa862e40745aa134198dfe070aa347c451dd7ffe`.
Delta-label code: `f498467f`; pre-code Specs33/50: `42092313`, `38ea6e96`.
Protected routing remains in design; no full-issue or release acceptance.

## Literal issue acceptance

### Issue #1300

- Source: [Issue #1300](https://github.com/tya5/chrona/issues/1300)
- Observed: 2026-10-11

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A test pair: a plan and the same plan with every date shifted by the same amount (and, separately, with an unrelated object appended). The set of suppressed relations and each delta label's anchor side are equal between the two Scenes. | not met | [Real default-preset Scene/SVG translation and unrelated-append test](../../../tests/integration/test_revision_delta_anchor_stability.py) passes; broader [relation-local routing contract](https://github.com/tya5/chrona/issues/1300#issuecomment-6095643389) remains unimplemented. This positive pair is not proof of general route stability. | — |
| 2 | A test where a critical relation has a route: it is never suppressed. Where none exists, the distinct diagnostic is emitted. | not met | [Owner-approved critical-only quality exception](https://github.com/tya5/chrona/issues/1300#issuecomment-6109829875) is recorded in [Spec50](../../specification/50-constraint-driven-gantt-surface-quality.md#33-relations); protected feasibility/completeness and its tests remain pending. | — |
| 3 | The trial's v1 → v2 pair keeps `spec-build` drawn. | not met | [Supplied trial and required result](https://github.com/tya5/chrona/issues/1300) still require protected-routing implementation and actual pair verification. | — |
| 4 | `--emit-scene` output diffs line by line (one primitive per line), and its parsed content is unchanged. | met | [Formatter identity/diff tests](../../../tests/unit/chrona/app/test_scene_inspection.py), [real draft CLI/artifact/result/write-guard tests](../../../tests/cli/test_cli_scene_inspection.py), and the immutable Context test in [test_cli.py](../../../tests/cli/test_cli.py) pass. Actual 1000-item Scene also preserves every parsed field and all 4460 complete primitive lines. Current-head CI/release remains pending. | — |
| 5 | Do not edit `examples/**`. | met | [Delta implementation scope](https://github.com/tya5/chrona/commit/f498467f) and [inspection implementation scope](https://github.com/tya5/chrona/commit/3a2f7aa59f4d6f6f97a700c2df8fb19fa43bfbf3) contain no example edits. Adopted main contains generated evidence, not authored changes for this issue. | — |

## Programme-level criteria (optional)

Latest combined delta/label/window/chip/route-label/inspection regression batch:
96 tests pass; Layout floating-point checker passes. Canonical end/start/above/
below delta placement uses typed canonical-slot obstruction, including actual
blocker IDs and bounds-only failures; same-side displacement remains diagnosed.
No member-name policy or adapter placement is added.

Earlier focused tests: 15 CLI/formatter tests, 3 unchanged Scene-output characterization
cases, and 6 canonical serialization/validation tests pass. Import direction:
11 packages/37 inward edges; 228 modules reachable, none orphaned.
CLI formatting follows canonical validation; it changes no layout, Scene data,
cache identity, normal stdout, or target bytes. Public materializers retain their
canonical serializer; the eventual current-head snapshot must confirm byte scope.
