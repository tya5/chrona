# Deadline leftovers — acceptance status

<!-- chrona:literal-acceptance/v1 -->

Rows1/3 retain their released evidence below. Remaining work follows the
[current design, architecture review and implementation plan](../../planning/active/issue-1397-remaining-deadlines-work-record-2026-10-17.md),
published as `787661b04` before code. Core owns verdicts; View owns selection;
Layout completes geometry; Scene/adapters project it. No `examples/**` edits.

## Literal issue acceptance

### Issue #1397

- Source: [issue](https://github.com/tya5/chrona/issues/1397)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | **`control-room-dark` deadline-mark ink (Layout).** Light bar on a dark ground: no single flat ink reaches 3:1 on both the row ground and the planned bar (swept over every Scheme color: best 2.15:1). It needs a halo or an outlined tick, a mark-geometry decision. Until then a View that shows deadlines on it gets `E_THEME_ROLE_REQUIRED`. | met | Implementation merged in [PR1521](https://github.com/tya5/chrona/pull/1521),198 focused cases, all100 public SVG/Scene bytes unchanged. Exact-main release [38678805146](https://github.com/tya5/chrona/actions/runs/38678805146) on `c068404687f97f6eb73eea094ada18431a153c02` succeeds on macOS, Ubuntu and Windows full pytest/conformance/wheel-smoke, newest-Python reproduction and MCP. | — |
| 2 | **Mirror the `deadline-mark` Theme block into `examples/halcyon-1/themes/editorial.yaml` and `editorial-readable-default.yaml` (reviewer-owned).** Those Themes are byte-mirrors of `presets/bundles/editorial` and `editorial-readable-default` (`test_public_preset_evidence`), so the bundled Editorial default and `editorial` cannot gain the role until the reviewer mirrors the same five lines (3 values, 1 role, 1 binding `deadline-mark.stroke: text`, verified 3:1 on both) in both places. Developer cannot edit `examples/**`. | deferred | [Reviewer decision](https://github.com/tya5/chrona/issues/1397#issuecomment-6182798308) replaces mirrors with package references; reviewer owns corpus adaptation. This PR does not absorb it. | [1397 reviewer row2](https://github.com/tya5/chrona/issues/1397). |
| 3 | **A "days late" caption next to the run**, through the #586 figure vocabulary and its format rules (locale and unit word are author text there). `W_DEADLINE` already states the number. | met | [Actual SVG/PDF/typeset tests](../../../tests/integration/test_deadline_caption.py), [template/Core handoff tests](../../../tests/unit/chrona/presentation/test_deadline_text.py), [two-anchor tests](../../../tests/unit/chrona/presentation/layout/test_deadline_captions.py): four count forms, author copy/braces, kept/absent/off-window, right-to-left fallback, positive omission counts/subjects,4.5:1 text gate and unchanged prior primitives. [PR1523 exact-head artifact](https://github.com/tya5/chrona/pull/1523#issuecomment-6184481064) proves100 public SVG/Scene bytes unchanged. Exact review-containing main `40125ab92d95892e01c82237502e1deaec0b0d55`: [release38685637012](https://github.com/tya5/chrona/actions/runs/38685637012) passed full pytest/conformance/wheel-smoke on Ubuntu, Windows and macOS, newest-Python materializers and MCP. | — |
| 4 | **A deadline mark on the dependency-network surface** (it has no timeline, so the View refuses the member) and per-object overrides of the `show` rule. | not met | Override implementation and [neutral tests](../../../tests/integration/test_deadline_overrides.py) cover replacing precedence, hidden caption versus retained Core warning, unknown ids, malformed syntax, empty-map identity and selection independence. The network-only [deferral proposal](https://github.com/tya5/chrona/issues/1397#issuecomment-6234014932) awaits reviewer disposition; the existing network prohibition remains. Earlier parking is not treated as current approval. | [1397 network decision](https://github.com/tya5/chrona/issues/1397#issuecomment-6234014932). |
| 5 | **Folded header points** carry no deadline mark (`I_LAYOUT_DEADLINE_FOLDED`); a mark on the compact header row is a separate Layout decision. | met | Reopened by [reviewer6233959539](https://github.com/tya5/chrona/issues/1397#issuecomment-6233959539). [Neutral integration](../../../tests/integration/test_folded_deadline_marks.py) proves kept/slipped ticks, run, distinct packed lanes, complete outlined/wobble envelopes in the authored header, caption, provenance and off-window diagnostics; [host tests](../../../tests/integration/test_deadline_mark.py) cover ordinary/folded/forecast occurrences and zero-width ink. Actual baseline and wobble PNGs viewed: two folded points, one ordinary task, visible six-day caption, no header overflow or backward date representation. Exact-main release remains a programme gate below. | — |

## Programme-level criteria (optional)

Current implementation requires focused rule/geometry tests, schema equivalence,
the official public SVG/Scene count batch and exact review-containing main
three-OS full pytest/conformance/wheel, public reproduction and MCP. Rows1/3
are accepted; parent1397 remains open for its incomplete/reviewer-owned rows.
Archive only after parent closure.

Schema equivalence passes: one additive View schema, 38 unchanged; existing
corpus verdicts and 739 diagnostic probes remain stable. Three stale merged
forecast delta entries were retired with proof by `--prune-stale`.
Independent architecture audit confirms shared Layout geometry, immutable
override normalization, preserved Core warnings, global outline paint order and
unchanged Scene/adapter ownership. Existing insufficient-header capacity keeps
`W_LAYOUT_GROUP_HEADER_OVERFLOW`, not a new fitting exception. The unrelated
all-point row-resurrection defect is [issue1660](https://github.com/tya5/chrona/issues/1660),
reproduced without deadlines on preceding main; mixed-plan acceptance does not
claim to resolve it. Public snapshot counts and exact-main release are pending.
