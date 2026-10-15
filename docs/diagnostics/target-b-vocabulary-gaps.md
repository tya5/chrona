# Target B: the reference elements chrona does not express (#429 row 4)

The `target-b` catalogue preset references the packaged design `src/chrona/resources/designs/target-b/` in place with the shared generic View `presets/bundles/design-default/view.yaml`. This report names every difference between the preset's rendered slide and its generated reference, with the capability each would need. Reference: [halcyon-1-target-design-2026-09-21/board/02-programme-board.png](../research/presentation/halcyon-1-target-design-2026-09-21/board/02-programme-board.png) (1600 x 900 hand-drawn mock; not chrona output). Render: `chrona render --preset target-b examples/halcyon-1/project.yaml --actual examples/halcyon-1/actual.yaml --format png` at `cdf6b4b81`, and `examples/chrona-roadmap/project.yaml` for a second project (status ok). Both images were read directly; measurements are by eye unless a number is cited, and canvas heights are from the PNG header. Row pitch, pixel offsets and colour values are not measured.

Reading rule. The reference is the HALCYON mock (26 work packages in six groups); the draft render is halcyon-1 as the project stands (29 work packages, two `objectType` groups, `point` and `span`). The example slide `21-target-b` reaches more of the reference because its own View names HALCYON's fields, window, periods and annotations. The preset's View is generic by design (#1492) and names no project value, so those rows are bundle-side choices, marked "bundle-side" below; they need no new capability.

| # | Name | Reference shows | Chrona draws | Missing capability | Tracked in |
| --- | --- | --- | --- | --- | --- |
| 1 | `group-names-by-object-type` | six bands named by team, each tinted (`Spacecraft bus` blue, `Imaging payload` green ...) | without Project roles, `point`/`span` fallback; scratch `fieldRoles.responsible: owner` shows six team bands plus `Unassigned` for three ownerless group objects | delivered: semantic responsibility binding; committed Project adoption is reviewer-owned | #1559; #883 |
| 2 | `phase-column-absent` | columns `Work package`, `Phase` (muted), `Δ finish` | generic role-bound `Phase` column; omitted when the role is undeclared, displayed in the scratch role-bound PNG | delivered: `fieldRoles.phase` and `{fieldRole: phase}`; no project field in the generic View | #1559 |
| 3 | `notes-rail-absent` | `NOTES` rail: three boxes (RISK red, NOTE blue) with dotted leaders | no rail; no annotation bindings in the generic View | none: rail is delivered (#1049, #1051, #1064) | bundle-side |
| 4 | `launch-window-absent` | faint blue band Oct to Nov, label `launch window` | no band, no label | none: named periods delivered (#582) | bundle-side |
| 5 | `baseline-ghost-absent` | dashed baseline outline beside the plan bar on the changed rows | no ghost; the legend still lists `baseline`. `baselineMarks: ghost-when-changed` draws nothing without a Snapshot (by design, #1492); no diagnostic | a draft-render way to supply a baseline Snapshot | #1533 |
| 6 | `heading-wording` | `HALCYON-1 · Programme board` with a subtitle line (team, baseline, as-of, calendar) | `HALCYON-1` only | not investigated (Layout heading template; calendar titles are #1026) | not measured |
| 7 | `as-of-chip-wording` | orange chip `as of 20 Aug` | orange chip `as of 20 Aug`; generic View inherits the design's marker wording | reached using existing marker defaults and date presentation | #1563 |
| 8 | `axis-window` | March to November | February to December (automatic) | none: `window.mode: explicit` exists | bundle-side |
| 9 | `plan-bar-colour` | mock blue | pale blue plan bar with a blue outline; the README records palette C as an owner decision | none: deliberate (class c) | none |
| 10 | `decoration-contrast-warning` | weekend stripes and calendar exceptions behind the bands | `W_SCENE_DECORATION_CONTRAST` (27 decorations, lowest 1.08:1 against the floor) | none identified; a reviewer choice | bundle-side |
| 11 | `canvas-height` | 900 px | 868 px (29 rows against 26) | none | not measured |

Reached as drawn: tinted group bands, two-tier axis, weekend stripes and calendar exceptions, plan, actual and in-progress hatch marks, 14 px diamond gates, dependencies with elbows and triangle heads, the legend entries. Typst and TikZ export both succeed (no refusal measured).

Not measured: colour values, pixel positions and the heading wording cause.
