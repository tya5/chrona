# Architecture Review — Table `minmax` Content Minimum and Flex Allocation (#487)

**Decision:** design approved for implementation planning, with one open question left
for the lead/owner (below). **Reviewed design:** [#487 contract](../../design/issue-487-table-minmax-flex-allocation-design-2026-09-26.md).
**Evidence:** [prototype evidence](../../research/presentation/issue-487-table-minmax-flex-allocation-prototype-evidence-2026-09-26.md).
**Normative update:** Specification 24 §2.1, Specification 33 §5, ADR-0032. This is a
design review, not issue acceptance.

## Whole-system consistency

| Boundary | Authority checked | Result |
| --- | --- | --- |
| View | Specification 24 §1, `tableColumns` | No change. The table's columns and cells are read, not redefined; this issue only changes how their already-measured extent feeds the slot's minimum. |
| Theme | Specification 07 §5.1, `resolve_theme_metrics` | No metric added, removed or renamed. `table.column.minInlineSize` keeps its #480 meaning (a `preferred_inline` floor); it is not folded into `minimum_inline`. |
| Layout / #480 boundary | Specification 24 §2.1, `_table_content_inline` | Contract 1 reuses the exact function #480 added for `preferred_inline`; no second measurement path is introduced. This is the boundary #480's architecture review explicitly deferred to this issue. |
| Layout / engine | Specification 33 §5 and §8, `layout/engine.py::_allocate` | Contract 2 changes one function used by every `row`/`column`/`grid` track resolution, on every axis. The isolation check in the evidence is the load-bearing proof that this does not silently reach non-table flexible tracks: every current zero-minimum `fill`/`{fr: n}` track is numerically unaffected. |
| Row path / #467 | Specification 38 §3 | Not touched. #467 owns block-axis row requirements; this issue is inline-axis flex distribution and does not call or extend `required_row_block_extents`. |
| Plot labels / #466 | Specification 50 label search | Not touched directly, but indirectly affected: a narrower or wider table changes how much room the sibling plot/relation surface has, which can toggle `W_LAYOUT_LABEL_SUPPRESSED`/`W_LAYOUT_RELATION_LABEL_SUPPRESSED` on a different member/relation. This is expected and must be attributed per slide, not treated as a #466 regression. |
| Scene / adapters | Specification 08 | No change. Scene still receives one resolved rectangle per slot from the manifest; it does not know or care which allocation rule produced it. |
| `print-mono` preset | `docs/research/presentation/preset-tuning/print-mono/README.md` | The preset's `minmax` workaround for #480 is unchanged in spelling; its resolved width changes along with the other 18 slides. Its purpose (giving the content-sized table slack for its last column) is still served, since the new minimum is still the table's real measured content. |

## Reviewed ambiguities and resolutions

1. **Additive versus `max(minimum, share)`.** Resolved in favor of `max(minimum, share)`
   (ADR-0032). The prototype evidence shows the two choices affect the identical 18
   slides, so there is no corpus-size argument for keeping additive; the qualitative
   difference (every table grows under additive versus most shrinking under
   `max(min, share)`) is a real design choice, not a magnitude one, and `max(minimum,
   share)` is preferred because it matches the schema's own CSS-Grid-derived vocabulary
   and does not let a minimum correction became an unbounded growth channel.
2. **Scope of the engine change.** The isolation check (design plan, item 3; evidence,
   "Corpus impact: which slides change") is the direct answer to "does this leak beyond
   tables": it does not, because no other flexible track in the public corpus declares a
   nonzero `minmax` minimum today. This is stated as a corpus fact, not an engine
   guarantee — a future profile that gives a legend or plot track a nonzero `minmax`
   minimum would newly become sensitive to this rule, which is intended and is exactly
   what Specification 33 §5's amendment now documents.
3. **Whether this belongs in Specification 24 or 33.** Both: §24 §2.1 states the
   table-specific consequence (minimum-inline equals measured content); §33 §5 states the
   general engine rule (`max(minimum, share)`) that makes §24's consequence hold once
   `minmax` is applied. Splitting them keeps the table-specific spec free of allocator
   arithmetic and the general spec free of one source's measurement details.
4. **ADR versus design-note only.** An ADR is added (ADR-0032) because the allocation-rule
   change is a public, engine-wide semantics change with a stated migration impact
   (`AGENTS.md`'s bar for recording a decision, not only a design note), even though its
   *effect* in the current corpus is scoped to tables.

## Risks and gates

- **Visible shrink, not just less growth.** 17 of 18 affected tables become narrower than
  their currently published width under the chosen rule (26.7–151.4 px). This is a
  legitimate output change, but it is a *different* kind of change than "the table no
  longer overflows its own columns" — it also makes some tables visually tighter than
  today. The implementation slice must render and inspect before/after PNGs, not rely on
  the Scene diff alone, and the slice review must say explicitly that this is accepted,
  not merely detected.
- **Diagnostic churn is bidirectional.** Some slides gain a suppression under the chosen
  rule that they did not have before (e.g. `halcyon-1/gallery-dark`, `halcyon-1/mission-brief`
  newly suppress a member label), because a narrower table gives the timeline more room,
  which can make an axis-adjacent label newly reachable in a place it previously was not,
  changing which candidate collides. Each new/removed diagnostic in the batch must be
  attributed to this width change specifically.
- **`_allocate` correctness for `maximum`.** The `min(target_size, maximum)` clip after
  `max(minimum, share)` must still hold when `minimum > maximum` (a malformed profile);
  the implementation should confirm the existing `E_LAYOUT_SCHEMA`/validation path already
  rejects a `minmax` where `min > max`, so this case cannot reach `_allocate` at runtime.

## Open question for the lead or issue owner

Is it acceptable that the chosen, standards-aligned fix makes several published tables
**narrower** than they are today (not only "less wide than an over-eager fix")? The
alternative (additive allocation) avoids that specific regression but reproduces the
uncontrolled-growth behavior the issue itself was filed to flag, with an identical
corpus-size impact either way. The design plan and this review recommend
`max(minimum, share)`; the design doc and ADR-0032 are written to that recommendation, but
this trade-off should be confirmed before implementation, since it is a visible, one-way
change to nine public layouts and two `print-mono` slides.

No other unresolved user choice remains.
