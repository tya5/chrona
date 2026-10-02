<!-- chrona:literal-acceptance/v1 -->

# Issue #881: post-review hygiene leftovers, acceptance review

Source: [Issue #881](https://github.com/tya5/chrona/issues/881), observed 2026-10-02 (body last updated 2026-10-02T04:39:28Z; the one comment on it is this work's claim and decisions, re-fetched before writing this review, no row added). The three rows are the three literal acceptance bullets of the body. Work record: [issue-881-hygiene-leftovers-2026-10-02.md](../planning/issue-881-hygiene-leftovers-2026-10-02.md) (baseline, decisions D1 to D3, plan).

Slices: work record [PR #887](https://github.com/tya5/chrona/pull/887) (`747cb1b9`); S1, helper removal and two description edits [PR #892](https://github.com/tya5/chrona/pull/892) (`3c226937`). Owner decisions with options, choice, reason and reversal: [issue comment](https://github.com/tya5/chrona/issues/881#issuecomment-5945706669).

## Literal issue acceptance

### Issue #881

- Source: [Issue #881](https://github.com/tya5/chrona/issues/881)
- Observed: 2026-10-02

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Items 1 and 2 are done. | narrowed | Item 2 is done: `_assert_member_end_gap` and its call are removed from [`test_readable_defaults.py`](../../../tests/integration/test_readable_defaults.py) ([PR #892](https://github.com/tya5/chrona/pull/892)); the both-sides check is [`test_member_label_association.py`](../../../tests/acceptance/output/test_member_label_association.py), which still passes on every public Scene. Item 1 is narrowed on purpose: the owner decided in [#715](https://github.com/tya5/chrona/issues/715) (decision B, 2026-10-01) to keep `icon-catalog-v0.3` for the bundled vector-only Material catalog, so retiring it or moving its `address` to `storeAddress` contradicts that decision. The narrower action: the v0.3 `address` description in [`icon-catalog-v0.3.schema.yaml`](../../../schemas/icon-catalog-v0.3.schema.yaml) now says the loose pattern is deliberate and points to the strict v0.4 grammar; the inventory entry keeps its `reason` ([`schema-inventory-v0.1.yaml`](../../../schemas/schema-inventory-v0.1.yaml)). `python -m tools.schema_equivalence --base-rev origin/main` passed on the description edit. | [#715](https://github.com/tya5/chrona/issues/715), decision B, with the `removalSlice` in the inventory entry |
| 2 | Item 3 is documented now, and the rename is either scheduled or declined with a reason. | met | Documented: [Spec 50](../../specification/50-constraint-driven-gantt-surface-quality.md) already states that one `maxEndGapEm` value bounds the end-side gap, the nearest-perimeter association gap and the final-rung gap; the [`layout-profile-v0.10`](../../../schemas/layout-profile-v0.10.schema.yaml) description now names the same three bounds ([PR #892](https://github.com/tya5/chrona/pull/892), schema equivalence PASS). Rename declined with reasons (public knob, an alias gives two spellings and a precedence rule, a new Layout Profile version moves every profile for a name) and the reversal (an additive `maxReachEm` in place under Spec 56 section 3.2, `maxEndGapEm` kept as the legacy spelling): work record D2 and the [issue comment](https://github.com/tya5/chrona/issues/881#issuecomment-5945706669). | — |
| 3 | Item 4 is decided and recorded. | met | Decision: keep `integrity: optional` for `chrona init --example`; examples are demos and `chrona init` is the starter, and pinning reverses ADR-0030 and rewrites 191 unpinned references. Options, choice, reason and reversal in work record D3 and the [issue comment](https://github.com/tya5/chrona/issues/881#issuecomment-5945706669). No code change; the existing comment in `.chrona/store.yaml` and the first-project guide already say the exception covers the example corpus only ([`local_authoring.py`](../../../src/chrona/usecases/local_authoring.py)). | — |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

No behaviour, schema accepted set or ownership changed: the schema edits are descriptions only, and the removed helper was a strictly weaker duplicate of a check that runs on every public Scene. No new test was added, so there is no mutation check to run; the removed check is covered by the association acceptance test, which has a synthetic both-sides case. Row 1 is `narrowed` and not `met`: item 1 as worded (retire v0.3 or re-pattern its address) is not done, by owner decision; the successor is the recorded #715 decision, not a new issue.

Exact review-bearing-main three-OS CI and newest-Python materializer run must pass before closing #881; record that run in the issue closing comment.
