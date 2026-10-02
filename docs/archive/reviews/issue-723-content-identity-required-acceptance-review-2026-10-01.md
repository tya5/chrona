<!-- chrona:literal-acceptance/v1 -->

# Issue #723 — content identity required by default acceptance review

Source: [Issue #723](https://github.com/tya5/chrona/issues/723), observed 2026-10-01 (no comments; body unchanged since 2026-10-01). Found by the #710 investigation (vulnerability 2 of its design, part A). Design and plan, published in [PR #725](https://github.com/tya5/chrona/pull/725) (merged as [`77c45b3f`](https://github.com/tya5/chrona/commit/77c45b3f7d5ca8855623c59004e0a3344cee25a8), [PR CI](https://github.com/tya5/chrona/actions/runs/36798916595)): [design](../../design/issue-723-content-identity-required-by-default-design-2026-10-01.md) and [implementation plan](../planning/issue-723-content-identity-required-by-default-implementation-plan-2026-10-01.md). Code: [PR #726](https://github.com/tya5/chrona/pull/726) merged as [`b8b7a199`](https://github.com/tya5/chrona/commit/b8b7a1999afd6eb2040b78c4f22548e4bb9cb559) ([PR CI](https://github.com/tya5/chrona/actions/runs/36800911441)).

## Literal issue acceptance

### Issue #723

- Source: [Issue #723](https://github.com/tya5/chrona/issues/723)
- Observed: 2026-10-01

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The default is required in the reader (`LocalSnapshotReader`, `LocalBaselineRegistry`) and in Store config (omitted `integrity` means `required`); `optional` remains an explicit opt-out in code, config and CLI. | met | `LocalSnapshotReader` and `LocalBaselineRegistry` default to required, a Store config that omits `integrity` means `required`, and `ConfiguredStoreReader` passes the flag to both readers explicitly. `optional` stays available as an explicit opt-out in code, in config and on the CLI, where `--require-content-identity` became `--allow-missing-content-identity` (regenerated in the [CLI reference](../../guides/cli-reference.md)). Specs 42 and 54 are amended. The store-config schema still permits omission. The [regression tests](../../../tests/unit/chrona/storage/test_content_identity_required_by_default.py) fail when each default is set back (mutation checks in the PR body). | — |
| 2 | `chrona init --example` writes `integrity: required`, and the Store it creates is readable by its own commands. | narrowed | `init --example` writes `integrity: required` ([PR #726](https://github.com/tya5/chrona/pull/726); checked by a [test](../../../tests/unit/chrona/storage/test_content_identity_required_by_default.py) and by running `chrona init x --example halcyon-1`). The commands that read through the Store config, `command apply` and `undo`, use pinned references and run under the required default in their tests. The example's own Contexts are different: they leave inner references unpinned by design (ADR-0030; 191 unpinned references against 17 pinned), so `chrona render-review` on one of them refuses by default with `E_CONTENT_IDENTITY_REQUIRED`, which I reproduced on a fresh `init --example` Store, and needs `--allow-missing-content-identity`. | [#727](https://github.com/tya5/chrona/issues/727) |
| 3 | Tests prove that, by default, an identity mismatch (`E_CONTENT_IDENTITY`) and a missing identity (`E_CONTENT_IDENTITY_REQUIRED`) are refused, and that `optional` remains an explicit opt-out; every committed fixture or test that relied on `optional` is migrated deliberately. | met | The [new tests](../../../tests/unit/chrona/storage/test_content_identity_required_by_default.py) assert the default refuses a mismatch and a missing identity, that an omitted `integrity` is required, that `optional` opts out, that `init` writes `required` and that the CLI flag works, deciding from reference data and not from the host OS. With the defaults flipped 32 tests failed; each was migrated deliberately, either by stating `require_content_identity=False` with the reason (the render-review closure helper and the materializer readers rely on ADR-0030's unpinned inner references) or by rewriting the assertion (`test_revision_store_identity.py`, listed in [PR #726](https://github.com/tya5/chrona/pull/726)). No test was weakened. | — |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Storage and CLI defaults only, plus two spec amendments; no schema change. Content identity is now a default control on the Store read path instead of an opt-in, which closes the weakness the #710 investigation named: an address check was the only barrier when identity was optional.

Disclosures:

- **Row 2 is narrowed.** The Store `init --example` creates cannot render its own unpinned example Contexts under its own `required` setting without the opt-out. Nothing shipped reads them through the config, so no flow in the repository broke, but the documented path from `init --example` to a rendered example Context now needs the flag; the choice between pinning the example references (reversing ADR-0030), documenting the flag, or letting the example corpus write `optional` is recorded in #727.
- **My end-to-end check was partial.** The default refusal was reproduced; the opt-out path was checked by the unit and CLI tests, and my own CLI run with a hand-built reference stopped at `E_CLOSURE_ID` because that reference lacked fields, so I did not complete it.
- **The schema permits omission.** The store-config schema was not edited; omission is defined by the spec and the reader, not forbidden by the schema.

Exact review-bearing-main three-OS CI and newest-Python materializer run must pass before closing #723; record that run in the issue closing comment.
