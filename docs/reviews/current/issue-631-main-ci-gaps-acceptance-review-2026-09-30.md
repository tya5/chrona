<!-- chrona:literal-acceptance/v1 -->

# Issue #631 — main CI gaps acceptance review

Source: [Issue #631](https://github.com/tya5/chrona/issues/631), observed 2026-09-30. Work records: [#590 work record](../../planning/active/issue-590-parallel-safe-derived-evidence-work-record-2026-09-29.md) (the sync design and its production proof) and PR [#637](https://github.com/tya5/chrona/pull/637) (the title check).

## Literal issue acceptance

### Issue #631

- Source: [Issue #631](https://github.com/tya5/chrona/issues/631)
- Observed: 2026-09-30

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Every push to `main` runs the three-OS matrix automatically, as #555 accepted, or runs it after `derived-sync` on the synchronized SHA. In either case the exact main SHA gets a three-OS result without manual dispatch. | met | The second option is implemented: the last step of [`derived-sync.yml`](../../../.github/workflows/derived-sync.yml) dispatches `conformance.yml` on the immutable ref of the final SHA, for a changed sync and for a no-op sync. Production runs, each started by the sync and never by hand: [36640196953](https://github.com/tya5/chrona/actions/runs/36640196953) on `1e023957` (no-op), [36644063129](https://github.com/tya5/chrona/actions/runs/36644063129) on `1ab126c8`, [36647931251](https://github.com/tya5/chrona/actions/runs/36647931251) on the bot commit `a18e0a5a` (changed path), and [36652826531](https://github.com/tya5/chrona/actions/runs/36652826531) on `efb8a3be`. Each shows Ubuntu, macOS, Windows and newest-Python jobs. The push run itself skips the matrix on the pre-sync SHA on purpose ([AGENTS.md](../../../AGENTS.md)). | — |
| 2 | The Windows exact-main run is green (#630). | met | PR [#630](https://github.com/tya5/chrona/pull/630) merged as `1e023957`. The exact-main runs above are green on `windows-latest`, beginning with [36640196953](https://github.com/tya5/chrona/actions/runs/36640196953). | — |
| 3 | AGENTS.md: PR titles and commit subjects must not contain closing keywords followed by an issue number, unless that PR closes the issue. A check (for example a PR-title lint in `classify-pr`) flags `(close, closes, fix, fixes, resolve, resolves) #n` in titles of PRs that are not the closing PR. (The alternation is written with commas here because a pipe splits a table cell; the issue writes it with pipes.) | met | [AGENTS.md](../../../AGENTS.md) now covers PR titles and names the `closes-issue` label as the exemption. [`tools/check_pr_title.py`](../../../tools/check_pr_title.py) and the [`pr-title` workflow](../../../.github/workflows/pr-title.yml) (a separate lightweight workflow rather than `classify-pr`, so that a title edit reruns only the check) implement it, with [unit tests](../../../tests/unit/tools/test_check_pr_title.py). Live proof on PR #637: editing the title to add `closes #631` failed [36653714070](https://github.com/tya5/chrona/actions/runs/36653714070) with `E_PR_TITLE_CLOSING_KEYWORD`, and restoring it passed [36653786313](https://github.com/tya5/chrona/actions/runs/36653786313). | — |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

The fix is CI and process only: no product code, schema, Scene or adapter changes. Row 3 covers PR titles; commit subjects reach `main` only inside PRs whose titles are checked, and this repository merges with merge commits, so the title is what GitHub reads. The check cannot see a keyword typed into a PR body, which AGENTS.md already forbids for partial PRs.

The exact-main three-OS run for the commit that publishes this review is cited when the issue is closed.
