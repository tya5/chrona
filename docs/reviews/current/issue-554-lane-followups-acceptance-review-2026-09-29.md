<!-- chrona:literal-acceptance/v1 -->

# Issue #554 — lane follow-ups acceptance review

Product base: [PR #589](https://github.com/tya5/chrona/pull/589), merged as `8f86014f793d49a2f87501ab6e8ef07c7aba0b03`. The selected design, architecture check, correction and slice plan are in the [living work record](../../planning/active/issue-554-lane-followups-work-record-2026-09-29.md); Specs 08/30/38/50 are the normative contracts. Rows 1, 3 and 4 were implemented earlier in PR #565 and rechecked on this base. #497 legend truncation is separate.

## Literal issue acceptance

### Issue #554

- Source: [Issue #554](https://github.com/tya5/chrona/issues/554)
- Observed: 2026-09-29

The [owner's bounded-distance scope decision](https://github.com/tya5/chrona/issues/554#issuecomment-5889528211) is included.

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Lane labels show a title: the group title, the member's title for one-item lanes, or a declared lane title. No raw id reaches the rendered table. A constant `Items` column is omitted or declared. | met | [03 table test](../../../tests/integration/test_readable_defaults.py), [02 public SVG](../../../examples/halcyon-1/generated/02-programme-board.svg), [03 public Scene](../../../examples/halcyon-1/generated/03-launch-campaign.scene.json): titled lanes, 03 omits constant `Items`; raw keys remain identities only. | — |
| 2 | A name placed off its own mark (stagger or displaced) either stays within a bounded distance of the mark or gets a leader to it. A Scene check measures label-to-mark distance for every member label, on both sides. | met | [Public and synthetic Scene checks](../../../tests/acceptance/output/test_member_label_association.py) measure every emitted member Text against its exact planned/actual mark within `2 × fontSize`, including start/end and folded group-header points; [lane/Theme integration](../../../tests/integration/test_lane_theme_handoff.py) checks host identity and no member leader. Layout limits lane displacement to one measured adjacent step, then tries declared fallback or source-keyed counted suppression. Public 02/11/12 each have 20 shown + 6 counted suppressed = 26, zero member leaders; their [02 SVG](../../../examples/halcyon-1/generated/02-programme-board.svg), [11 SVG](../../../examples/halcyon-1/generated/11-overlay-briefing.svg), and [12 SVG](../../../examples/halcyon-1/generated/12-glyph-gates.svg) were inspected. | — |
| 3 | Every warning printed by the CLI for a render is also in that render's Scene `diagnostics`, and a test asserts that the two sets are equal. | met | [Attached-milestones CLI test](../../../tests/cli/test_cli.py) compares warning inventories with multiplicity to the serialized Scene diagnostics. The two `W_LAYOUT_LABEL_OVERFLOW` warnings are present in both the CLI and Scene. | — |
| 4 | The weekend fill and its legend key pass the starter perceptibility gate. | met | [Starter perceptibility tests](../../../tests/unit/tools/test_check_starter_perceptibility.py) validate chart/key paint against serialized SVG; [public HALCYON SVG](../../../examples/halcyon-1/generated/02-programme-board.svg) retains the shared closed-day treatment. | — |

## Programme-level criteria (optional)

### Verification and generated evidence

- Local focused verification: 253 passed, 25 skipped in the relevant Layout/Scene/schema/integration/output/CLI set; seven targeted readable-default tests passed. All 29 public materializers regenerated as one batch and `--check --jobs 4` passed; conformance passed. The starter gate and raw SVG output were inspected, not inferred solely from Scene. No Project/Actual data changed.
- [PR CI run 36571770643](https://github.com/tya5/chrona/actions/runs/36571770643): conformance, three pytest shards and newest-Python reproduction passed. An earlier red run contained obsolete 26/26 count assertions in readable-default tests; these were changed to the owner-approved shown-plus-counted-suppression invariant before the green run.
- [Exact product-main CI run 36572591358](https://github.com/tya5/chrona/actions/runs/36572591358) passed three-OS full pytest/conformance/wheel and newest-Python public reproduction on `8f86014f`. Exact review-bearing-main CI is **PENDING**; PR CI cannot substitute for it.
- Generated diff reviewed as a batch: affected public Scene files, SVGs (including 02/11/12) and three diagnostic reports were regenerated. The 02/11/12 change from 26 shown to 20 shown + 6 source-keyed suppressed is intentional and visible; no Project/Actual or Theme file changed. The Scene v0.6/v0.7 lane-obstacle `leader-route` member extension and `memberLabelLeader` semantic were retired together; unrelated annotation routing remains. Old member-leader Scenes are intentionally incompatible without a version bump, as recorded in the design.
- Optional HALCYON Theme probes at 13px body size and 24px large spacing remained materializable but gained at most one visible name on each board and did not improve the crowded SVG enough to publish. Gallery-target tuning belongs to [#575](https://github.com/tya5/chrona/issues/575), using project YAML rather than core special cases; it is not a missing literal #554 criterion.

## Architecture conclusion

View declares sides and fallback, Theme supplies typography, Layout completes measured bounds, exact-mark association and suppression, Scene projects the completed text and shared warning ledger, and SVG serializes without choosing geometry. Synthetic and public tests cover this boundary. No corpus-specific branch, route mechanism, or Project/Actual edit was added. **Release acceptance remains pending** until this review is published and the exact review-bearing `main` CI matrix, wheel, conformance and newest-Python materializer gate pass.
