<!-- chrona:literal-acceptance/v1 -->

# Issue 806 — inline typed fields acceptance

Implementation: PR1771. Design and work record:
[archived work record](../planning/issue-806-inline-typed-fields-work-record-2026-10-19.md).
Normative authority: [Spec 65 §12](../../specification/65-terse-plan-syntax.md#12-inline-typed-fields-and-declared-profiles-806).
The reviewer closed #806 in
[comment 6268760253](https://github.com/tya5/chrona/issues/806#issuecomment-6268760253).

| Literal owner criterion | Status | Evidence |
| --- | --- | --- |
| A terse plan with `risk=high` on tasks compiles to a Project whose objects carry the field, and renders coloured by risk through the typed-fields guide's encoding. | met | `test_valid_typed_fields_retain_exact_package_bytes`; `test_inline_typed_plan_matches_compile_then_yaml_svg_scene_and_encodes_each_actual_bar`: all three actual SVG planned-mark fills match their Scene risk witnesses, with distinct low/medium/high colours; direct terse and compile-then-YAML SVG/Scene bytes match. [Inspected SVG raster](assets-806/typed-risk.png) shows labels and encoded bars without clipping. |
| An unknown key, a wrong type and an out-of-enum value each fail at compile with the line and column. | met | `test_field_rejections_are_positioned_on_the_complete_assignment` checks all three codes and exact assignment ranges/no partial Project or YAML; CLI enum rejection leaves stdout empty. Fieldless unknown profiles, invalid/ambiguous packages, required fields and authored extension-schema errors are also tested. |
| Existing terse plans compile byte-identically. | met | Existing golden bytes remain unchanged; deterministic/hash/locale/mutation-fuzz tests, compile and plan-dispatch CLI tests, and table-import regressions pass. |
| The terse guide documents the clause, checked by the docs tests. | met | The one-page card and executable typed-fields guide document the clause and render paths. Documented-command/plan/card tests pass; all seven guide commands executed in the disposable docs workspace. |

Latest-ready focused batch: 494 passed across terse, typed application/CLI,
extension/profile, table import, executable docs and import-direction tests.
The official public snapshot and actual raster were inspected. The review-
containing main `9dca9c55a8df0d1e44149a0543fe892366d39930` passed exact
[release39256723703](https://github.com/tya5/chrona/actions/runs/39256723703):
Ubuntu, Windows and macOS full matrix; conformance; wheel/smoke; MCP floor;
and newest-Python public reproduction. The reviewer closed the issue after
this release passed.
