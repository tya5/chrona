<!-- chrona:literal-acceptance/v1 -->

# Release Review — Group header role-marked spans

Implementation: [PR 1204](https://github.com/tya5/chrona/pull/1204), merge commit `6206943c83968bc4905bdaa775c9804a043c5431`, base `576b3bdc262ae523e540128e9d982afdc9007211` (derived-main ready). Final PR run [37645748471](https://github.com/tya5/chrona/actions/runs/37645748471) on head `79a3a8f6`: classify, derived-preview, conformance, three pytest shards, newest-Python reproduction and `derived-ready` all passed. Design, options and reversal: [Status comment](https://github.com/tya5/chrona/issues/1192#issuecomment-6038509770).

## Literal issue acceptance

### Issue #1192

- Source: [Issue #1192](https://github.com/tya5/chrona/issues/1192)
- Observed: 2026-10-08

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A marked template emits one Text run per span, on one baseline, in order, each with its role's ink and size. | met | [Integration tests](https://github.com/tya5/chrona/blob/6206943c83968bc4905bdaa775c9804a043c5431/tests/integration/test_group_header_runs.py) (`#run0..#run2`, one baseline, role sizes 22/15/11, SVG fills per run, `textLength` per run under `text-follows-box`); [placement tests](https://github.com/tya5/chrona/blob/6206943c83968bc4905bdaa775c9804a043c5431/tests/unit/chrona/presentation/layout/test_group_header_run_placement.py); evidence slide read as an image (orange bold ordinal, white title, small muted gloss on one baseline) and under serif and monospace fallback faces. | — |
| 2 | The header block's measured width is the sum of the spans and gaps. | met | [Exact-arithmetic test with a fake face](https://github.com/tya5/chrona/blob/6206943c83968bc4905bdaa775c9804a043c5431/tests/unit/chrona/presentation/layout/test_group_header_run_placement.py): runs at 100, 125, 150 for widths 20, 15 and gaps 5, 10; [integration sum test](https://github.com/tya5/chrona/blob/6206943c83968bc4905bdaa775c9804a043c5431/tests/integration/test_group_header_runs.py) on the completed Scene. | — |
| 3 | An unknown role is an error at its pointer. | met | [Integration tests](https://github.com/tya5/chrona/blob/6206943c83968bc4905bdaa775c9804a043c5431/tests/integration/test_group_header_runs.py): `E_THEME_ROLE_REQUIRED` at `/body/grouping/header/text`, and `/first` for the first-group variant, Theme pointer in the detail; an ink-less role fails the same way. | — |
| 4 | An unmarked template is byte-identical. | met | [PR run 37645748471](https://github.com/tya5/chrona/actions/runs/37645748471) derived-preview and `regenerate_public_examples.py --check` (67 slides): no existing public Scene or SVG differs; [grammar tests](https://github.com/tya5/chrona/blob/6206943c83968bc4905bdaa775c9804a043c5431/tests/unit/chrona/presentation/test_group_header_runs_text.py) show every existing template parses to an equal template. | — |
| 5 | Title Card adopts the orange ordinal. | narrowed | The reviewer's step (the feature is on `main`; no `examples/halcyon-1` file was edited by this work), tracked on the Title Card target [Issue #1182](https://github.com/tya5/chrona/issues/1182). | [#1182](https://github.com/tya5/chrona/issues/1182) |

## Programme-level criteria (optional)

Schema: description-only change to `grouping.header.text`; `python -m tools.schema_equivalence --base-rev origin/main` passed, no expected-delta entry. Mutation check: 14 mutants over gaps, give-way order, baseline, role admission, tab bound, vertical refusal, scene role, consumer lookup, role parse and run merge were all killed. Typst and TikZ draw each run as an ordinary positioned text at Layout's offset; they were not rendered here, and a face of other metrics drifts the gaps unless the roles use `text-follows-box` (Specification 50 section 3.4).
Required closure gate: the three-OS pytest/conformance/wheel/materializer run on the exact published commit containing this review; the closing comment must cite that receipt.

## Architecture conclusion

View owns the template grammar and its roles, Theme declares the roles and their ink, Layout owns measurement, gaps, baseline and overflow, Scene emits ordinary Text primitives, and adapters and the contrast gate need no new contract. A vertical group tag refuses marked spans (`E_LAYOUT_GROUP_HEADER_RUNS_VERTICAL`); a figure id may not contain `|`. Specifications 07 and 50 carry the rule.
