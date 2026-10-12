<!-- chrona:literal-acceptance/v1 -->

# Issue1300 — revision stability acceptance

Partial implementation only; no full-issue or release acceptance.
WIP baseline READY9573049a; reconciled integration `ef85d5cc`.
[Current work/design record](https://github.com/tya5/chrona/issues/1300#issuecomment-6095643389).
Inspection, delta anchors and critical-first facts/order are independent of
the unimplemented protected feasibility pass and previous-Scene hints.

## Literal issue acceptance

### Issue #1300

- Source: [Issue1300](https://github.com/tya5/chrona/issues/1300)
- Observed: 2026-10-13

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A test pair: a plan and the same plan with every date shifted by the same amount (and, separately, with an unrelated object appended). The set of suppressed relations and each delta label's anchor side are equal between the two Scenes. | not met | [Positive translation/append controls](../../../tests/integration/test_revision_delta_anchor_stability.py) pass; they do not establish the general relation-local stability contract. | — |
| 2 | A test where a critical relation has a route: it is never suppressed. Where none exists, the distinct diagnostic is emitted. | not met | [Spec50](../../specification/50-constraint-driven-gantt-surface-quality.md#33-relations) scopes protected feasibility to suppress; completeness, implementation and impossibility evidence remain unfinished. Critical-first priority alone is not proof. | — |
| 3 | The trial's v1 → v2 pair keeps `spec-build` drawn. | met | [Actual supplied launch pair](../../../tests/integration/test_revision_launch_trial.py) passes through real Scene and SVG under the current default; no spatial suppressions. No protected-search claim. | — |
| 4 | `--emit-scene` output diffs line by line (one primitive per line), and its parsed content is unchanged. | met | [Formatter controls](../../../tests/unit/chrona/app/test_scene_inspection.py) and [actual CLI controls](../../../tests/cli/test_cli_scene_inspection.py) pass. Canonical/cache serialization and normal machine envelope stay unchanged. Current-head CI/release pending. | — |
| 5 | Do not edit `examples/**`. | met | [Published WIP scope](https://github.com/tya5/chrona/tree/wip/issue-1300-readable-inspection) contains implementation/tests/specification changes, not authored example edits. | — |

## Programme-level criteria (optional)

No new closing criteria; [hint contract clarification](https://github.com/tya5/chrona/issues/1300#issuecomment-6123808805) remains pending.

## Verification and architecture

Latest own-venv inspection/delta/priority/content/actual-launch suite:144 PASS3.69s.
One public46-context materializer batch completed: zero relation paths added,
removed or changed;20 Scene/SVG pairs byte-identical.26 Scenes add anchor
diagnostics; only3 SVGs change: aster overview1 delta, gallery-image-notes11
deltas plus one note (box/text), and gates1 delta. The note relocation follows
changed label obstacles, not a new annotation rule. Expose these side effects
in the eventual PR; do not refresh examples to hide them.
Evidence: `python -m tools.routing_performance_evidence --output-dir <empty-dir>
--jobs 4`; actual outputs retained in the issue work record.

Core critical facts stay in Presentation; Layout owns label obstruction/anchor
decisions and routing order; CLI only formats already-validated Scene data.
Protected quality/completeness is not enabled. Unsafe-mode supersession follows
published #1427, not an unapproved hint or compatibility policy.
