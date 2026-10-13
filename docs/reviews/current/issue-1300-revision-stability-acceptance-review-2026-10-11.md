<!-- chrona:literal-acceptance/v1 -->

# Issue1300 — revision stability acceptance

H1/H2 is released; selected S/C completion is locally verified, release pending.
[PR1450](https://github.com/tya5/chrona/pull/1450) head239598cc passed
[CI38324544571](https://github.com/tya5/chrona/actions/runs/38324544571).
Synced public `01255938758e26af8416200d806c9b6a00b5be55` passed
[three-OS release38325655439](https://github.com/tya5/chrona/actions/runs/38325655439)
including full pytest/conformance/wheel, MCP floor and newest-Python reproduction.
[Current work/design record](https://github.com/tya5/chrona/issues/1300#issuecomment-6095643389).
Inspection, delta anchors and critical-first facts/order are independent of
the protected feasibility pass. [Reviewer6136355223](https://github.com/tya5/chrona/issues/1300#issuecomment-6136355223)
replaces unconditional S with hint-based stability and narrows C to the declared
finite search domain. Original wording remains below with explicit disposition.

## Literal issue acceptance

### Issue #1300

- Source: [Issue1300](https://github.com/tya5/chrona/issues/1300)
- Observed: 2026-10-13

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A test pair: a plan and the same plan with every date shifted by the same amount (and, separately, with an unrelated object appended). The set of suppressed relations and each delta label's anchor side are equal between the two Scenes. | deferred | Approved replacement: previous-Scene first-fit retains every revalidated trial route; hinted shift/append controls preserve route geometry, delta sides and suppressed identities. [Hinted trial](../../../tests/integration/test_revision_launch_trial.py) and [shift/append controls](../../../tests/integration/test_revision_delta_anchor_stability.py): six tests pass. No no-hint independence claim. Required release pending. | [Selected S6136355223](https://github.com/tya5/chrona/issues/1300#issuecomment-6136355223) |
| 2 | A test where a critical relation has a route: it is never suppressed. Where none exists, the distinct diagnostic is emitted. | deferred | Approved finite-domain guarantee under suppress: shared safety validators, uncapped simple-path exhaustion, measured quality fallback and SEARCH_DOMAIN_EXHAUSTED warning. [Finite-domain unit controls](../../../tests/unit/chrona/presentation/layout/test_protected_finite_route_domain.py) and [actual Scene/SVG controls](../../../tests/integration/test_critical_finite_domain_render.py) pass. No continuous-space claim; required release pending. | [Selected C6136355223](https://github.com/tya5/chrona/issues/1300#issuecomment-6136355223) |
| 3 | The trial's v1 → v2 pair keeps `spec-build` drawn. | met | [Actual supplied launch pair](../../../tests/integration/test_revision_launch_trial.py) passes through real Scene and SVG under the current default; no spatial suppressions. No protected-search claim. | — |
| 4 | `--emit-scene` output diffs line by line (one primitive per line), and its parsed content is unchanged. | met | [Formatter controls](../../../tests/unit/chrona/app/test_scene_inspection.py) and [actual CLI controls](../../../tests/cli/test_cli_scene_inspection.py) pass. Canonical/cache serialization and normal machine envelope stay unchanged; exact-head and synced-main release above succeed. | — |
| 5 | Do not edit `examples/**`. | met | [Published WIP scope](https://github.com/tya5/chrona/tree/wip/issue-1300-readable-inspection) contains implementation/tests/specification changes, not authored example edits. | — |

## Additional mandatory hint acceptance

[Selected hint contract](https://github.com/tya5/chrona/issues/1300#issuecomment-6133101982)
remains intact; the later6136355223 disposition changes the original S/C criteria,
not these three hint requirements.

| Literal acceptance | Disposition | Evidence |
| --- | --- | --- |
| The trial's v1 → v2 revision rendered with v1's Scene as hints keeps `spec-build` drawn with the same shape. | met | Actual trial test verifies translated point sequence, accepted/no-search receipt and emitted SVG; full release above passes. |
| A counter shows that only changed or new relations are searched. | met | Same-input10/10 routes accepted without search; changed-obstacle/validator failures fall through to search; typed per-instance dispositions partition the summary. Finite ordinary proposals are not falsely counted as search; full release passes. |
| Without a hint, output is identical to without the feature. | met | Preview11780366932 verifies92/92 public Scene/SVG files identical; only two source diagnostic inventories change. Best retains identical Scene/SVG/receipts; immutable pin identity remains truthful. Full release reproduces all46 contexts. |

## Programme-level criteria (optional)

No additional programme gate replaces the original or mandatory hint criteria.

## Verification and architecture

Selected S/C implementation: `2cf36485` plus the independently moving endpoint
join test correction. Focused routing/critical/hints/Scene/SVG suite138 PASS;
final protected controls8 PASS and strengthened S controls6 PASS. Initial
zero-bend render test was interrupted after65.53s; the published quality-floor
design correction replaces exhaustive rejected-safe-path enumeration with a
sound bound, not a larger quota. Independent Luna review found cross-pair rank
and first-fit fallback-order defects; both have real regression tests and fixes.
Local conformance passes every check except stale generated diagnostic inventory;
CI must regenerate it in the shared snapshot. The46-slide batched materializer
check passed before the final ordering/diagnostic refinements; exact-head CI
snapshot must confirm the final bytes. Do not close until that and full release.

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
CI after the corrections succeeded; the original stability/critical rows remain not met.
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
