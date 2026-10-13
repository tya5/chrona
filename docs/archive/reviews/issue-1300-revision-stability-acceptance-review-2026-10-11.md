<!-- chrona:literal-acceptance/v1 -->

# Issue1300 — revision stability acceptance

#1300 is closed after exact-main acceptance. H1/H2, S and C are complete under
the approved6136355223 dispositions. Original literal criteria1 and2 remain
deferred because their approved replacements define the accepted evidence.
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
| 1 | A test pair: a plan and the same plan with every date shifted by the same amount (and, separately, with an unrelated object appended). The set of suppressed relations and each delta label's anchor side are equal between the two Scenes. | deferred | Approved S replacement: with the prior Scene, first-fit retains each revalidated v1→v2 trial route; hinted shift/append controls retain route geometry and delta anchor sides and compare suppressed relation identities. [Hinted trial](../../../tests/integration/test_revision_launch_trial.py) and [shift/append controls](../../../tests/integration/test_revision_delta_anchor_stability.py) pass in the final focused batch. Exact-main release succeeded. | [Selected S6136355223](https://github.com/tya5/chrona/issues/1300#issuecomment-6136355223) |
| 2 | A test where a critical relation has a route: it is never suppressed. Where none exists, the distinct diagnostic is emitted. | deferred | Approved C replacement: under suppress, exhaust the declared finite port/event/simple-path domain with the existing safety validators; select a measured safe fallback when quality rejects all safe routes, and emit `SEARCH_DOMAIN_EXHAUSTED` when no accepted route exists. [Finite-domain unit controls](../../../tests/unit/chrona/presentation/layout/test_protected_finite_route_domain.py) and [actual Scene/SVG controls](../../../tests/integration/test_critical_finite_domain_render.py) pass in the focused batch. Exact-main release succeeded. | [Selected C6136355223](https://github.com/tya5/chrona/issues/1300#issuecomment-6136355223) |
| 3 | The trial's v1 → v2 pair keeps `spec-build` drawn. | met | [Actual supplied launch pair](../../../tests/integration/test_revision_launch_trial.py) passes through real Scene and SVG under the current default; no spatial suppressions. | — |
| 4 | `--emit-scene` output diffs line by line (one primitive per line), and its parsed content is unchanged. | met | [Formatter controls](../../../tests/unit/chrona/app/test_scene_inspection.py) and [actual CLI controls](../../../tests/cli/test_cli_scene_inspection.py) pass. Canonical/cache serialization and normal machine envelope stay unchanged; exact-head and synced-main release above succeed. | — |
| 5 | Do not edit `examples/**`. | met | [Permanent implementation diff](https://github.com/tya5/chrona/compare/9c1cb8b9...9e3d2e73) contains implementation, tests and specification changes; no authored example edits were made. | — |

## Additional mandatory hint acceptance

[Selected hint contract](https://github.com/tya5/chrona/issues/1300#issuecomment-6133101982)
remains intact; the later6136355223 disposition changes the original S/C criteria,
not these three hint requirements.

| Literal acceptance | Disposition | Evidence |
| --- | --- | --- |
| The trial's v1 → v2 revision rendered with v1's Scene as hints keeps `spec-build` drawn with the same shape. | met | Actual trial test verifies the accepted revalidated route geometry, its endpoint instances, the accepted receipt and emitted SVG; exact-main release above passes. |
| A counter shows that only changed or new relations are searched. | met | Same-input10/10 routes are accepted without search; changed-obstacle/validator failures fall through to search; typed per-instance dispositions partition the summary. Finite ordinary proposals are not falsely counted as search; exact-main release passes. |
| Without a hint, output is identical to without the feature. | met | Released H1/H2 compatibility controls include preview11780366932 (92/92 public Scene/SVG files identical; diagnostic inventory changes only) and final reproduction of all46 contexts. Exact-main release passes. |

## Programme-level criteria (optional)

No additional programme gate replaces the original or mandatory hint criteria.

## Verification and architecture

Implementation: [PR1453](https://github.com/tya5/chrona/pull/1453), final
head9e3d2e73, merged publice8a53082. [Exact-head CI38336753803](https://github.com/tya5/chrona/actions/runs/38336753803)
succeeded: all three pytest shards, conformance, MCP, newest-Python reproduction
and derived-ready. Published main `aea06f4b6b311c1863a9d1aaefb7256e010bf21b`
passed [release38339181830](https://github.com/tya5/chrona/actions/runs/38339181830)
with all five required jobs; issue1300 is closed.

Focused routing/critical/hint/Scene/SVG batch138 PASS; final counter/message/
hint batch57 PASS. Real rendered controls cover safe over-quality routes,
domain exhaustion, actual search receipts and reanchored joins. Independent
reviews found rank and first-fit-order defects; regression tests cover the fixes.
The sound endpoint quality floor avoids pointless zero-bend enumeration without
weakening safety. Uncapped simple-path work can still be exponential.

Failure disposition: initial CI38335371719 failed one missing curated warning
sentence, fixed in diagnostic_messages.py with a finite-domain regression.
Corrected CI38336078901 and final-head CI38336753803 succeeded. Final artifact
11785377450 has101 managed paths, no retirements and92/92 identical public
Scene/SVG bytes; only the generated diagnostic inventory changes
([final audit](https://github.com/tya5/chrona/pull/1453#issuecomment-6136656126)).
No authored examples change.

Architecture: scheduler owns immutable critical facts; ingress owns pinned
prior-Scene integrity; Layout owns matching, reanchoring, completed safety,
quality, finite-domain feasibility and truthful counters. Scene/adapters only
project. Other unroutable modes retain1427; ordinary bounded search and best
ignoring hints remain unchanged. The [port correction](../../design/issue-1300-scene-hint-port-correction-2026-10-13.md)
does not infer missing egress IDs or add a duplicate geometry validator.
