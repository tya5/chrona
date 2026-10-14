<!-- chrona:literal-acceptance/v1 -->

# Issue #1478 — Summary Panel Title Acceptance Review

- Implementation: `691d94ab13d44c6fcbb81ce0a62288c5f2c7d863` (`bf6e96a8` applied after normative Spec 06 commit `ad1dd5a9`)
- Public fixture source: PR #1476 commit `c2ddb68f647b566a4c51c25f2fe0735fbb664d04`

## Literal issue acceptance

### Issue #1478

- Source: [Issue #1478](https://github.com/tya5/chrona/issues/1478)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The halcyon Title Card is byte-identical. | met | The [public materializer](../../../tools/regenerate_public_examples.py) passed in check mode. Reproduced Scene SHA-256 `340240745dbf914e948424dfcae9157593db5edc060661343ffe921444b96b1b` and SVG SHA-256 `3b03af4dae4ad35404d437578fedece7ee60f685da26d2aec161b8a721632640` match the immutable fixture's [Scene](https://github.com/tya5/chrona/blob/c2ddb68f647b566a4c51c25f2fe0735fbb664d04/examples/halcyon-1/generated/23-titlecard.scene.json) and [SVG](https://github.com/tya5/chrona/blob/c2ddb68f647b566a4c51c25f2fe0735fbb664d04/examples/halcyon-1/generated/23-titlecard.svg). | — |
| 2 | PR #1476's roadmap Title Card can read e.g. `RC まで`. | met | Ran the [public materializer](../../../tools/regenerate_public_examples.py) on two disposable copies of the [immutable roadmap fixture](https://github.com/tya5/chrona/tree/c2ddb68f647b566a4c51c25f2fe0735fbb664d04/examples/chrona-roadmap). In the override copy only, added `wording.summary.countdown.title: RC まで`; generated Scene and SVG both contain `RC まで`. Override Scene/SVG SHA-256: `922ff7b611ea8e38bcea148948648560a60c7c568bfd218997992b9dc0540f15` / `d69385c8b383c260e60f3c454a6d3ace408a1d3b3ebfeaf337b23a656defc4ad`. The baseline copy rendered separately; neither source fixture was edited. | — |
| 3 | Test for override and for an unknown panel. | met | [Profile connection tests](../../../tests/unit/chrona/presentation/review/test_profile_connections.py), including `test_summary_wording_overrides_panel_title_without_mutating_profile_and_checks_collisions`, cover override/unknown panel/escaped pointer/collisions. Focused presentation94 PASS; schema/annotation128 PASS; schema equivalence L2/L3 PASS. | — |
| 4 | Do not edit `examples/**`. | met | [Implementation commit](https://github.com/tya5/chrona/commit/691d94ab13d44c6fcbb81ce0a62288c5f2c7d863) and `git diff --name-only 7a08f0c03b878a747465360c217a00d97e303b59..HEAD` contain no `examples/**` path. The public fixture remained clean after materialization. | — |

## Programme-level criteria (optional)

None.

## Architecture conclusion

The View owns project wording. Profile closure resolves `<panel-id>.title` in the existing summary-wording namespace before rendering, preserves the authored profile and stable panel identity, and rejects unknown or ambiguous joined keys at the View pointer. The shared schema changes descriptions only. The implementation commit and local acceptance evidence are ready for PR review; CI and the release snapshot are still pending, so this review does not close the issue.
