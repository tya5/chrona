<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review: #1958 rows 1 to 4

Observed on `main` at `ef49fe995` (the merge of [PR #1960](https://github.com/tya5/chrona/pull/1960), the single implementation PR). [Issue #1958](https://github.com/tya5/chrona/issues/1958) was re-fetched with `gh issue view 1958 -R tya5/chrona --json body,comments` on 2026-10-25 (1 comment) and counted literally. Rows 1 to 3 are the three bullets under `Acceptance:` of the body; row 4 is the closing sentence "When this lands, update `skills/chrona/references/design-from-a-brief.md` step 9". The one comment (dev B's claim and plan, with the side-effect table) adds no acceptance row; its "CLI flags added: 0 or 1 (`--layout`, only if needed)" is checked under row 2.

What landed: `chrona validate preset.yaml` (kind `presentation-preset`) validates the preset, then each declared member file, the View after the Layout `viewDefaults` merge; `chrona validate view.yaml` takes the defaults from `--layout`, else from the `preset.yaml` beside it that declares it, and prints `"validatedThrough": "preset.yaml"`. Specified in [Spec 56](../../specification/56-schema-authoring-and-diagnostics.md) (section 3.2 paragraph on resource files).

## Method

Private venv `/private/tmp/claude-501/venv1682`, `PYTHONPATH=<worktree>/src:<worktree>:<worktree>/packages/chrona-fonts-noto-cjk/src` (absolute), a fresh worktree of `origin/main` at `ef49fe995`. Every builtin preset (15, from `chrona preset list`) was copied with `chrona preset copy <id> --output all/<id>` and validated unedited through both routes; members were then broken one at a time.

- All 15 builtin presets, both routes: [script](assets-1958/validate-all-builtin-presets.sh.txt), [output](assets-1958/validate-all-builtin-presets-output.txt) (15 of 15: `preset.yaml` is `ok` as `presentation-preset`; `view.yaml` is `ok` with `validatedThrough: preset.yaml`).
- Member-by-member breakage, post-merge View error, missing member, broken catalog, View outside its preset with and without `--layout`: [script](assets-1958/validate-negatives.sh.txt), [output](assets-1958/validate-negatives-output.txt).
- Parity with a render of the same preset (`chrona render ... --preset <copy>/preset.yaml`): [script](assets-1958/render-parity.sh.txt), [output](assets-1958/render-parity-output.txt).
- Tests: [pytest-trial3-gaps-1958.txt](assets-1958/pytest-trial3-gaps-1958.txt) (14 passed in `tests/cli/test_cli_trial3_gaps.py`).

Observations, on a copied `yuya` or `target-b` preset:

| probe | `validate preset.yaml` | `validate view.yaml` |
| --- | --- | --- |
| unedited copy, all 15 builtins | `ok` | `ok`, `validatedThrough: preset.yaml` |
| unknown member added to `view.yaml`, `theme.yaml`, `scheme.yaml`, `layout.yaml`, `detail.yaml` (one at a time) | `E_SCHEMA`, sourceRef `<file>#/`, message `<file>: unexpected property 'bogus'` | n/a |
| View marker `kind: nonsense` (an error after the merge) | `E_SCHEMA` at `view.yaml#/body/markers/0/kind` | `E_SCHEMA` at `/body/markers/0/kind`; a render rejects the same pointer (`E_VIEW_SCHEMA`) |
| `view.yaml` copied alone into another directory | n/a | the 7 missing members are still reported; with `--layout <layout.yaml>`: `ok` |
| `theme.yaml` deleted | `E_INPUT_IO`, status `failed`, absolute path in the message | n/a |
| invalid YAML appended to a declared icon catalog (`yuya`) | `ok` (not read) | n/a |

## Literal issue acceptance

### Issue #1958

- Source: [Issue #1958](https://github.com/tya5/chrona/issues/1958)
- Observed: 2026-10-25

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `chrona validate preset.yaml` validates the whole preset closure: every member file, with the View after its `viewDefaults` merge. Each error names the member file and pointer. | narrowed | Met for the members it reads: `validate_preset_closure` and `preset_members` in [`resource_checks.py`](../../../src/chrona/usecases/resource_checks.py) check the preset, then View, Style, Theme, Color Scheme, Layout, Review Detail and Summary profiles and the compatible Color Schemes, the View with the Layout `viewDefaults` (`defaults if kind == "view"`), wired in [`cli.py`](../../../src/chrona/app/cli.py) (`_validate_preset`). Each finding is `<declared path>: <message>` with sourceRef `<declared path>#<pointer>` ([output](assets-1958/validate-negatives-output.txt): `view.yaml#/body/markers/0/kind`, `theme.yaml#/`). The test [`test_validate_preset_names_the_member_file_and_pointer_of_each_error`](../../../tests/cli/test_cli_trial3_gaps.py) pins the file and pointer. Not met for "every member file": the `resources.iconCatalogs` files a preset declares (5 of the 15 builtins: `technical-print`, `marquee`, `sunday`, `titlecard`, `yuya`) are not opened, so a broken catalog still prints `ok` ([output](assets-1958/validate-negatives-output.txt), last probe); icon-catalog is not a kind `validate` accepts. A member missing on disk is `E_INPUT_IO` with `failed` and an absolute path, not a rejected diagnostic. [Spec 56](../../specification/56-schema-authoring-and-diagnostics.md) lists the members checked and so does not claim catalogs; the skill sentence "every member file" in [design-from-a-brief.md](../../../skills/chrona/references/design-from-a-brief.md) and the guide line in [cli-reference.md](../../guides/cli-reference.md) read wider than the code. The issue's own example (`target-b`, no catalogs) is fully covered. | [#1961](https://github.com/tya5/chrona/issues/1961) |
| 2 | `chrona validate view.yaml` on a View whose omitted members a Layout would supply does not report those members as missing. It either says the View is a split View, validated through its preset, or accepts a `--layout` to merge with. It never reports an error that a render of the same preset would not. | met | The copied View of all 15 builtins validates `ok` and says so: `"validatedThrough": "preset.yaml"` ([output](assets-1958/validate-all-builtin-presets-output.txt)), from `sibling_preset_defaults` ([`resource_checks.py`](../../../src/chrona/usecases/resource_checks.py)) via `_validate_resource` in [`cli.py`](../../../src/chrona/app/cli.py), which also accepts `--layout`, and `--layout` still wins over the sibling. No flag was added (the comment allowed 0 or 1; `--layout` already existed, only its help changed: [cli-reference.md](../../guides/cli-reference.md)). Parity: an error after the merge (`markers/0/kind`) is rejected by `validate view.yaml` and by a render at the same pointer, and the 4 builtin copies rendered (`target-b`, `yuya`, `marquee`, `wallboard-dark`) are accepted by both ([output](assets-1958/render-parity-output.txt)). [`test_validate_view_alone_without_a_preset_still_needs_its_layout`](../../../tests/cli/test_cli_trial3_gaps.py) pins that a View with no `preset.yaml` beside it is still incomplete without `--layout`: a View alone outside its preset is not a rendered preset, so the 7 `missing` errors there are not an error a render of that preset would not report. Boundaries stated, not narrowed, because the text names `chrona validate`: the sibling is found only as `preset.yaml` in the same directory, and the MCP tool `validate_project` (`_validate_project` in `agent_tools.py`) calls `validate_resource_mapping` with no defaults, so a split View there still reports the missing members and a preset is `E_CLOSURE_KIND`; [Spec 56](../../specification/56-schema-authoring-and-diagnostics.md) states the preset check is "CLI only". | — |
| 3 | A synthetic test: a copied builtin preset, unedited, validates clean through both routes. | met | [`test_a_copied_preset_validates_clean_through_preset_yaml_and_its_split_view`](../../../tests/cli/test_cli_trial3_gaps.py) copies `target-b` (the issue's preset) and asserts `preset.yaml` gives exactly `{"status": "ok", "diagnostics": [], "resource": "presentation-preset"}` and `view.yaml` exits 0 with `validatedThrough == "preset.yaml"` (passes, [log](assets-1958/pytest-trial3-gaps-1958.txt)). The test covers one builtin; this review ran all 15 through both routes, all clean ([output](assets-1958/validate-all-builtin-presets-output.txt)). | — |
| 4 | When this lands, update `skills/chrona/references/design-from-a-brief.md` step 9, which currently says to check `view.yaml` by rendering. | met | Step 9 of [design-from-a-brief.md](../../../skills/chrona/references/design-from-a-brief.md) (heading "9. Iterate, then check against the claims") now lists `chrona validate looks/brief-look/view.yaml` and `.../preset.yaml` in its command block, and the sentence "check it by rendering instead" is replaced by the split-View and closure description; no "by rendering" wording remains in the file. The same sentence repeats "every member file", which row 1 narrows (icon catalogs). | — |

Counts: 4 rows, 3 `met`, 1 `narrowed`, 0 `not met`.

## Programme-level criteria (optional)

### Public side effects

This review adds a document and logs and scripts under [assets-1958](assets-1958/validate-all-builtin-presets-output.txt); it changes no behavior, schema, specification, guide, preset, design, example, test or workflow.

| Item | Slides changed | New diagnostics | Schema delta |
| --- | ---: | ---: | --- |
| This review | 0 | 0 | none |
| #1960, as observed here | 0 (no render path changed) | 0 (existing `E_SCHEMA`, `E_CLOSURE_KIND` now also raised per member with the file in the message) | none |
