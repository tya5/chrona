<!-- chrona:literal-acceptance/v1 -->

# Release review — edge spaces between role-marked group-header runs

Implementation: [#1247](https://github.com/tya5/chrona/pull/1247) (merge `25b7f771`). The run layout already turned edge spaces into gaps but measured a gap as the space advance only; a letter-spaced role paints spacing after the glyph before the space and after the space, so one space shrank to about 1px. A gap between two runs is now the whitespace advance plus the letter spacing after each whitespace character plus the letter spacing after the glyph before it, only when whitespace exists. Rule: Specification 50 section 3.4. Plan: [Status comment](https://github.com/tya5/chrona/issues/1238#issuecomment-6065343348).

The Marquee View's double-space workaround is in `examples/**`, which is reviewer-owned; it is the reviewer's step, not a dev row. The issue stays open until that step lands.

## Literal issue acceptance

### Issue #1238

- Source: [Issue #1238](https://github.com/tya5/chrona/issues/1238)
- Observed: 2026-10-09

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | "A {x&#124;r} B" lays out the run `A `, the run `x` and the run ` B` with the measured space widths between them. | met | [Diff](https://github.com/tya5/chrona/pull/1247/files): `layout/group_header_runs.py` `_resolve_runs`; `tests/unit/chrona/presentation/layout/test_group_header_run_placement.py::test_edge_spaces_of_a_template_are_the_measured_gaps_between_its_runs`, `..._letter_spacing_a_painted_line_would_put_around_the_space`, `..._leading_space_of_the_first_run...`; end to end `tests/integration/test_group_header_runs.py`. The run text is the stripped core; the edge spaces are the gaps, as before. | — |
| 2 | Templates without &#124; are byte-identical. | met | [PR body](https://github.com/tya5/chrona/pull/1247): templates without &#124; do not use the run layout; a materialize pass over all 68 corpus slides changed only the two that use the role separator (halcyon-1 marquee, 12 run primitives; titlecard, 6), never a slide without &#124;. | — |
| 3 | Marquee drops its double-space workaround. | deferred | [`examples/halcyon-1/views/24-marquee.yaml`](../../../examples/halcyon-1/views/24-marquee.yaml) `text: 'ACT  {ordinal&#124;group-ordinal}  · {title}'` is unchanged: `examples/**` is reviewer-owned (AGENTS.md fast path). With the fix, the single-space template renders the spaces; verified locally on a scratch copy and reverted. | [Owner note on the issue](https://github.com/tya5/chrona/issues/1238#issuecomment-6065343348): the reviewer edits the View to single spaces and regenerates marquee and titlecard evidence with derived-sync. |

## Programme-level criteria (optional)

None.
