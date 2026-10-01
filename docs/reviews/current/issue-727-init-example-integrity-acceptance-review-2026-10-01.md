<!-- chrona:literal-acceptance/v1 -->

# Issue #727 — init --example integrity acceptance review

Source: [Issue #727](https://github.com/tya5/chrona/issues/727), observed 2026-10-01 (no comments; body unchanged since 2026-10-01). Found by #723. Design and plan, published in [PR #748](https://github.com/tya5/chrona/pull/748) (merged as [`75fa6298`](https://github.com/tya5/chrona/commit/75fa6298c74b439219cc598e62ad87672196b504), [PR CI](https://github.com/tya5/chrona/actions/runs/36822258562)): [design](../../design/issue-727-init-example-integrity-design-2026-10-01.md) and [implementation plan](../../planning/active/issue-727-init-example-integrity-implementation-plan-2026-10-01.md). Code and docs: [PR #751](https://github.com/tya5/chrona/pull/751) merged as [`83bac1a8`](https://github.com/tya5/chrona/commit/83bac1a8763b7c698b140069398227f984a470d1) ([PR CI](https://github.com/tya5/chrona/actions/runs/36823646588)).

## Literal issue acceptance

### Issue #727

- Source: [Issue #727](https://github.com/tya5/chrona/issues/727)
- Observed: 2026-10-01

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The documented path from `chrona init --example` to a rendered example Context works, with the chosen option stated in the guide and covered by a test that runs it. | met | The owner-delegated choice was option 3: the example corpus is not a trust boundary and ADR-0030 stays, so `chrona init --example` writes an explicit `integrity: optional` with a comment citing ADR-0030 and "example corpus only", while a Store you create yourself, and an `integrity` you omit, stay `required`. The [first-project guide](../../guides/first-project.md) has a new section, "Render an example Context from its Store", with the reference file written by a heredoc and a `render-review --context-reference … --store-config …` command, and it states the option and the reason; the README says the same and links to it. The [end-to-end test](../../../tests/integration/test_init_example_documented_path.py) reads the `init` and `render-review` commands and the reference YAML out of the guide and runs them as written in a temporary directory, asserting an SVG is produced and that the guide's command carries no `--allow-missing-content-identity`. I ran the guide's steps myself on a fresh `init` Store: it rendered a 77 KB SVG with layout warnings only, and the same Store flipped to `required` refused with `E_CONTENT_IDENTITY_REQUIRED`. | — |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

CLI, init and documentation only; no schema or reader-default change. The #723 defaults (`LocalSnapshotReader`, `LocalBaselineRegistry` and an omitted `integrity` all mean `required`) are untouched, and the example references stay unpinned, as ADR-0030 has it. Content identity is therefore still required everywhere except the one Store that `init --example` creates for the example corpus.

Disclosures:

- **A scope addition the issue did not name.** `render-review` never read the Store config: it built its reader only from `--snapshot-root`, `--store-identity` and `--allow-missing-content-identity`, and only the `command-*`, `actual-*` and `baseline-*` commands used a config. Writing `optional` into `.chrona/store.yaml` alone would not have fixed the documented path, so [PR #751](https://github.com/tya5/chrona/pull/751) added an explicit `render-review --store-config`: root, identity and integrity come from the config entry matching the Context reference's `store`; `--snapshot-root` and `--store-identity` are required only without it and are rejected alongside it; `--allow-missing-content-identity` still overrides a `required` config for one call. Without `--store-config` the command behaves as before.
- **The guide previously did not say how to write a `--context-reference`.** The README's `render-review` block was `doc-check skip` ("author-created reference"). The new guide section is runnable and its block carries a `doc-check skip` marker only because the heredoc creates its own input.
- **The #723 acceptance review is now out of date on one point.** [It records](issue-723-content-identity-required-acceptance-review-2026-10-01.md) that `init --example` writes `integrity: required`; since #751 it writes `optional` for the example corpus. That review is a dated record and is left as published; this review supersedes it on that point. Spec 42, the #723 design and plan, the unit tests that asserted `required` for the example, and the generated CLI reference were updated.
- **Plain `chrona init` writes no Store config.** The brief expected a `required` line from it; there is no config to write one into, so the tests assert that omission means `required` instead.

Exact review-bearing-main three-OS CI and newest-Python materializer run must pass before closing #727; record that run in the issue closing comment.
