<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review: #1958 rows 1 to 4

Observed on `main` at `536288873` (the merges of [PR #1960](https://github.com/tya5/chrona/pull/1960), `ef49fe995`, and of [PR #1963](https://github.com/tya5/chrona/pull/1963), the residual fix found by the first pass of this review). [Issue #1958](https://github.com/tya5/chrona/issues/1958) was re-fetched with `gh issue view 1958 -R tya5/chrona --json body,comments` on 2026-10-25 (1 comment) and counted literally. Rows 1 to 3 are the three bullets under `Acceptance:` of the body; row 4 is the closing sentence "When this lands, update `skills/chrona/references/design-from-a-brief.md` step 9". The one comment (dev B's claim and plan, with the side-effect table) adds no acceptance row; its "CLI flags added: 0 or 1 (`--layout`, only if needed)" is checked under row 2.

What landed: `chrona validate preset.yaml` (kind `presentation-preset`) validates the preset, then each declared member file, the View after the Layout `viewDefaults` merge; `chrona validate view.yaml` takes the defaults from `--layout`, else from the `preset.yaml` beside it that declares it, and prints `"validatedThrough": "preset.yaml"`. Specified in [Spec 56](../../specification/56-schema-authoring-and-diagnostics.md) (section 3.2 paragraph on resource files).

## Method

Private venv `/private/tmp/claude-501/venv1682`, `PYTHONPATH=<worktree>/src:<worktree>:<worktree>/packages/chrona-fonts-noto-cjk/src` (absolute), a worktree of `origin/main` at `536288873`. Every builtin preset (15, from `chrona preset list`) was copied with `chrona preset copy <id> --output all/<id>` and validated unedited through both routes; members were then broken one at a time.

- All 15 builtin presets, both routes: [script](assets-1958/validate-all-builtin-presets.sh.txt), [output](assets-1958/validate-all-builtin-presets-output.txt) (15 of 15: `preset.yaml` is `ok` as `presentation-preset`; `view.yaml` is `ok` with `validatedThrough: preset.yaml`).
- Member-by-member breakage, post-merge View error, missing member, broken catalog, View outside its preset with and without `--layout`: [script](assets-1958/validate-negatives.sh.txt), [output](assets-1958/validate-negatives-output.txt).
- Parity with a render of the same preset (`chrona render ... --preset <copy>/preset.yaml`): [script](assets-1958/render-parity.sh.txt), [output](assets-1958/render-parity-output.txt).
- Tests: [pytest-trial3-gaps-1958.txt](assets-1958/pytest-trial3-gaps-1958.txt) (17 passed in `tests/cli/test_cli_trial3_gaps.py`, 14 from #1960 and 3 from #1963).

Observations, on a copied `yuya` or `target-b` preset:

| probe | `validate preset.yaml` | `validate view.yaml` |
| --- | --- | --- |
| unedited copy, all 15 builtins | `ok` | `ok`, `validatedThrough: preset.yaml` |
| unknown member added to `view.yaml`, `theme.yaml`, `scheme.yaml`, `layout.yaml`, `detail.yaml` (one at a time) | `E_SCHEMA`, sourceRef `<file>#/`, message `<file>: unexpected property 'bogus'` | n/a |
| View marker `kind: nonsense` (an error after the merge) | `E_SCHEMA` at `view.yaml#/body/markers/0/kind` | `E_SCHEMA` at `/body/markers/0/kind`; a render rejects the same pointer (`E_VIEW_SCHEMA`) |
| `view.yaml` copied alone into another directory | n/a | the 7 missing members are still reported; with `--layout <layout.yaml>`: `ok` |
| `theme.yaml` deleted | rejected `E_SCHEMA`, sourceRef `theme.yaml#/`, message `theme.yaml: the member file declared by the preset does not exist` | n/a |
| invalid YAML appended to a declared icon catalog (`yuya`) | rejected `E_SCHEMA`, sourceRef `catalogs/chrona-target-parts-v2026-10-09.yaml#/`, message prefixed with that file | n/a |

## Literal issue acceptance

### Issue #1958

- Source: [Issue #1958](https://github.com/tya5/chrona/issues/1958)
- Observed: 2026-10-25

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `chrona validate preset.yaml` validates the whole preset closure: every member file, with the View after its `viewDefaults` merge. Each error names the member file and pointer. | met | `validate_preset_closure` and `preset_members` in [`resource_checks.py`](../../../src/chrona/usecases/resource_checks.py) check the preset, then View, Style, Theme, Color Scheme, Layout, Review Detail and Summary profiles, the compatible Color Schemes and, since #1963, each `resources.iconCatalogs` file, the View with the Layout `viewDefaults` (`defaults if kind == "view"`), wired in [`cli.py`](../../../src/chrona/app/cli.py) (`_validate_preset`). Each finding is `<declared path>: <message>` with sourceRef `<declared path>#<pointer>` ([output](assets-1958/validate-negatives-output.txt): `view.yaml#/body/markers/0/kind`, `theme.yaml#/`, `catalogs/chrona-target-parts-v2026-10-09.yaml#/`). A declared member missing on disk or unreadable is a rejected `E_SCHEMA` at `<declared path>#/`, with no absolute path. Tests in [`test_cli_trial3_gaps.py`](../../../tests/cli/test_cli_trial3_gaps.py): [`test_validate_preset_names_the_member_file_and_pointer_of_each_error`](../../../tests/cli/test_cli_trial3_gaps.py) (#1960), [`test_validate_preset_rejects_an_invalid_icon_catalog_with_its_file_and_pointer`](../../../tests/cli/test_cli_trial3_gaps.py) and [`test_validate_preset_rejects_a_missing_member_naming_the_declared_path`](../../../tests/cli/test_cli_trial3_gaps.py) (#1963); [Spec 56](../../specification/56-schema-authoring-and-diagnostics.md) lists the members including the icon catalogs, and the guide line in [cli-reference.md](../../guides/cli-reference.md) ("all its member files") is now accurate. At `ef49fe995` this row was `narrowed` (catalogs not opened, raw `E_INPUT_IO`); #1963 fixed both, and the follow-up issue #1961 was closed as not planned. | — |
| 2 | `chrona validate view.yaml` on a View whose omitted members a Layout would supply does not report those members as missing. It either says the View is a split View, validated through its preset, or accepts a `--layout` to merge with. It never reports an error that a render of the same preset would not. | met | The copied View of all 15 builtins validates `ok` and says so: `"validatedThrough": "preset.yaml"` ([output](assets-1958/validate-all-builtin-presets-output.txt)), from `sibling_preset_defaults` ([`resource_checks.py`](../../../src/chrona/usecases/resource_checks.py)) via `_validate_resource` in [`cli.py`](../../../src/chrona/app/cli.py), which also accepts `--layout`, and `--layout` still wins over the sibling. No flag was added (the comment allowed 0 or 1; `--layout` already existed, only its help changed: [cli-reference.md](../../guides/cli-reference.md)). Parity: an error after the merge (`markers/0/kind`) is rejected by `validate view.yaml` and by a render at the same pointer, and the 4 builtin copies rendered (`target-b`, `yuya`, `marquee`, `wallboard-dark`) are accepted by both ([output](assets-1958/render-parity-output.txt)). [`test_validate_view_alone_without_a_preset_still_needs_its_layout`](../../../tests/cli/test_cli_trial3_gaps.py) pins that a View with no `preset.yaml` beside it is still incomplete without `--layout`: a View alone outside its preset is not a rendered preset, so the 7 `missing` errors there are not an error a render of that preset would not report. Boundaries stated, not narrowed, because the text names `chrona validate`: the sibling is found only as `preset.yaml` in the same directory, and the MCP tool `validate_project` (`_validate_project` in `agent_tools.py`) calls `validate_resource_mapping` with no defaults, so a split View there still reports the missing members and a preset is `E_CLOSURE_KIND`; [Spec 56](../../specification/56-schema-authoring-and-diagnostics.md) states the preset check is "CLI only". | — |
| 3 | A synthetic test: a copied builtin preset, unedited, validates clean through both routes. | met | [`test_a_copied_preset_validates_clean_through_preset_yaml_and_its_split_view`](../../../tests/cli/test_cli_trial3_gaps.py) copies `target-b` (the issue's preset) and asserts `preset.yaml` gives exactly `{"status": "ok", "diagnostics": [], "resource": "presentation-preset"}` and `view.yaml` exits 0 with `validatedThrough == "preset.yaml"` (passes, [log](assets-1958/pytest-trial3-gaps-1958.txt)). The test covers one builtin; this review ran all 15 through both routes, all clean ([output](assets-1958/validate-all-builtin-presets-output.txt)). | — |
| 4 | When this lands, update `skills/chrona/references/design-from-a-brief.md` step 9, which currently says to check `view.yaml` by rendering. | met | Step 9 of [design-from-a-brief.md](../../../skills/chrona/references/design-from-a-brief.md) (heading "9. Iterate, then check against the claims") now lists `chrona validate looks/brief-look/view.yaml` and `.../preset.yaml` in its command block, and the sentence "check it by rendering instead" is replaced by the split-View and closure description; no "by rendering" wording remains in the file. | — |

Counts: 4 rows, 4 `met`, 0 `narrowed`, 0 `not met`.

## Programme-level criteria (optional)

### Public side effects

This review adds a document and logs and scripts under [assets-1958](assets-1958/validate-all-builtin-presets-output.txt); it changes no behavior, schema, specification, guide, preset, design, example, test or workflow.

| Item | Slides changed | New diagnostics | Schema delta |
| --- | ---: | ---: | --- |
| This review | 0 | 0 | none |
| #1960 and #1963, as observed here | 0 (no render path changed) | 0 (existing `E_SCHEMA`, `E_CLOSURE_KIND` now also raised per member, icon catalogs and missing members included, with the file in the message) | none |
