<!-- chrona:literal-acceptance/v1 -->

# Issue #1626 — grouped import acceptance

Implementation: [PR #1650](https://github.com/tya5/chrona/pull/1650), head
`a4bc049e6d7ba65a6b2d341c281e69bc19d0962a`; squash commit
`ba895af3a52075b1f6bfbb6dcf130dd451a89026` has the same tree. Published on
ready main `cf1218655`. This review is present on exact review-containing main
`98cf1ce517dafd82cc0e887cc16b859a40b67e15`; see the [closure record](https://github.com/tya5/chrona/issues/1626#issuecomment-6232842711).

Final PR CI [39021307150](https://github.com/tya5/chrona/actions/runs/39021307150)
passed all three pytest shards, conformance, public reproduction, MCP floor and
derived-ready. Its official snapshot is artifact [12097325673](https://github.com/tya5/chrona/actions/runs/39021307150/artifacts/12097325673).
The exact review-containing main passed required release
[39022491953](https://github.com/tya5/chrona/actions/runs/39022491953): Linux,
macOS and Windows full pytest/conformance/wheel, newest-Python public
materializer reproduction and oldest-supported MCP SDK checks all succeeded.

## Literal issue acceptance

### Issue #1626

- Source: [Issue #1626](https://github.com/tya5/chrona/issues/1626), with [reviewer replacement of row2](https://github.com/tya5/chrona/issues/1626#issuecomment-6230791458)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Trace posted; synthetic twins for grouped import with and without a responsible role. | met | [Trace and architecture](https://github.com/tya5/chrona/issues/1626#issuecomment-6229468273); [neutral integration twins](https://github.com/tya5/chrona/blob/a4bc049e6d7ba65a6b2d341c281e69bc19d0962a/tests/integration/test_role_group_summary_order.py) cover declaration/explicit/time order, bound-role omission/count, selection, direct-field/none controls and role-normalization idempotence. The Sunday role/direct-field matrix retains required-barrier, quality-fallback, route-completeness and safety guards. | — |
| 2 | on the trial CSV, target-b without `--role` shows Design, Build and Release in CSV order. With `--role responsible=owner`, target-b and sunday show no group-summary bars in an Unassigned lane, and the diagnostic is present. Viewed as PNG. | met | Exact [trial3 inputs](https://github.com/tya5/chrona/tree/dbbce45e60392b7b0be788f841fe2673f4830944/trial3), project-only README renders: target-b no-role shows Design→Build→Release; target-b/sunday with-role omit all 3 summary bars and emit `I_VIEW_FIELD_GROUP_SUMMARIES_OMITTED` with count 3. All 3 PNGs viewed; no declared grouping-none design changed. See [closure evidence](https://github.com/tya5/chrona/issues/1626#issuecomment-6232842711). | — |
| 3 | Public SVG/Scene changes listed with counts. | met | [Final-head official snapshot](https://github.com/tya5/chrona/actions/runs/39021307150/artifacts/12097325673): all 50 SVG and 50 Scene pairs byte-identical; each slide has zero routes, labels or primitives changed/added/removed. Only inventory references change. | — |

## Programme-level criteria (optional)

On exact review-containing main `98cf1ce517dafd82cc0e887cc16b859a40b67e15`,
[release 39022491953](https://github.com/tya5/chrona/actions/runs/39022491953)
passed Linux (12,814 pytest), macOS (12,819), and Windows (12,812), with
conformance and wheel checks on all three; newest-Python public-materializer
reproduction and the oldest-supported MCP SDK checks also passed. The closure
decision and the trial-only routing tradeoff are recorded in the [issue closing
comment](https://github.com/tya5/chrona/issues/1626#issuecomment-6232842711).

## Architecture conclusion

Role-origin normalization preserves the declared grouping contract; projection
owns declaration order and selected summary omission. Typed info carries a count,
not Layout policy. No nested grouping mechanism, schema migration, preset copy,
source mutation or Scene/adapter geometry rule. Nested Project-group plus lane
presentation is only a successor candidate; it is not implemented or required
here. The diagnosed no-role target-b routing tradeoff remains documented: one
through-mark warning is added while the number of overlap resolutions remains
unchanged. No project-specific patch is warranted.
