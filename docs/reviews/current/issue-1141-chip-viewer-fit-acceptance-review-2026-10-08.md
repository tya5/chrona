<!-- chrona:literal-acceptance/v1 -->

# Release review — chip viewer-fit follow-ups

Implementation: `a602ad3b`, `25c3fdee`, `72ec279e`; [current design, architecture review and implementation plan](https://github.com/tya5/chrona/issues/1141#issuecomment-6040718788).
Reconciled with trusted-ready `937483c80fe2f1426bce2fa63b98d8f976f53448` in `dd810896` ([exact derived gate](https://github.com/tya5/chrona/actions/runs/37683530158)). Chip/token/placement/role/SVG tests: 64 passed after source-main integration (`test_viewer_fit_stamp.py`, `test_viewer_fit_token.py`, `test_chip_box_follows_text.py`, `test_viewer_fit_roles.py`); the subsequent ready commit changes only the generated diagnostic inventory. Import direction, module reachability and literal review checks pass. This is local Part 1 evidence, not release acceptance.
The [previous PR run](https://github.com/tya5/chrona/actions/runs/37680647425) passed all code checks; its freshness check failed after main advanced. Its shared artifact `11509182958` was independently checked against all 143 base files: 67 SVGs, 67 Scenes and eight reports were byte-identical; only existing-ID diagnostic guard sites/source locations changed. Fresh-base PR evidence remains required.

## Literal issue acceptance

### Issue #1141

- Source: [Issue #1141](https://github.com/tya5/chrona/issues/1141)
- Observed: 2026-10-08

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A chip fixture under `box-follows-text`: no static chip rect, the filter group around the label, every line ending with the end-inset spacing; a rounded chip or a stroked chip refused at its declaration; `raw` byte-identical; contrast unchanged. | met | [Four-family actual SVG and serialized Scene fixtures](https://github.com/tya5/chrona/blob/72ec279e/tests/integration/test_chip_box_follows_text.py): paired filter/boxId, every line's trailing spaces, independent baseline raw Scene/SVG hashes, unchanged geometry/paint/contrast, legacy/physical rounded and stroked declaration pointers. [Completed-placement guards](https://github.com/tya5/chrona/blob/72ec279e/tests/unit/chrona/presentation/layout/test_viewer_fit_stamp.py): absent/suppressed/empty chips and hosted visual rejection. | — |
| 2 | Part 2 only after the owner decision. | not met | [Owner decision request](https://github.com/tya5/chrona/issues/1141#issuecomment-6039236312) remains pending. No independent bar-label role has been implemented or presumed approved; the issue remains open. | — |

## Programme-level criteria (optional)

Layout alone completes geometry, metrics and chip/text identity; Scene projects the completed fit and applies existing paint admission. Spec07 records chip admission; Spec08's one-to-one fit invariant and adapters are reused. No schema change, compatibility alias or examples edits. No unresolved Part 1 architecture finding.
Publication gate remains pending: exact-current-base PR checks, shared corpus snapshot review, and successful exact-review-main three-OS pytest/conformance/wheel/materializer CI. Part 2 needs the owner's selected rule or explicit successor disposition before issue closure.
