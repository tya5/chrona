# Deadline leftovers — acceptance status

<!-- chrona:literal-acceptance/v1 -->

Caption source: `5f04445fc`; [design](../../design/issue-1397-days-late-caption-design-2026-10-15.md),
[implementation plan and evidence](../../planning/active/issue-1397-days-late-caption-implementation-plan-2026-10-15.md).
103 focused tests and29 documentation checks PASS; schema-equivalence L1/L2/L3
PASS (additive View member, no baseline diagnostic changes). Independent static
review found no remaining boundary issue. No `examples/**` or generated report
edits. Layout completes text; Scene projects it; Core remains count authority.
Post-CI correction `ea6e4c785`:87 focused regressions and65 obstacle-index checks
PASS. Its [exact-head snapshot](https://github.com/tya5/chrona/pull/1523#issuecomment-6184396020)
keeps all100 public SVG/Scene bytes unchanged; only diagnostic locations and
the four new count-format coverage entries differ. After adopting READY main
`7c46a7c69`,61 caption/key-row/ownership regressions PASS. Final-head CI and
snapshot remain required; earlier-head evidence is not substituted.

## Literal issue acceptance

### Issue #1397

- Source: [issue](https://github.com/tya5/chrona/issues/1397)
- Observed: 2026-10-15

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | **`control-room-dark` deadline-mark ink (Layout).** Light bar on a dark ground: no single flat ink reaches 3:1 on both the row ground and the planned bar (swept over every Scheme color: best 2.15:1). It needs a halo or an outlined tick, a mark-geometry decision. Until then a View that shows deadlines on it gets `E_THEME_ROLE_REQUIRED`. | met | Implementation merged in [PR1521](https://github.com/tya5/chrona/pull/1521),198 focused cases, all100 public SVG/Scene bytes unchanged. Exact-main release [38678805146](https://github.com/tya5/chrona/actions/runs/38678805146) on `c068404687f97f6eb73eea094ada18431a153c02` succeeds on macOS, Ubuntu and Windows full pytest/conformance/wheel-smoke, newest-Python reproduction and MCP. | — |
| 2 | **Mirror the `deadline-mark` Theme block into `examples/halcyon-1/themes/editorial.yaml` and `editorial-readable-default.yaml` (reviewer-owned).** Those Themes are byte-mirrors of `presets/bundles/editorial` and `editorial-readable-default` (`test_public_preset_evidence`), so the bundled Editorial default and `editorial` cannot gain the role until the reviewer mirrors the same five lines (3 values, 1 role, 1 binding `deadline-mark.stroke: text`, verified 3:1 on both) in both places. Developer cannot edit `examples/**`. | deferred | [Reviewer decision](https://github.com/tya5/chrona/issues/1397#issuecomment-6182798308) replaces mirrors with package references; reviewer owns corpus adaptation. This PR does not absorb it. | [1397 reviewer row2](https://github.com/tya5/chrona/issues/1397). |
| 3 | **A "days late" caption next to the run**, through the #586 figure vocabulary and its format rules (locale and unit word are author text there). `W_DEADLINE` already states the number. | not met | [Actual SVG/PDF/typeset tests](../../../tests/integration/test_deadline_caption.py), [template/Core handoff tests](../../../tests/unit/chrona/presentation/test_deadline_text.py), [two-anchor tests](../../../tests/unit/chrona/presentation/layout/test_deadline_captions.py): four count forms, author copy/braces, kept/absent/off-window, right-to-left fallback, positive omission counts/subjects,4.5:1 text gate and unchanged prior primitives. Approved closed-placeholder scope follows the reviewer decision, not a new per-object figure model. PR snapshot and exact-main release remain pending. | This caption PR's CI and release gate. |
| 4 | **A deadline mark on the dependency-network surface** (it has no timeline, so the View refuses the member) and per-object overrides of the `show` rule. | deferred | [Reviewer parks this row](https://github.com/tya5/chrona/issues/1397#issuecomment-6182798308) pending a network position rule. | [1397 parked row4](https://github.com/tya5/chrona/issues/1397). |
| 5 | **Folded header points** carry no deadline mark (`I_LAYOUT_DEADLINE_FOLDED`); a mark on the compact header row is a separate Layout decision. | deferred | [Reviewer declines it](https://github.com/tya5/chrona/issues/1397#issuecomment-6182798308): existing truthful folded diagnostic is sufficient. No folded-row Layout exception added. | [Approved won't-do disposition](https://github.com/tya5/chrona/issues/1397#issuecomment-6182798308). |

## Programme-level criteria (optional)

None. Parent1397 stays open. Local passing tests do not establish release
acceptance; current-head snapshot/CI and an exact containing-review main release
must be inspected before changing the pending dispositions.
