# Issue 1756 — customisation acceptance

All five literal rows are met; issue1756 is closed. Exact review-containing
main `1abfa2fef03ae407e3691068454ff61df98e0605` passed
[release39352901914](https://github.com/tya5/chrona/actions/runs/39352901914):
three-OS full pytest/conformance/wheel, MCP floor and newest-Python reproduction.
A implemented rows1–2 (`eca1ac1bf`); B implemented rows3–5 (PR1765/1762).
[Published design/architecture/plan](https://github.com/tya5/chrona/issues/1756#issuecomment-6256669837);
normative Specs28/60 and pre-code exact-coverage correction `b9c9e0b41`.

| # | Literal acceptance criterion | Status and direct evidence |
| ---: | --- | --- |
| 1 | An encoding whose realized slot colours are indistinct from each other, or from another legend key's colour, gets a warning naming both, using Spec 60's existing distinctness measure. Show it on a synthetic case. | Met. `test_legend_colour_warning_render.py` joins each warning subject to actual Scene/SVG swatches; Layout tests cover declared vision simulations and exact existing-domain coverage. [View/semantic example](assets-1756/view-encoding-semantic.png): Team a `#269D78` vs On track `#269D79`, CIEDE2000 0.291. [Distinct Style meanings on one scale/value](assets-1756/same-scale-same-value-style.png) also warn; sharing a scale/value does not hide a distinct key. |
| 2 | Find whether this is intended; make both modes consistent or state the rule, and add a synthetic test. | Met. Spec28 states the ordinary Theme-gate point is outside View `target: planned`; forecast points are eligible; omitting the optional Theme gate role gives both the planned fallback. `test_gate_encoding_modes.py` checks real SVG and serialized Scene without a project exception. |
| 3 | The guide shows the colour-by-field recipe working on at least two bundled presets, plus title and subtitle customisation, checked by the docs tests. | Met. `docs/guides/typed-fields.md` and `test_typed_fields_colour_recipe_works_on_executive_light_and_target_b` prove both presets' three colours, legend values, custom title and subtitle, after the original no-series-scale refusal. B independently ran the guide commands and inspected [executive-light](assets-1756/recipe-executive-light.png) and [target-b](assets-1756/recipe-target-b.png); A verified both images and tests. The shared clean-wheel run now passes on all three OS. |
| 4 | The message names the role and what to declare, or the preset declares the role (reviewer YAML). | Met. `test_deadline_mark.py::test_a_subtitle_without_a_theme_subtitle_role_names_the_role_and_what_to_declare` proves `E_THEME_ROLE_REQUIRED` names subtitle, typography and `roles.subtitle`, without `bindingType=NoneType`; the guide shows the derived Theme. No preset edit was needed. |
| 5 | The error says that a parent path is not permitted and names the allowed form; the guide states it. | Met. `test_schema_diagnostics.py::test_an_extension_path_with_a_parent_directory_says_so_and_names_the_allowed_form` proves the parent-directory refusal and permitted `folder/file.yaml`; the guide gives `extensions/typed-team.yaml`. |

Architecture: Presentation supplies explicit scale/domain identities and resolved
collision facts. Layout alone checks final visible legend ink with the existing
CIEDE2000/vision measure and deduplicates only the exact covered domain pair.
No ID parsing, second resolver, threshold change or Scene/adapter policy.

Verification: 184 focused owner/integration tests; shared1754/1756/416 batch532
passed. PR1786 CI39344125617 passed; official artifact12229874166 has50SVG and
50Scene byte-identical, with only intended coverage/inventory report changes.
B's row3–5 review and pictures are consolidated here rather than maintained as
a second contradictory acceptance table; source history remains in Git.

Earlier release39342287509 failed wheel documentation because the guide and
Skill copied into the same destination. PR1788 retained the non-overwrite and
checker contracts, gave the guide distinct `looks/typed-*` paths, and added a
discovered-command regression (red before, green after). Fresh wheel
`ff38c18a54eb618239d86e0f8fa29ebbc42af256f6ab356001afc43587d3f36a`
passed the actual empty-workspace `tools/wheel_doc_check.py`. Corrected release
39352901914 above passes every required gate; no generated output was authored.
