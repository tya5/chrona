# Issue 806 — inline typed fields acceptance

Candidate, not release acceptance. Product commits: `c276703a5` (shared byte
snapshots), `60c4398a4` (pure syntax), `ccda7bb51` (application/CLI),
`1a02e5837` (guide and SVG/Scene evidence). Ready public base: `137eed375`.
Design and architecture review: [work record](../../planning/active/issue-806-inline-typed-fields-work-record-2026-10-19.md),
published before product code at `4294e23d8`; implementation plan `1c745b453`.
Normative authority: [Spec 65 §12](../../specification/65-terse-plan-syntax.md#12-inline-typed-fields-and-declared-profiles-806).

| Literal owner criterion | Status | Evidence |
| --- | --- | --- |
| A terse plan with `risk=high` on tasks compiles to a Project whose objects carry the field, and renders coloured by risk through the typed-fields guide's encoding. | met locally; release pending | `test_valid_typed_fields_retain_exact_package_bytes`; `test_inline_typed_plan_matches_compile_then_yaml_svg_scene_and_encodes_each_actual_bar`: all three actual SVG planned-mark fills match their Scene risk witnesses, distinct low/medium/high colours, direct terse and compiled YAML SVG/Scene bytes identical. [Actual SVG raster](assets-806/typed-risk.png) inspected: labels and three encoded bars visible, no clipping. |
| An unknown key, a wrong type and an out-of-enum value each fail at compile with the line and column. | met locally; release pending | `test_field_rejections_are_positioned_on_the_complete_assignment` checks all three codes and exact assignment ranges/no partial Project or YAML; CLI enum rejection leaves stdout empty. Explicit fieldless unknown profiles, invalid/ambiguous packages, required fields and authored extension-schema errors also tested. |
| Existing terse plans compile byte-identically. | met locally; release pending | Unchanged golden files, deterministic/hash/locale/mutation-fuzz tests in `tests/unit/chrona/terse`; existing compile and plan-dispatch CLI tests; table-import regressions. No legacy input/golden bytes changed. Official public snapshot still requires CI inspection. |
| The terse guide documents the clause, checked by the docs tests. | met locally; release pending | Updated one-page terse card (120 lines), executable typed-fields guide with declared package, typed terse file, compile and both render paths. Documented-command/plan/card tests and `tools/check_documented_commands.py --check` pass; all seven typed-guide commands executed successfully in the disposable docs workspace. |

Architecture review: pure syntax imports no resource/presentation layers;
shared package resolution retains bytes once; application checks explicit
bindings and stages those exact bytes. Validate/schedule do not reopen source
packages. Temp Project/package filename collisions and cleanup on success and
failure are tested. Profile group syntax retains rollup/parent semantics;
custom Project types remain custom types, without new presentation aliases.
No schema, overlay, dependency, source-map or adapter-placement change.

Latest-ready focused batch: 494 passed in 45.52 s across the terse unit suite,
typed usecase/CLI tests, legacy compile/dispatch, extension/profile checks,
table import, executable docs and import-direction guards. Ledger tests:
3 passed. `git diff --check` and documented-command check pass. No costly full
local pytest run duplicated; CI owns the planned release matrix.

Release gate: pending exact-head PR conformance/pytest shards/newest-Python
materializer evidence, official public-output diff, and the three-OS release
on a main commit containing this review. Keep issue806 open until complete.
