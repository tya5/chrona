# Font stack resolution review

<!-- chrona:literal-acceptance/v1 -->

Plan, design and architecture: [living record](https://github.com/tya5/chrona/issues/1495#issuecomment-6170861324).
[Approved clarification](https://github.com/tya5/chrona/issues/1495#issuecomment-6180564063)
preserves Spec30 and1281: exhausted coverage includes the packaged face; existing
per-glyph fallback stays unchanged. Published implementation: [PR1505](https://github.com/tya5/chrona/pull/1505)
and [PR1508](https://github.com/tya5/chrona/pull/1508).
Accepted public base: `4aab0b9b98a9f342ce65fa29572a53e4c9819e35`.

The actual selected family/weight is addressable by completed-text consumers;
`setdefault` preserves declared exact metrics. Only unavailable named prefixes
produce the skip warning. Attempted names affect failure detail, not geometry,
coverage or adapters. Raw composition font failures use the existing usecase
normalization; Layout/Scene never discover host fonts. Independent review found
no blocker. Focused tests:122PASS.

The catalog collects each metric object's glyph warnings once, rather than
once per lookup alias. Distinct metric objects retain multiplicity.
This is catalog bookkeeping, not a glyph fallback or renderer change. The
[regression test](../../../tests/unit/chrona/presentation/model/test_font_metrics.py)
and installed CJK render test cover alias deduplication;54 focused tests pass.
Independent architecture review found no blocker. Both current-head PR checks
and their snapshot byte inspections passed.

## Literal issue acceptance

### Issue #1495

- Source: [issue](https://github.com/tya5/chrona/issues/1495), including the approved clarification above
- Observed: 2026-10-15

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | Synthetic test: a Theme list `Missing Family, <installed or declared family>` resolves to the second family with the warning. A list where nothing is available still fails with a diagnostic that names every family tried. | met | [Synthetic integration tests](../../../tests/integration/test_installed_fonts.py): installed and declared later faces, actual-family viewer-fit lookup, no warning for the first available face, PDF rendering and ordered exhausted-glyph candidates. Reviewer clarification means no face including packaged can supply the glyph; packaged/per-glyph tests remain. [Warning message test](../../../tests/unit/chrona/usecases/test_diagnostic_messages.py) verifies requested/skipped/selected names. | — |
| 2 | The four rows above, rerun: rows 2–4 render, and row 1 is unchanged (its only CJK-capable family is missing). | met | [Recorded verification](https://github.com/tya5/chrona/issues/1495#issuecomment-6170861324): actual macOS CLI with roadmap Project, marquee preset and Title Card overrides; only editorial value substituted in memory. Row1 exit1, E_FONT_GLYPH_UNAVAILABLE U+7B2C, tried `[Noto Sans JP, Noto Sans]`; row2 exit0, W_FONT_FAMILY_SKIPPED names Noto Sans JP and selected Hiragino Sans; rows3/4 exit0. No tracked inputs edited. | — |
| 3 | Public examples that declare their font assets in Context are byte-identical. | met | [Recorded verification](https://github.com/tya5/chrona/issues/1495#issuecomment-6170861324): own-worktree `.venv/bin/python tools/regenerate_public_examples.py --check --jobs 4`: all50 slides PASS. [Final correction snapshot](https://github.com/tya5/chrona/pull/1508#issuecomment-6181221336): all100 SVG/Scene files byte-identical; only source-line refreshes in two generated reports. | — |
| 4 | Do not edit `examples/**`. | met | [Source commit](https://github.com/tya5/chrona/commit/cd3316d9ba7bae8ed7cda373bda9badac1437f9d) contains only font resolution/metrics, usecase diagnostics, Spec30 and synthetic tests; materializer check writes no authored examples. | — |

## Programme-level criteria (optional)

None.

Release accepted: [38658997444](https://github.com/tya5/chrona/actions/runs/38658997444)
on the exact review-containing public base above passed Ubuntu/macOS/Windows
full pytest, conformance and wheel/smoke, newest-Python public materializers,
and the MCP floor. Actual public-main API/CLI viewport checks also passed
(125 renders,25 exact expected refusals,zero failures in each mode).
Issue1495 was deliberately closed after this release on2026-10-15.
