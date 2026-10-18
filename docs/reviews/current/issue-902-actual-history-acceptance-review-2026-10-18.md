<!-- chrona:literal-acceptance/v1 -->

# Issue 902 — Actual history (item 3)

This accepts neither item2 nor the parked item4/#814/#815; the parent stays open.

## Literal issue acceptance

### Issue #902

- Source: [issue902](https://github.com/tya5/chrona/issues/902)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Acceptance for 2, 3 and 5: each has its own stale-base, replay and no-overwrite tests, plus an MCP stdio test where it is a tool. | met | Item3 focused evidence only: [fresh-base/state checks, durable replay and immutable revisions](../../../tests/unit/chrona/operational/test_actual_history_engine.py); [real processes](../../../tests/integration/test_actual_history_concurrency.py); [real MCP stdio revert/redo and write gate](../../../tests/mcp/test_mcp_stdio_e2e.py). Item5's separate two-process criterion is reviewed in the work record. | — |

## Programme-level criteria (optional)

Design `a79ab0307`, implementation plan `504478877`, implementation
`c2984c018`, focused review `db9caca1d` and scheduling amendment `f03a8fc86`
are published in that order. The [living work record](../../planning/active/issue-902-store-write-safety-work-record-2026-10-18.md)
contains focused counts and the normative Spec35/10/15/66 consistency review.
Store adapters own persistence, the shared operational engine owns durable
intent/ancestry/CAS validation, and CLI/MCP retain the same gate and dispatch.
Redo revalidates intent; revert creates a new immutable revision. Legacy
unrecoverable intent is diagnosed, not guessed. No renderer or project YAML
changes; generic Project history is unchanged.

Final item3 head `1489598c75744cc3323d79a5fd1df784d8a7d72e` passed
[PR CI39105280589](https://github.com/tya5/chrona/actions/runs/39105280589).
Official artifact12128521189 has all50 SVG/Scene pairs unchanged and only two
intended diagnostic inventories changed. Item3 merged as PR1706 at
`ea6873b5d5767258408dc5709d0361ee0b8bf20e`. The review-containing exact main
`5fe41db8e8512e5438e9ecbe67f5c56c1d18d152` passed
[full release39108421823](https://github.com/tya5/chrona/actions/runs/39108421823):
all three native OS pytest/conformance/wheel gates, MCP floor and newest-Python
public-materializer reproduction. **Item3 is accepted independently.** This
does not accept item2 or parked item4/#814/#815; parent #902 remains open.

The initial PR CI findings concerning diagnostic classifications and schema
migration expectations were corrected before final CI; supported v0.3 dispatch
and the unchanged baseline-invalid population remain covered. The final artifact,
merge and exact-main release above establish item3 acceptance. Item5 and item3
are accepted independently; item2 is tracked in its own review and remains
pending its exact-main full-release result. Parked item4/#814/#815 remain outside
this review, and parent #902 remains open.
