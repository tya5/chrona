<!-- chrona:literal-acceptance/v1 -->

# Release Review — Actionable Unsupported Resource Versions (#489)

**Implementation base:** `6683115bbed7acbe3ab5b4e9ddae22d50cbf2ac4`, with generated-inventory correction `570c9513cf61dbb3d7215c8c5b8be9f2ff94ad40`. **Design chain:** [design plan](../../planning/active/issue-489-resource-version-diagnostics-design-plan-2026-09-27.md), [design](../../design/issue-489-resource-version-diagnostics-design-2026-09-27.md), [architecture review](issue-489-resource-version-diagnostics-architecture-review-2026-09-27.md), [implementation plan](../../planning/active/issue-489-resource-version-diagnostics-implementation-plan-2026-09-27.md), and [Specification 56](../../specification/56-schema-authoring-and-diagnostics.md).

## Release evidence

- The CLI regression test copies `mission-light`, changes one declared member version, and invokes the public `chrona render` command. View `chrona/view/v0.22` reports support for `chrona/view/v0.26`; Theme `chrona/theme/v0.1` reports `chrona/theme/v0.11`; Layout Profile `chrona/layout-profile/v0.1` reports `chrona/layout-profile/v0.9`. Each JSON diagnostic has `E_RESOURCE_VERSION_UNSUPPORTED`, `sourceRef: /version`, kind, identity, found and supported versions, and `chrona preset copy mission-light --output <new-dir>`. None creates the requested SVG. A separate explicit stale View override test proves that a member not declared by the copy does **not** receive the copy remedy.
- Focused local command: `.venv/bin/python -m pytest -q tests/cli/test_cli.py tests/unit/chrona/presentation/contracts/test_contract_resources.py tests/unit/chrona/presentation/model/test_draft_closure.py tests/unit/chrona/presentation/model/test_snapshot_context_closure.py` — **156 passed**. Contract tests cover every registered kind, malformed-version separation and sibling diagnostic collection; closure tests cover direct/guided Draft and snapshot Layout/Review Detail paths. The environment was a project `.venv` with `.[dev,render]` and the CJK font package.
- `.venv/bin/python tools/regenerate_public_examples.py --check --jobs 4` — **PASS, 28 slides**; the implementation changed no generated public Scene/SVG bytes. `.venv/bin/python tools/diagnostic_inventory.py --check`, `.venv/bin/python tools/declared_value_inventory.py --check`, `.venv/bin/python tools/check_issue_acceptance_reviews.py`, and `git diff --check` passed. The diagnostic inventory adds the new code; the declared-value inventory updates only one closure source line number.
- The first [CI run on `6683115b`](https://github.com/tya5/chrona/actions/runs/36288255074) reproduced all public materializers and passed full pytest on all three OSes, but its conformance gate failed on all three because that one generated declared-value inventory line was stale. The cause was isolated from each job log and corrected in `570c9513`. The final [CI run on `570c9513`](https://github.com/tya5/chrona/actions/runs/36288517179) passed all four jobs: macOS, Ubuntu and Windows conformance/full pytest/wheel-smoke, plus newest-Python public reproduction.

## Literal issue acceptance

### Issue #489

- Source: [Issue #489](https://github.com/tya5/chrona/issues/489)
- Observed: 2026-09-27

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Rendering a preset copy with an older View version fails with a code and message that name the found and supported versions, with `sourceRef: /version`. | met | [`test_cli_copied_builtin_preset_rejects_unsupported_member_version`](../../../tests/cli/test_cli.py) checks the public JSON, both versions, pointer and absent SVG for stale View. | — |
| 2 | For a builtin preset copy, the message tells the user to re-run `chrona preset copy <id>`. | met | The same CLI test checks the exact catalogue-id command; [`test_cli_stale_explicit_override_with_current_preset_has_no_copy_remedy`](../../../tests/cli/test_cli.py) checks provenance isolation. | — |
| 3 | A CLI test covers a stale View, a stale Theme and a stale Layout Profile. | met | [`test_cli_copied_builtin_preset_rejects_unsupported_member_version`](../../../tests/cli/test_cli.py) is parameterized over all three resource kinds and versions; focused and CI results above. | — |

## Programme-level criteria (optional)

No supported schema version or resource migration behavior changed. Existing valid public materializers remain byte-identical.

## Architecture conclusion

The resource contract registry remains the only authority for supported versions. Contract/collector layers report typed, resource-local failure and continue sibling validation; closure preserves the pointer and failed preset declaration; only the CLI formats a copy command. Snapshot identity checks remain before contract parsing. Project, View, Theme, Layout, Scene and adapter rendering paths are unchanged. All literal criteria and the final CI gate are met; publish this review, verify its own CI, then close #489.
