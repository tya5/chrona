# Font stack resolution review

<!-- chrona:literal-acceptance/v1 -->

Plan, design and architecture: [living record](https://github.com/tya5/chrona/issues/1495#issuecomment-6170861324).
[Approved clarification](https://github.com/tya5/chrona/issues/1495#issuecomment-6180564063)
preserves Spec30 and1281: exhausted coverage includes the packaged face; existing
per-glyph fallback stays unchanged. Source: cd3316d9ba7bae8ed7cda373bda9badac1437f9d,
based on READY9e6431abc8e16afcaaff5985f91cba83a05226ea.
Normal merge adopts READYe907c6c10e6df56bcb1258f65630a809a4b36868 (PR1504's
independent Windows UTF-8 report correction). Post-adoption focused checks44PASS;
the approved font behavior and existing byte evidence remain unchanged.

The actual selected family/weight is addressable by completed-text consumers;
`setdefault` preserves declared exact metrics. Only unavailable named prefixes
produce the skip warning. Attempted names affect failure detail, not geometry,
coverage or adapters. Raw composition font failures use the existing usecase
normalization; Layout/Scene never discover host fonts. Independent review found
no blocker. Focused tests:122PASS.

Post-merge correction: source0eb6f2cfe50d3a1b22f2b1a1c273dc4eca017987
collects each metric object's glyph warnings once, rather than once per alias.
Self-review reproduced one substitution reported2 times before the new alias
and3 afterwards; both now report1. Distinct metric objects retain multiplicity.
This is catalog bookkeeping, not a glyph fallback or renderer change. The
[regression test](../../../tests/unit/chrona/presentation/model/test_font_metrics.py)
and installed CJK render test cover alias deduplication;54 focused tests pass.
Independent architecture review found no blocker. The pre-correction release
on2c81f9d3 cannot accept this correction: require its own current-head checks,
snapshot inspection and review-containing exact-main three-OS release.

## Literal issue acceptance

### Issue #1495

- Source: [issue](https://github.com/tya5/chrona/issues/1495), including the approved clarification above
- Observed: 2026-10-15

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | Synthetic test: a Theme list `Missing Family, <installed or declared family>` resolves to the second family with the warning. A list where nothing is available still fails with a diagnostic that names every family tried. | met | [Synthetic integration tests](../../../tests/integration/test_installed_fonts.py): installed and declared later faces, actual-family viewer-fit lookup, no warning for the first available face, PDF rendering and ordered exhausted-glyph candidates. Reviewer clarification means no face including packaged can supply the glyph; packaged/per-glyph tests remain. [Warning message test](../../../tests/unit/chrona/usecases/test_diagnostic_messages.py) verifies requested/skipped/selected names. | — |
| 2 | The four rows above, rerun: rows 2–4 render, and row 1 is unchanged (its only CJK-capable family is missing). | met | [Recorded verification](https://github.com/tya5/chrona/issues/1495#issuecomment-6170861324): actual macOS CLI with roadmap Project, marquee preset and Title Card overrides; only editorial value substituted in memory. Row1 exit1, E_FONT_GLYPH_UNAVAILABLE U+7B2C, tried `[Noto Sans JP, Noto Sans]`; row2 exit0, W_FONT_FAMILY_SKIPPED names Noto Sans JP and selected Hiragino Sans; rows3/4 exit0. No tracked inputs edited. | — |
| 3 | Public examples that declare their font assets in Context are byte-identical. | met | [Recorded verification](https://github.com/tya5/chrona/issues/1495#issuecomment-6170861324): own-worktree `.venv/bin/python tools/regenerate_public_examples.py --check --jobs 4`: Public materializers PASS, all50 slides. Tracked example diff remains empty. Validation source was unchanged while its commit was recorded as cd3316d9. CI preview must independently confirm intended byte identity before merge. | — |
| 4 | Do not edit `examples/**`. | met | [Source commit](https://github.com/tya5/chrona/commit/cd3316d9ba7bae8ed7cda373bda9badac1437f9d) contains only font resolution/metrics, usecase diagnostics, Spec30 and synthetic tests; materializer check writes no authored examples. | — |

## Programme-level criteria (optional)

None.

Release acceptance remains pending: keep issue1495 open until current-head PR
checks, preview byte inspection, publication and the exact review-containing
main three-OS full release succeed. A passing local test is not that release.
