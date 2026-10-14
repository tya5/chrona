# Issue #1478 — Summary Panel Title Acceptance Review

- Source: [Issue #1478](https://github.com/tya5/chrona/issues/1478)
- Implementation: `691d94ab13d44c6fcbb81ce0a62288c5f2c7d863` (`bf6e96a8` applied after normative Spec 06 commit `ad1dd5a9`)
- Public fixture source: PR #1476 commit `c2ddb68f647b566a4c51c25f2fe0735fbb664d04`
- Observed: 2026-10-14

## Literal issue acceptance

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The halcyon Title Card is byte-identical. | met | The public HALCYON `titlecard` materializer passed in check mode. Reproduced Scene SHA-256 `340240745dbf914e948424dfcae9157593db5edc060661343ffe921444b96b1b` and SVG SHA-256 `3b03af4dae4ad35404d437578fedece7ee60f685da26d2aec161b8a721632640` exactly match `examples/halcyon-1/generated/23-titlecard.scene.json` and `.svg` in the immutable PR #1476 fixture. | — |
| 2 | PR #1476's roadmap Title Card can read e.g. `RC まで`. | met | Ran the public `roadmap-titlecard` materializer on two disposable copies of the PR #1476 `chrona-roadmap` fixture. In the override copy only, added `wording.summary.countdown.title: RC まで`; generated Scene and SVG both contain `RC まで`. Override Scene/SVG SHA-256: `922ff7b611ea8e38bcea148948648560a60c7c568bfd218997992b9dc0540f15` / `d69385c8b383c260e60f3c454a6d3ace408a1d3b3ebfeaf337b23a656defc4ad`. The baseline copy rendered separately; neither source fixture was edited. | — |
| 3 | Test for override and for an unknown panel. | met | `tests/unit/chrona/presentation/review/test_profile_connections.py::test_summary_wording_overrides_panel_title_without_mutating_profile_and_checks_collisions` covers the title override, unknown panel, escaped pointer, metric-key collision, and duplicate-panel ambiguity. Focused presentation tests passed (94 passed); schema/annotation unit tests passed (128 passed), and schema equivalence reported `PASS` for L2/L3. | — |
| 4 | Do not edit `examples/**`. | met | `git diff --name-only 7a08f0c03b878a747465360c217a00d97e303b59..HEAD` contains no `examples/**` path. The public fixture remained clean after materialization. | — |

## Architecture conclusion

The View owns project wording. Profile closure resolves `<panel-id>.title` in the existing summary-wording namespace before rendering, preserves the authored profile and stable panel identity, and rejects unknown or ambiguous joined keys at the View pointer. The shared schema changes descriptions only. The implementation commit and local acceptance evidence are ready for PR review; CI and the release snapshot are still pending, so this review does not close the issue.
