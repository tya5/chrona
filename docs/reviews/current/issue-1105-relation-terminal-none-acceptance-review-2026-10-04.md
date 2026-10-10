<!-- chrona:literal-acceptance/v1 -->

# Issue #1105: relation terminal shape `none`, acceptance review

Source: [Issue #1105](https://github.com/tya5/chrona/issues/1105), re-fetched 2026-10-04 after the merge (body unchanged; comments: this work's claim and status lines, no new acceptance rows). Work record: [issue-1105-relation-terminal-none-2026-10-04.md](../planning/active/issue-1105-relation-terminal-none-2026-10-04.md).

Slices: design [PR #1115](https://github.com/tya5/chrona/pull/1115); implementation [PR #1124](https://github.com/tya5/chrona/pull/1124) (`6cb0dc3d`), CI green before merge (conformance, three pytest shards, newest-Python reproduction, derived-ready).

## Literal issue acceptance

### Issue #1105

- Source: [Issue #1105](https://github.com/tya5/chrona/issues/1105)
- Observed: 2026-10-04

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | With the source terminal `none`, a relation has no source-terminal primitive, and its first point is the source port. | met | [`test_relation_terminal_none.py`](../../../tests/unit/chrona/presentation/scene/test_relation_terminal_none.py): composed by the real surface composer, `marker_start` is `None` and the first route point equals the span's end edge at mid height; the target arrowhead is kept. Dropping the `none` branch fails 6 of 18 tests. | none |
| 2 | With the target terminal `none`, the same holds at the target. | met | [`test_relation_terminal_none.py`](../../../tests/unit/chrona/presentation/scene/test_relation_terminal_none.py): `marker_end` is `None` and the last route point is the target's start edge at mid height; both `none` draws a plain stroke, with a corner radius the ends stay at the ports and the last corner may round because no head run is reserved (a strict-inequality test that catches a reserved run). | none |
| 3 | Every other shape gives byte-identical output. | met | [`test_relation_terminal_none.py`](../../../tests/unit/chrona/presentation/scene/test_relation_terminal_none.py) parametrized over every other shape: the composed markers equal their own resolution. No committed Theme declares `none`, so no existing slide can change; the only generated addition is the new slide below. The vocabulary widening is one expected-delta entry and `schema_equivalence` passes. | none |
| 4 | Target B declares a `none` source terminal and matches the mock. | deferred | `examples/halcyon-1/themes/target-b.yaml` is the reviewer's file ([`target-b.yaml`](../../../examples/halcyon-1/themes/target-b.yaml)); it was not edited. The knob is available for the reviewer's PR [#1061](https://github.com/tya5/chrona/pull/1061). Evidence the shape works end to end: Controller Z slide `terminal-none` through YAML ([`terminal-none.yaml`](https://github.com/tya5/chrona/blob/abbe91a40b46621e448eded6dcfb42b1dd97bb7b/examples/controller-z/themes/terminal-none.yaml)), image read: no source dots, target arrowheads kept. | [#1077](https://github.com/tya5/chrona/issues/1077) |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Layout owns the decision: `marker_geometry` resolves `none` to the existing "no marker" value, so Scene and the adapters are unchanged. SVG, PNG and PDF omit the marker. Typst and TikZ reject only primitives that carry a marker, so a relation whose terminals are both `none` is drawn there as a plain path (tested); a mixed relation is rejected as before. The legend key of a `none` role is the plain stroke (tested). The marker object keeps its four required fields for `none` (the numbers are validated and ignored), because relaxing `required` would not be an additive schema change.

Disclosures: no committed slide other than the new `terminal-none` changed, by construction (no committed Theme uses `none`); I did not regenerate and diff the whole corpus for this issue.

#1105 stays open: row 4 is deferred to the reviewer-owned #1077 and the repository rule keeps the issue open unless the owner approves closing it on the successor. Exact review-bearing-main three-OS CI is recorded on the issue when it runs.
