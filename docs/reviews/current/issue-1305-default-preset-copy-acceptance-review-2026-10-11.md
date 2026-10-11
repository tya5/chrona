<!-- chrona:literal-acceptance/v1 -->

# Acceptance review — the bundled default is listed and copyable; copies have no YAML anchors (#1305)

Implementation: [#1361](https://github.com/tya5/chrona/pull/1361) (merge `a407aad6a`), checked against `origin/main` `12f8c6eba`. `chrona-default-draft` is a catalogue entry in `library.yaml` (same member files as `presets/default.yaml`), reported as `"default"` by `preset list`; `preset copy` dumps with a `_PlainDumper` whose `ignore_aliases` is always true, so a repeated mapping is written in full. Plan: [Status comment](https://github.com/tya5/chrona/issues/1305).

## Literal issue acceptance

### Issue #1305

- Source: [Issue #1305](https://github.com/tya5/chrona/issues/1305) (body, assignment and Status comments)
- Observed: 2026-10-11

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A CLI test: `preset list` contains the default id. `preset copy` of it succeeds. Rendering a fixture with the copied `preset.yaml` gives the same SVG bytes as rendering without `--preset`. | met | [`test_preset_copy.py`](../../../tests/cli/test_preset_copy.py): `test_the_bundled_default_is_listed_as_the_default` (`listed["default"] == "chrona-default-draft"` and the id is in `presets`) and `test_the_copied_default_renders_byte_identically_to_a_render_without_a_preset` (copy exit 0; render with `--preset mine/preset.yaml` equals the plain render, bytes). This is a real comparison between two different inputs (the copy and the bundled resources). The fixture is the `chrona init` starter and its Actual Set, not HALCYON-1, so the equality is shown for one small plan. | — |
| 2 | A test over every builtin preset: the copied YAML contains no anchor or alias tokens (checked by parsing events, not by grep), and re-rendering through the copy is byte-identical to rendering by id. | met | `test_every_builtin_copy_is_plain_yaml_and_renders_like_the_id` in the [same file](../../../tests/cli/test_preset_copy.py), parametrized over `list_builtin_presets()` (which now includes the default): every `*.yaml` of the copy is parsed with `yaml.parse` and fails on an `AliasEvent` or an event with an anchor; the copy's render equals the render by id. Same single starter fixture as row 1. | — |
| 3 | Do not edit `examples/**`. | met | [Diff of #1361](https://github.com/tya5/chrona/pull/1361/files): `docs/guides/first-project.md`, `src/`, `tests/`; no `examples/**`, no bot-generated file. | — |

## Programme-level criteria (optional)

The scope rows are also met: `preset list` shows the default marked as default (scope 1), copies are plain YAML with `sort_keys=False` so the key order follows the source (scope 2: "stable" is source order, not sorted), and the default's look is untouched (scope 4; #1302 is separate). The catalogue entry is kept last because probe pointers index entries (a commit message of the PR). CI: [full-matrix run 38098834510](https://github.com/tya5/chrona/actions/runs/38098834510) (workflow_dispatch on `2c96d5445`, a descendant of the merge; macOS, Ubuntu, Windows `success`). All three rows are met, so #1305 can close once this review is on `main` and the three-OS run on the commit that publishes it is cited (AGENTS.md).
