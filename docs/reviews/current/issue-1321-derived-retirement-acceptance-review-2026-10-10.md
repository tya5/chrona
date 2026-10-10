<!-- chrona:literal-acceptance/v1 -->

# Issue #1321 — source-baseline retirement acceptance

Recovery base: `ea681d44324cffe509a5d0530655cb849386b54e` (failed sync
38010814862); [design, architecture review and implementation plan](https://github.com/tya5/chrona/issues/1321#issuecomment-6092377582).
This is the exclusively assigned red-main tooling fix, not normal feature publication.
Current local dry-run proves all 52 retirements without changing generated files.
Public snapshot, source sync/trusted gate and final-review-containing full release
remain pending; do not close.

## Literal issue acceptance

### Issue #1321

- Source: [Issue #1321](https://github.com/tya5/chrona/issues/1321)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Main `derived-main` is green on a commit after the fix, and the 52 orphan files are gone from the tree. | not met | [Recovery disposition](https://github.com/tya5/chrona/issues/1321#issuecomment-6092377582): exact-main trusted sync and bot-owned retirement remain required. The read-only source dry-run recognizes exactly 52 formerly declared, unchanged tracked outputs. | — |
| 2 | A synthetic test deletes a slide, then lands an unrelated commit, then syncs. The test sees the outputs retired, and a planted never-declared file still rejected. | met | [Synthetic git-history and snapshot tests](../../../tests/unit/tools/test_derived_workflow.py): one snapshot case covers deletion, unrelated docs commit, actual retirement, exact source bytes in the before archive, and a subsequent planted never-declared output refused by the real orphan validator. Separate cases cover independent ancestors, non-FF merges, modified/restored and deleted/recreated refusals. Combined workflow/trusted-gate batch: 24 passed (11.81s). | — |
| 3 | Do not edit `examples/**` by hand. | met | Only [workflow tooling](../../../tools/derived_workflow.py), [synthetic tests](../../../tests/unit/tools/test_derived_workflow.py) and this review change. No authored example or managed generated output edits. | — |

## Programme-level criteria (optional)

None. Public release remains unverified; local tests and a dry-run do not prove main recovery.

## Architecture conclusion

Retirement discovery belongs to workflow tooling: first-parent tracked-blob and
manifest provenance, with uninterrupted unchanged presence. Current inventory,
source-baseline byte comparisons, path/symlink bounds, orphan rejection and
trusted gate/fast-forward/full release semantics stay unchanged. Core, View,
Theme, Layout, Scene and adapters are untouched. No fallback deletion of unknown
outputs, depth cap, history side-branch traversal or gate weakening is added.
