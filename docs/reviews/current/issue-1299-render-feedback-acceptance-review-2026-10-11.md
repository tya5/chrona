<!-- chrona:literal-acceptance/v1 -->
# Render feedback acceptance (#1299)

Authority: pre-code `c14a86aa`, Specs06 §6.1 and33 §13; [living work record](https://github.com/tya5/chrona/issues/1299#issuecomment-6095558700). Implementation: observer/routing `b3d401fc`/`dc31c097`, CLI `99e111c0`, relation override `d67cdf94`, height policy `8eaa30a3`; current READY7563df4c adoption `85bd7220`, retained default table-bound correction `29d02e9d`.

## Literal issue acceptance

### Issue #1299

- Source: [Issue #1299](https://github.com/tya5/chrona/issues/1299)
- Observed: 2026-10-11

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A CLI test with a pseudo-terminal sees phase lines on stderr. A non-terminal run produces byte-identical stdout and stderr to today. | met | [Actual CLI tests](../../../tests/integration/test_render_progress_cli.py): real PTY; unobserved/quiet/explicit-progress stdout and SVG equality; unchanged quiet stderr. Progress is isolated from the separately declared height-policy migration. | — |
| 2 | A CLI test: `--relations none` on a plan with relations yields a Scene with no relation primitives and no `W_LAYOUT_RELATION_SUPPRESSED`. Without the flag the Scene is unchanged. | met | [CLI tests](../../../tests/integration/test_render_progress_cli.py): absent/semantic Scene identity; no relation primitives/suppression and zero-relation passes for none; authored-hidden scalar/object Views re-enabled without writes. [Ingress unit tests](../../../tests/unit/chrona/presentation/model/test_draft_relation_override.py) preserve options and effective identity. | — |
| 3 | A test: a plan whose rows exceed the declared limit yields the tall-canvas warning with the row count. A plan within the limit yields none. | met | [Completed Layout/Scene/SVG tests](../../../tests/integration/test_auto_block_limit_render.py) assert warning facts, strict equality/no warning, unchanged primitives/canvas/SVG; actual CLI default60 rows reports declared3600 and actual height. [Boundary/token/admission tests](../../../tests/unit/chrona/presentation/layout/test_auto_block_limit.py) cover omission, zero, finite block and required tokens. | — |
| 4 | Do not edit `examples/**`. | met | [Implementation](https://github.com/tya5/chrona/commit/8eaa30a3): authored diff against merged source main contains no examples paths. | — |

## Programme-level criteria (optional)

Current own Python3.11 focused suite:107 PASS42.44s, covering progress/PTY,
height limits, relation override, packaged table bounds and explicit-window
relation/lane/Scene absences. Merge keeps completed paint/absence geometry and
separate progress-pass identity; plot bounds retain their positional handoff.
The standalone default preserves merged table maxInlineShare0.4, adding only
the declared height limit and truthful Layout ID; the whole-resource equality
test remains intact. Network auto remains rejected; finite network requests
do not receive this advisory.

Architecture: CLI owns terminal I/O; Draft overrides View before admission/effective identity freeze; Core dependencies/schedules are unchanged. Layout alone compares completed geometry against resolved declared limits; Scene transports typed facts. No resizing, route changes, clocks, serialization authority or implemented paging. Default Layout provenance intentionally changes; catalogue Editorial and mirrors remain unchanged. Paging follow-up is specified in Spec33.

Current import check:11 packages/37 inward edges. Full schema gate against
origin/main7563df4c PASS:one additive Layout schema,37 equal,483 documents
(379 mapped),739 probes (462 rejected/277 accepted), four known-invalid
unchanged; L2+L3=50.2s against unchanged60s budget. The provided tool proves
and retires19 merged L1 entries; L2/L3 predecessor records remain intact.
Authored examples diff is empty. Current PR/public-artifact and containing-review
exact-main three-OS release remain required; no second active PR is opened.
