<!-- chrona:literal-acceptance/v1 -->

# Issue1300 — revision stability acceptance

Partial implementation only; no full-issue or release acceptance.
Current feature base READY165587e6; final release pending for H1/H2.
[Current work/design record](https://github.com/tya5/chrona/issues/1300#issuecomment-6095643389).
Inspection, delta anchors and critical-first facts/order are independent of
the unimplemented protected feasibility pass. H1/H2 previous-Scene reuse is
locally verified, not a substitute for either original unfinished criterion.

## Literal issue acceptance

### Issue #1300

- Source: [Issue1300](https://github.com/tya5/chrona/issues/1300)
- Observed: 2026-10-13

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A test pair: a plan and the same plan with every date shifted by the same amount (and, separately, with an unrelated object appended). The set of suppressed relations and each delta label's anchor side are equal between the two Scenes. | not met | [Translation/append controls](../../../tests/integration/test_revision_delta_anchor_stability.py) verify actual delta sides and a nonempty explicit-suppress set with a painted blocker. They do not establish the general relation-local/processing-order contract. | — |
| 2 | A test where a critical relation has a route: it is never suppressed. Where none exists, the distinct diagnostic is emitted. | not met | [Spec50](../../specification/50-constraint-driven-gantt-surface-quality.md#33-relations) scopes protected feasibility to suppress; completeness, implementation and impossibility evidence remain unfinished. Critical-first priority alone is not proof. | — |
| 3 | The trial's v1 → v2 pair keeps `spec-build` drawn. | met | [Actual supplied launch pair](../../../tests/integration/test_revision_launch_trial.py) passes through real Scene and SVG under the current default; no spatial suppressions. No protected-search claim. | — |
| 4 | `--emit-scene` output diffs line by line (one primitive per line), and its parsed content is unchanged. | met | [Formatter controls](../../../tests/unit/chrona/app/test_scene_inspection.py) and [actual CLI controls](../../../tests/cli/test_cli_scene_inspection.py) pass. Canonical/cache serialization and normal machine envelope stay unchanged. Current-head CI/release pending. | — |
| 5 | Do not edit `examples/**`. | met | [Published WIP scope](https://github.com/tya5/chrona/tree/wip/issue-1300-readable-inspection) contains implementation/tests/specification changes, not authored example edits. | — |

## Additional mandatory hint acceptance

[Selected contract](https://github.com/tya5/chrona/issues/1300#issuecomment-6133101982)
supplements, and replaces none of, the original criteria.

| Literal acceptance | Disposition | Evidence |
| --- | --- | --- |
| The trial's v1 → v2 revision rendered with v1's Scene as hints keeps `spec-build` drawn with the same shape. | locally met; release pending | Actual trial test verifies translated point sequence, accepted/no-search receipt and emitted SVG. |
| A counter shows that only changed or new relations are searched. | locally met; release pending | Same-input10/10 routes accepted without search; changed-obstacle/validator failures fall through to search; typed per-instance dispositions partition the summary. Finite ordinary proposals are not falsely counted as search. |
| Without a hint, output is identical to without the feature. | locally met; release pending | All46 public contexts reproduce; best with a valid pin has identical Scene/SVG/receipts. No-hint rendering emits no hint diagnostics; immutable Context pin identity remains truthful. |

## Programme-level criteria (optional)

No additional programme gate replaces the original or mandatory hint criteria.

## Verification and architecture

Independent inspection/delta/priority release208cf1cc/38290538367 succeeded;
atomic recovery release8ce44cb0/38317097402 succeeded. H1 focused70 tests pass;
H2 focused100 tests pass. Own-venv `tools/regenerate_public_examples.py --check
--jobs 4` passes46 slides. The real immutable public materializer stages/reads
neutral artifact bytes exactly, preserves the prior file and emits hint receipts.
Schema equivalence passes; no historical verdicts or authored examples change.

PR1450 head a9d884c8 CI38324000103 initially failed three conformance checks:
the new hash-comparison classification, regenerated CLI reference and required
programme-section heading were missing. The classification follows the already
approved exact-byte pin contract; restore the reference and heading, not the
validators. Preview11780156269 confirms all92 public Scene/SVG files are
byte-identical; only two source diagnostic inventories change. Re-run exact-head
CI after the corrections; the original stability/critical rows remain not met.
The queued test-only stability evidence is included in this necessary correction
push, avoiding a second CI restart/publication cycle. CLI reference execution,
live classification and23 focused tooling tests pass locally.

Core critical facts stay in Presentation; Layout owns label obstruction/anchor
decisions and routing order; CLI only formats already-validated Scene data.
Protected quality/completeness is not enabled. Unsafe-mode supersession follows
published #1427. The [port correction](../../design/issue-1300-scene-hint-port-correction-2026-10-13.md)
does not infer missing historical egress IDs: current legal pairs are tried in
declared first-fit order through shared safety/quality validators. Scene/adapters
only project; no extra Scene schema field, heuristic cache or duplicate validator.
