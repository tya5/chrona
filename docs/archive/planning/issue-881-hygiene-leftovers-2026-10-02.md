# Work Record: post-review hygiene leftovers (#881)

Issue: [#881](https://github.com/tya5/chrona/issues/881), observed 2026-10-02 (body only, no comments before this work). One living record for baseline, decisions, plan and evidence. This record changes no schema and no product code by itself.

## Baseline (main `72192057`)

Published and verified:

- `schemas/icon-catalog-v0.3.schema.yaml` `rasterSource.address` keeps the traversal-free pattern; v0.4 uses `common#/$defs/storeAddress`. The inventory entry for v0.3 is `transitioning` and already carries a `reason` (PR #804): kept for the bundled Material catalog on purpose, owner decision 2026-10-01 in [#715](https://github.com/tya5/chrona/issues/715) (decision B; work record `issue-715-schema-parts-leftovers-plan-2026-10-01.md`).
- `_assert_member_end_gap` in `tests/integration/test_readable_defaults.py` checks the end-side gap only and is called once. `tests/acceptance/output/test_member_label_association.py` checks every emitted member label of every public Scene against its own mark on both sides (gap at most 2 em, `hostPlacementId` identity) and has a synthetic both-sides test.
- Spec 50 (`reviewSurface.memberNames`) already states that `maxEndGapEm` bounds the end-side gap, the nearest-perimeter association gap and the final-rung gap. The `layout-profile-v0.10` schema description states only the reach and its extension by the last own mark.
- `chrona init --example` writes `integrity: optional` with a comment citing ADR-0030 (#727, option 3); the first-project guide documents it; a Store you create yourself and an omitted `integrity` stay `required` (#723).

Unverified until the slice runs: the exact `schema_equivalence` result for the two description edits.

## Literal acceptance and decisions

| # | #881 acceptance row | Decision | Slice |
| ---: | --- | --- | --- |
| 1 | Items 1 and 2 are done. | Item 2: remove the helper and its call; the association acceptance test is the stronger check. Item 1: the owner decided in #715 (B) to keep v0.3 for the bundled catalog, so retiring or re-patterning it contradicts that decision. Narrower action: keep v0.3, state in the `address` description that the loose pattern is deliberate and why; the inventory `reason` stays. Row is `narrowed`, successor #715. | S1 |
| 2 | Item 3 is documented now, and the rename is either scheduled or declined with a reason. | Document the full meaning in the schema description (Spec 50 already has it). Rename declined (D2). | S1 |
| 3 | Item 4 is decided and recorded. | Keep `integrity: optional` for the example Store (D3). Recorded here and on the issue. | this PR |

## Design

**D1 (item 1). v0.3 `address` stays loose.** Applying `storeAddress` in place (Spec 56 section 3.2) needs v0.3's consumer to check the address at parse time, which it does not; the bundled catalog is vector-only, so the pattern is never exercised by shipped data. A description-only edit changes what no document accepts. The `address` description names the deliberate looseness and points to the strict v0.4 rule. No new successor issue: #715 holds the owner decision and the inventory entry holds the `removalSlice`.

**D2 (item 3). `maxEndGapEm` keeps its name; the meaning is documented.** Options: (a) document only; (b) rename to `maxReachEm` as an additive alias in the current Layout Profile version, `maxEndGapEm` staying accepted; (c) a new Layout Profile version with the rename. Chosen: (a). Why: the knob is public and used by user profiles and tests; an alias gives two spellings of one value and needs a precedence and conflict rule for no behaviour change; (c) forces every profile to move for a name. Spec 50 and the schema description state that one value bounds the end-side gap, the association distance on both sides and the final-rung gap. Reversal: add `maxReachEm` as an optional property in the current version (behaviour-preserving, in place), make "both set and different" a schema error, run `python -m tools.schema_equivalence --base-rev origin/main`, and document `maxEndGapEm` as the legacy spelling. Not scheduled; revisit if a second reach-like knob appears.

**D3 (item 4). The example Store stays `optional`.** Options: (1) pin the example Contexts (reverses ADR-0030, rewrites 191 unpinned references and every canonical Context); (2) keep `optional`; (3) `required` plus the opt-out flag in the docs. Chosen: (2). Why: the guide and README present `init --example` as a runnable demo and `chrona init` as the starter for a real project; nothing positions an example as a template, and pinning is a design change that buys a default no demo needs. Reversal: if examples are ever offered as project templates, write `required` from `init --example` and pin the Contexts it copies under a new ADR. The comment in `.chrona/store.yaml` already says the exception is for the example corpus. No code or guide change.

## Implementation plan

- **S1** (one PR): delete `_assert_member_end_gap` and its call; edit the `maxEndGapEm` description in `layout-profile-v0.10.schema.yaml` and the `address` description in `icon-catalog-v0.3.schema.yaml` (in place, description only). No new test: a removal and two descriptions. Evidence: `python -m tools.schema_equivalence --base-rev origin/main` shows no accepted-set change; conformance; the association acceptance test and `test_readable_defaults.py` still pass.
- **S2**: acceptance review `docs/reviews/current/issue-881-*`, then the exact-main three-OS run before closing.
