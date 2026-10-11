<!-- chrona:literal-acceptance/v1 -->
# First-run defaults acceptance (#1302)

Implementation through `7cb26df9`, integrated normally with #1299/#1306 on
trusted READY `b694b8589479bdf6bcf67ef9b1f3557067662f76`.
[Current design, architecture review and implementation plan](https://github.com/tya5/chrona/issues/1302#issuecomment-6095688853).
The rows below record local evidence only; public-artifact review, current-head CI
and exact-main three-OS release remain required. This is not permission to close.

## Literal issue acceptance

### Issue #1302

- Source: [Issue #1302](https://github.com/tya5/chrona/issues/1302)
- Observed: 2026-10-12

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A test: `chrona init` + `chrona render` with and without `--actual` emits no warnings, and the progress fill of `design` is present in the Scene. | met | [Actual starter CLI/Scene/SVG test](../../../tests/cli/test_cli.py#L401), both Actual modes. | — |
| 2 | A test over all valid conformance projects: a default render emits no diagnostic whose cause is a default Theme token (contrast/decoration codes on default-owned primitives). | met | [All6 valid Projects through actual validated SVG](../../../tests/integration/test_first_run_conformance_theme.py), including verified extension package. | — |
| 3 | A test: a project with groups renders group header rows in the default; a flat project's Scene is unchanged. | met | [Nested headers, complete flat Scene/SVG identity, Actual and unpainted scheduled-port tests](../../../tests/integration/test_first_run_hierarchy.py). | — |
| 4 | A test: `order.yaml` above renders rows in start order under every builtin preset, and no "Items" column where each lane has one item. | met | [Exact issue fixture across all8 presets, actual Scene/SVG order and count-column checks](../../../tests/integration/test_first_run_lane_order.py). | — |
| 5 | A test: PNG with `technical-print` and `elevated-light` succeeds without `--visual-profile` and records the fallback. | met | [Actual PNG signatures and CLI fallback diagnostics](../../../tests/cli/test_cli.py#L937); explicit incompatible profile remains rejected. | — |
| 6 | A test asserts that the default row pitch equals the documented rule's value for two different Theme text sizes. | met | [Measured Scene/SVG pitch at14px/40px typography and changed mark/padding](../../../tests/integration/test_first_run_row_pitch.py). | — |
| 7 | Do not edit `examples/**`. | met | [Published implementation diff](https://github.com/tya5/chrona/compare/fa862e40745aa134198dfe070aa347c451dd7ffe...7cb26df9d8afc840b9d3fd71796cb3ab2dbf2f24): no authored examples changes. | — |

## Programme-level criteria (optional)

CI38170085140 has28 failures across its three shards; conformance, MCP and
newest-Python reproduction pass. [Correction plan](https://github.com/tya5/chrona/pull/1423#issuecomment-6113256906)
is implemented in `51b4e517`: canonical Core identity assertions, shared exact
preset-copy guard, matched historical View/Theme, group-header/date coverage,
actual SVG row-rule verification and14 approved CLI records. The unrelated
chip fixture retains its original byte hashes with explicit count:true.
No product, schema, authored examples or managed-report changes.34 focused
regressions pass41.92s. Isolated validation on this source with the unaltered
CI-owned snapshot11713338434:287 affected CLI/shared-design/public-preset/
readable-default/first-run tests pass113.25s; contributor guards35 pass6.91s.
Current-head CI and exact-main release remain required.
[All46 generated Scene/SVG pairs](https://github.com/tya5/chrona/pull/1423#issuecomment-6113213242)
are reviewed as a batch, with identity-only changes, six declared lane-order
changes and one identity-seeded wobble change distinguished. The newly
suppressed launch-campaign label is disclosed, not hidden by corpus edits.
Contributor guards328 pass92.16s; imports, Layout floats and schema gate pass.

Architecture: Core owns dates/critical facts/identity; View owns hierarchy and
lane order/count; Theme declares paint and pitch floor; Layout completes text,
geometry and unpainted ports; Scene projects them. Target fallback belongs to
Draft ingress, not immutable Context. No fake mark, validator waiver, adapter
placement or project-specific condition. Intended output counts and regenerated
public artifacts still require review before release acceptance.
