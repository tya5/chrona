# Design Correction — Progressive Tutorial Source Boundaries (#378 I378-3)

## Decision

The onboarding guide remains one ordered learning path, but not one universal
Project-file workflow. Stages for fixed spans, gates, dependencies/lag,
calendars, constraints/deadlines, hierarchy/rollup, and Actuals/progress use
small independent Draft fixtures and `chrona render`. Each fixture is a
complete valid Project (plus Actual Set and progress-selecting View only when
introduced), so readers may
copy or edit that stage alone. A structural test requires each stage's own
declared concept and verifies that all listed commands render. A deliberate
edit/re-render proof demonstrates that source changes affect output.

The seventh Draft stage needs that minimal View because an Actual Set owns
the observation while View owns its visible progress facet and fill. The
packaged default View does not select either. The stage-7 View declares
`comparison.actual: required`, the `progress` facet, and
`progressFill.source: actual`; it is not hidden data in Project or Actual.

Scenario learning uses Project `scenarios` **and** a View selecting the
scenario; adding an unselected scenario to a Project and rendering a default
View is not evidence. The guide may invoke the existing HALCYON scenario
corpus materializer as the executable illustration, linking the Project and
View source locations and the corresponding Scene/evidence. It does not copy
the large corpus into a new tutorial fixture.

Snapshot learning uses `snapshot-ref/v0.2` from immutable Render Context
`inputs.snapshot`, a pinned baseline Project revision, and a View whose
comparison baseline is `snapshot`. Extension learning uses Project
`extensions` with a pinned profile package in the immutable closure. These
stages use their existing small declared corpus manifests and the public
`chrona materialize` command, not a purported Draft-only Project snippet.

The guide distinguishes an author-edited Draft artifact from byte-reproduced
immutable evidence. It does not teach a Context reference as editable YAML
or suggest that a gallery page supplies render inputs. The corpus is cited,
not repackaged, for the advanced stages.

## Acceptance and failure behavior

The documentation gate executes every non-skipped guide command in a
disposable workspace. A separate tutorial test checks the seven compact
Project/Actual/View fixtures, the introduced concepts, the edit/re-render change,
the selected-scenario Project/View pair, and the named snapshot/extension
closure edges. Public materializer byte reproduction remains the final check
for those advanced examples. The #378 acceptance review maps every literal
rung to an executable command and observed artifact.

No new Project, View, Context, snapshot, or extension syntax is introduced.
