<!-- chrona:literal-acceptance/v1 -->
# Render feedback acceptance (#1299)

Authority: pre-code `c14a86aa`, Specs06 §6.1 and33 §13; [living work record](https://github.com/tya5/chrona/issues/1299#issuecomment-6095558700). Implementation: observer/routing `b3d401fc`/`dc31c097`, CLI `99e111c0`, relation override `d67cdf94`, height policy `8eaa30a3`; retained table-bound correction `29d02e9d`. Integrated with #1302/#1306 on trusted READY `b694b8589479bdf6bcf67ef9b1f3557067662f76`. PR/artifact and exact-main release acceptance remain pending.

## Literal issue acceptance

### Issue #1299

- Source: [Issue #1299](https://github.com/tya5/chrona/issues/1299)
- Observed: 2026-10-12

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A CLI test with a pseudo-terminal sees phase lines on stderr. A non-terminal run produces byte-identical stdout and stderr to today. | met | [Actual CLI tests](../../../tests/integration/test_render_progress_cli.py): real PTY; unobserved/quiet/explicit-progress stdout and SVG equality; unchanged quiet stderr. Progress is isolated from the separately declared height-policy migration. | — |
| 2 | A CLI test: `--relations none` on a plan with relations yields a Scene with no relation primitives and no `W_LAYOUT_RELATION_SUPPRESSED`. Without the flag the Scene is unchanged. | met | [CLI tests](../../../tests/integration/test_render_progress_cli.py): absent/semantic Scene identity; no relation primitives/suppression and zero-relation passes for none; authored-hidden scalar/object Views re-enabled without writes. [Ingress unit tests](../../../tests/unit/chrona/presentation/model/test_draft_relation_override.py) preserve options and effective identity. | — |
| 3 | A test: a plan whose rows exceed the declared limit yields the tall-canvas warning with the row count. A plan within the limit yields none. | met | [Completed Layout/Scene/SVG tests](../../../tests/integration/test_auto_block_limit_render.py) assert warning facts, strict equality/no warning, unchanged primitives/canvas/SVG; actual CLI default2/120 rows checks declared3600 against completed height. [Boundary/token/admission tests](../../../tests/unit/chrona/presentation/layout/test_auto_block_limit.py) cover omission, zero, finite block and required tokens. | — |
| 4 | Do not edit `examples/**`. | met | [Implementation](https://github.com/tya5/chrona/commit/8eaa30a3): authored diff against merged source main contains no examples paths. | — |

## Programme-level criteria (optional)

Current integration:129 focused cases pass59.52s; two shared-design assertions
against stale committed generated evidence remain unchanged and require the
CI-owned snapshot. Progress/PTY/relations, height-limit, observer and default
cases pass. Contributor/import/CI-selection/MCP batch328 passes92.16s.
Imports11 packages/37 inward edges, Layout floats and literal reviews pass.
Schema gate after design-reuse adoption passes:one additive/one declared
changed/36 equal schemas,739 probes and four unchanged known-invalid documents.
The supported tool proves and retires5 merged design-reuse L1 entries; no
baseline refresh or authored examples/report changes.

The completed-height test uses2/120 rows after #1302's derived pitch; its old
60-row case is correctly below3600. No threshold or geometry was changed to
satisfy a test. The standalone default preserves maxInlineShare0.4; omitted
limits are inert and network-auto admission remains unchanged.
Earlier CI38163628369's9 failures were explicit stub/default-identity migrations,
authored CLI reference generation and real Scene-field delivery registration;
all48 affected/related tests pass25.85s. Managed inventories are not patched.

Architecture: CLI owns terminal I/O; Draft overrides View before identity/admission;
Core dependencies remain unchanged. Layout compares completed geometry with
declared limits; Scene carries typed evidence. No resizing, clocks, adapter
placement or implemented paging; the paging follow-up is specified in Spec33.
Current-head PR artifacts/checks and containing-review exact-main three-OS
release remain required before closure.
