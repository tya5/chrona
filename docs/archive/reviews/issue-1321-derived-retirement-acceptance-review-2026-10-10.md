<!-- chrona:literal-acceptance/v1 -->

# Issue #1321 — source-baseline retirement acceptance

Recovery base: `ea681d44324cffe509a5d0530655cb849386b54e` (failed sync
38010814862); [design, architecture review and implementation plan](https://github.com/tya5/chrona/issues/1321#issuecomment-6092377582).
This is the exclusively assigned red-main tooling fix, not normal feature publication.
PR #1323 merged as `6fe0dacf04e31b5e542f422f4f16eaa5f8810998` after every
substantive check and [independent artifact audit](https://github.com/tya5/chrona/pull/1323#issuecomment-6092580719)
passed. [Sync](https://github.com/tya5/chrona/actions/runs/38016810914) published
bot-generated main `fed9727461e6fefa5b092cdea638bf3a722dfcef`: all 99 outputs
match the audited snapshot; exactly 52 retired paths are absent, with no extra
changes. Closed after [exact-main release](https://github.com/tya5/chrona/actions/runs/38020427654)
succeeded on `0fd085d17422fd332c49b4b75ebdf43fe9459f93`, containing this final record.

## Literal issue acceptance

### Issue #1321

- Source: [Issue #1321](https://github.com/tya5/chrona/issues/1321)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Main `derived-main` is green on a commit after the fix, and the 52 orphan files are gone from the tree. | met | [Trusted gate](https://github.com/tya5/chrona/actions/runs/38017276223) completed success on fed97274; check114110242946 independently verified as completed/success from github-actions. [Sync](https://github.com/tya5/chrona/actions/runs/38016810914) fast-forwarded actual main to that SHA. Exact tree/snapshot audit proves all 52 retired paths absent and all 99 surviving blobs identical. | — |
| 2 | A synthetic test deletes a slide, then lands an unrelated commit, then syncs. The test sees the outputs retired, and a planted never-declared file still rejected. | met | [Synthetic git-history and snapshot tests](../../../tests/unit/tools/test_derived_workflow.py): one snapshot case covers deletion, unrelated docs commit, actual retirement, exact source bytes in the before archive, and a subsequent planted never-declared output refused by the real orphan validator. Separate cases cover independent ancestors, non-FF merges, modified/restored and deleted/recreated refusals. Combined workflow/trusted-gate batch: 24 passed (11.81s). | — |
| 3 | Do not edit `examples/**` by hand. | met | Only [workflow tooling](../../../tools/derived_workflow.py), [synthetic tests](../../../tests/unit/tools/test_derived_workflow.py) and this review change. No authored example or managed generated output edits. | — |

## Programme-level criteria (optional)

None. The old unready-base PR derived-ready wait was cancelled after recovery merge;
it is not counted green and no gate was weakened. The exact-main release above passed
three-OS pytest, conformance and wheel/smoke, newest-Python materializers and MCP.

## Architecture conclusion

Retirement discovery belongs to workflow tooling: first-parent tracked-blob and
manifest provenance, with uninterrupted unchanged presence. Current inventory,
source-baseline byte comparisons, path/symlink bounds, orphan rejection and
trusted gate/fast-forward/full release semantics stay unchanged. Core, View,
Theme, Layout, Scene and adapters are untouched. No fallback deletion of unknown
outputs, depth cap, history side-branch traversal or gate weakening is added.
