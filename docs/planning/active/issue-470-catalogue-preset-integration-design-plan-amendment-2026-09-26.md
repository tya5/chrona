# Design Plan Amendment — Combined Preset PR and Layout-Failure Gate (#470)

**Predecessor:** [original design plan](issue-470-catalogue-preset-integration-design-plan-2026-09-26.md). **Trigger:** #470 owner clarification and combined [PR #485](https://github.com/tya5/chrona/pull/485) on 2026-09-26, following the [current-base validation](../../reviews/current/issue-470-current-base-pr-validation-2026-09-26.md).

## Published change to the baseline

The issue now explicitly defines row 2 as **no layout failure**, in CLI output
or Scene diagnostics. Layout failure means `W_LAYOUT_*OVERFLOW*`,
`W_LAYOUT_ROW_DENSITY` or `W_SCENE_TEXT_INTERSECTION`. The TVAC incomplete-Actual
fact and declared `W_LAYOUT_LABEL_SUPPRESSED` do not fail this gate. Requested
1600 × 900 may grow naturally. #485 combines the five tuning branches, resolves
their shared packaged-resource test conflict and supersedes #471–#475. This
replaces the original strict all-warning and serial-five-merge assumptions;
earlier documents remain historical, not current instructions.

## Literal current acceptance criteria

1. Each of the five presets has its own members and a merged tuning PR with
   before/after images on HALCYON-1 and the `chrona init` starter.
2. Every preset renders HALCYON-1 with a requested 1600 × 900 viewport, and the
   canvas may grow, without any **layout failure**, whether printed by the CLI
   or stored in the Scene's `diagnostics`. A layout failure is any
   `W_LAYOUT_*OVERFLOW*`, `W_LAYOUT_ROW_DENSITY` or
   `W_SCENE_TEXT_INTERSECTION`. Data-state facts such as
   `W_LAYOUT_ACTUAL_INCOMPLETE:tvac` and declared suppression
   (`W_LAYOUT_LABEL_SUPPRESSED`) are not layout failures and may remain.
3. Every mechanism gap found is either filed as its own issue or attached to
   an existing one.

## Design decisions to complete before merge

Confirm #485's combined provenance and exact changed-file scope, the complete
union of packaged resources, preservation of each preset's distinct View,
Theme and Layout, and unchanged bare default. Recheck its current-main
mergeability, full CI and copied-preset renders after the #477 material push.
Review images as a batch and verify the gap map. Publish a design correction,
whole-architecture review and implementation-plan amendment before merging.
Do not erase the existing Scene diagnostics or reinterpret an overflow as data
state merely to pass the gate.

The five PR READMEs currently say "no warnings" without qualifying CLI versus
Scene; the combined PR body is precise. The final published research record
must use the corrected layout-failure wording or explicitly state that it
means CLI output only. This is documentation honesty, not a rendering blocker.
