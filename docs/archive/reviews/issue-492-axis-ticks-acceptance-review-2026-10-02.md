<!-- chrona:literal-acceptance/v1 -->

# Issue #492 — axis ticks at interval starts acceptance review

Source: [Issue #492](https://github.com/tya5/chrona/issues/492), observed 2026-10-02 (body unchanged since filing, plus two comments of the implementing session: the claim and the owner decision). The issue has one acceptance row, copied below. Design: [design plan](../planning/issue-492-axis-ticks-design-plan-2026-10-02.md), [design](../../design/issue-492-axis-ticks-design-2026-10-02.md), [architecture review](issue-492-axis-ticks-architecture-review-2026-10-02.md), [implementation plan](../planning/issue-492-axis-ticks-implementation-plan-2026-10-02.md), living contract [Specification 39](../../specification/39-axis-and-observation-clarity.md) "Axis ticks (#492)".

Slices: design plan [PR #839](https://github.com/tya5/chrona/pull/839) (`f273aef5`); design and Specification 39 amendment [PR #844](https://github.com/tya5/chrona/pull/844) (`446f073b`); architecture review [PR #852](https://github.com/tya5/chrona/pull/852) (`d24a2d89`); implementation plan [PR #855](https://github.com/tya5/chrona/pull/855) (`c804ade6`); implementation [PR #859](https://github.com/tya5/chrona/pull/859) (`6adaba78`), with the main-sync evidence commit `62b73038`. Owner decision (options A and B, choice B, reversal) is [a comment on the issue](https://github.com/tya5/chrona/issues/492#issuecomment-5942433713) and in the design.

## Literal issue acceptance

### Issue #492

- Source: [Issue #492](https://github.com/tya5/chrona/issues/492)
- Observed: 2026-10-02

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A tier can draw ticks of a Theme-declared length at its interval starts, including a week tier, and one committed slide shows them. | met | A `grid-major` or `grid-minor` tier draws a tick of the length its Theme role declares as `tickLength`, standing on the axis rule at every interval start, for any unit ([`surface_axis.py`](../../../src/chrona/presentation/layout/surface_axis.py) `_axis_tick_length`; schema property in [`theme-v0.11`](../../../schemas/theme-v0.11.schema.yaml) and [`theme-v0.13`](../../../schemas/theme-v0.13.schema.yaml)). Ten synthetic tests in [`test_axis_ticks.py`](../../../tests/unit/chrona/presentation/scene/test_axis_ticks.py): a week tier gives at least 52 ticks of the declared length standing on the slot bottom; a tier whose role declares no length keeps the full-height line; both roles; the ticks stand at the same positions, ids and paint order as the full-height line; length equal to the slot is allowed; zero, negative and oversized lengths are diagnosed (`E_PRESENTATION_AXIS_INVALID`, `E_PRESENTATION_AXIS_OVERFLOW`); role admission admits `tickLength` on the two grid roles only. Committed slide: Controller Z [`axis-ticks`](../../../examples/controller-z/generated/axis-ticks.svg) (manifest [entry](../../../examples/controller-z/manifest.yaml); view, Theme and Context beside it) draws 23 week ticks (`M518.4 108.8L518.4 116.8`, 8 px, ending on the rule at 116.8). Rendered and viewed: the ticks stand on the axis rule under the month labels and the quarter band, and the labels are unchanged. | — |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

The View is unchanged (no widening, no version): the tier says where, the Theme says how far. Theme v0.11 and v0.13 gained one optional role property in place under Specification 56 section 3.2; `python -m tools.schema_equivalence --base-rev origin/main` reported `additive=2 equal=38` and PASS, with no new expected-delta entry. Layout owns the geometry; Scene, the adapters and the semantic registry are untouched. The default path is byte-identical: a full `tools/regenerate_public_examples.py --write` of the corpus changed no existing slide, and the sync commit `62b73038` adds only the new slide and the derived reports.

Disclosures:

- **Not delivered, by design and not filed:** a tick origin other than the axis rule ("or from the lane edge" in the issue body), and a per-tier length (one length per grid role per Theme). Both are additive successors (a `tickAnchor` role property, a View tier role) only if a target asks; the issue's acceptance row does not require them.
- **The target mocks** that the issue names were read as pictures; Off-World names week ticks in its README, the Swiss mock shows short marks, and the Flat Pack, Marquee and Montmartre rows do not mention ticks in text. No preset or catalogue Theme was edited, so none of the five named targets' presets draws ticks yet; adopting `tickLength` in a preset is a preset-owner decision (#718 area).
- **Test-suite counts moved with the new slide:** the public-evidence counts (30 slides, axis labels, hosted labels, 69 derived paths) and the derived-inventory test, which now compares declared outputs with tracked and untracked unignored files because a PR never authors declared evidence.
- **#493** (two labels in one cell) shares no mechanism with this and was left open.

Exact review-bearing-main three-OS CI and newest-Python materializer run must pass before closing #492; record that run in the issue closing comment.
