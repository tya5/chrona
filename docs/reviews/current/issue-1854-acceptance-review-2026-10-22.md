<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review: #1854 rows 1 to 5

Observed on `main` at `b91f0f53c` (the derived-sync bot commit after [PR #1896](https://github.com/tya5/chrona/pull/1896)). [Issue #1854](https://github.com/tya5/chrona/issues/1854) has five numbered rows, each with one `Acceptance:` line. The body and comments were re-fetched with `gh issue view 1854 -R tya5/chrona --json body,comments` on 2026-10-22 and counted literally: five rows, no comments, no row added since the first reading. Row 1 landed in [PR #1863](https://github.com/tya5/chrona/pull/1863) (`aa92e2794`), row 2 in [PR #1864](https://github.com/tya5/chrona/pull/1864) (`8c31cd50b`), row 3 in [PR #1859](https://github.com/tya5/chrona/pull/1859) (`9d6e31a90`), row 4 in [PR #1866](https://github.com/tya5/chrona/pull/1866) (`4a981e54e`), row 5 in [PR #1867](https://github.com/tya5/chrona/pull/1867) (`2ab156547`). All five rows are met; the issue touches no reviewer-owned YAML.

## Method

Private venv `/private/tmp/claude-501/venv1682`, `PYTHONPATH=<worktree>/src:<worktree>`, worktree on `origin/main` `b91f0f53c`, no shared install. Every log starts with the command it records. Focused tests: [pytest-1854.txt](assets-1854/pytest-1854.txt) (108 passed; the full suite was not run). The derived-theme file that is only a variant is stored as `.yaml.txt`.

## Literal issue acceptance

### Issue #1854

- Source: [Issue #1854](https://github.com/tya5/chrona/issues/1854)
- Observed: 2026-10-22

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `validate` dispatches on the document's `kind` (Theme, Scheme, Layout Profile, View, Project) and validates against that kind's schema; an unknown kind names the accepted kinds. | met | [Log](assets-1854/row1-validate-by-kind.txt): on the marquee design, `chrona validate theme.yaml`, `scheme.yaml` and `layout.yaml` each print `status ok` with `resource` `theme`, `color-scheme`, `layout-profile` (exit 0); a Project still validates as a Project (`launch.yaml`, `status ok`); a View is checked with the design's `viewDefaults` supplied by `--layout` (without it the View is rejected with `E_SCHEMA` for members the design supplies, with it `status ok`); `kind: widget` is `E_CLOSURE_KIND` at `/kind` with "the accepted kinds are project, theme, color-scheme, layout-profile, view, style, actual-set, summary-profile, review-detail-profile". Tests in [`test_cli_trial3_gaps.py`](../../../tests/cli/test_cli_trial3_gaps.py); text in [`cli-reference.md`](../../guides/cli-reference.md) and [Spec 56](../../specification/56-schema-authoring-and-diagnostics.md). | — |
| 2 | every member a standalone Theme may declare is accepted (or deliberately documented as non-inheritable) in a derived Theme; a synthetic derived Theme with `contrastPolicy` renders with the policy applied. | met | The body members of the standalone v0.15 schema and the derived v0.16 schema are compared in the [log](assets-1854/row2-derived-theme-run.txt): nothing is missing in the derived schema (`contrastPolicy` and `markStack` were the two added; `extends` is the only derived-only member). A derived Theme [declaring `contrastPolicy: {decoration: error}`](assets-1854/row2-derived-theme.yaml.txt) over `target-b` (whose own policy is `decoration: none`) is rejected by `chrona render` with `E_SCENE_DECORATION_CONTRAST` at `/body/contrastPolicy/decoration`, so the derived policy is the one applied; a [variant declaring only `mark: warning`](assets-1854/row2-derived-theme-mark-only.yaml.txt) renders `status ok` because the base's `decoration` class is kept. Tests in [`test_cli_derived_theme_policy.py`](../../../tests/cli/test_cli_derived_theme_policy.py) and [`test_theme_inheritance.py`](../../../tests/unit/chrona/presentation/model/test_theme_inheritance.py); merge rule in [Spec 07](../../specification/07-style-and-theme.md). | — |
| 3 | the error lists the role's supported properties (from the same table the validator uses). | met | [Reproduction](assets-1854/row3-role-property-error.py), [output](assets-1854/row3-role-property-error.txt): `pattern` on the `calendar-closed` role gives `E_THEME_ROLE_PROPERTY_UNSUPPORTED` at `/body/roles/calendar-closed/pattern` with "does not read the property 'pattern'; supported properties: align, backgroundPaintOrder, ... wobbleWavelength". The test compares that list with `theme_role_contract("calendar-closed").properties`, the validator's table: [`test_band_patterns.py`](../../../tests/integration/test_band_patterns.py), [`test_role_admission.py`](../../../tests/unit/chrona/presentation/test_role_admission.py). | — |
| 4 | each of these names the user-visible subject (label text, leader of note N), and the relation-policy info is not emitted when no relation is drawn. | met | Six tests pass ([log](assets-1854/row4-subjects-pytest.txt), [`test_diagnostic_subjects_names.py`](../../../tests/integration/test_diagnostic_subjects_names.py)): `W_LAYOUT_AXIS_LABEL_THINNED` names the dropped text and not `axis-label:N:M`; `W_LAYOUT_ROUTE_FALLBACK` for a note leader reads "leader of note ..." and names the note's target, while a relation route keeps its wording; `I_LAYOUT_RELATION_POLICY_SUPERSEDED` is absent with `mode: none` and still emitted when a relation is drawn (the [notes-and-lanes render](assets-1854/row5-render.txt) draws relations and still carries it). Text in [Spec 39](../../specification/39-axis-and-observation-clarity.md) and [Spec 50](../../specification/50-constraint-driven-gantt-surface-quality.md). | — |
| 5 | the skill (or a guide it links) shows a plan with notes, risks and grouping by a field role; a docs test renders that snippet. | met | [`SKILL.md`](../../../skills/chrona/SKILL.md) links [`notes-risks-and-lanes.md`](../../../skills/chrona/references/notes-risks-and-lanes.md), which shows the plan [`notes-and-lanes/plan.yaml`](../../../skills/chrona/examples/notes-and-lanes/plan.yaml) (annotations of kind `note` and `risk`, `fieldRoles: {responsible: team}`). The test `test_the_skill_links_notes_risks_and_lanes_and_the_page_snippet_renders` in [`test_chrona_skill.py`](../../../tests/unit/chrona/skills/test_chrona_skill.py) checks the page's snippet equals the file, validates and renders it, and asserts the lanes, `NOTE · build`, `RISK · test` and both texts. Run here: [render log](assets-1854/row5-render.txt) (`status ok`, no `W_` warning; both annotation texts found once in the [SVG](assets-1854/notes-and-lanes.svg)). | — |

Counts: 5 rows, 5 `met`, 0 `narrowed`, 0 `not met`.

## Programme-level criteria (optional)

### Public side effects

This review adds a document, logs, one SVG and one script under [assets-1854](assets-1854/pytest-1854.txt); it changes no code, schema, specification, guide, preset or example.

| Item | Slides changed | New diagnostics | Schema delta |
| --- | ---: | ---: | --- |
| This review | 0 | 0 | none |

The public effect of the reviewed PRs is in their own bodies.
