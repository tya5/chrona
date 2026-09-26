# Design Correction — Combined Catalogue Preset Merge (#470)

**Supersedes:** the warning gate and five serial merge units in the [original integration design](issue-470-catalogue-preset-integration-design-2026-09-26.md). **Plan amendment:** [current baseline](../planning/active/issue-470-catalogue-preset-integration-design-plan-amendment-2026-09-26.md). The issue owner clarified the criterion in [#470](https://github.com/tya5/chrona/issues/470); combined [PR #485](https://github.com/tya5/chrona/pull/485) supersedes the five heads.

## Selected behavior and evidence boundary

All five catalogue IDs retain distinct project-generic View, Theme and Layout
members in their own bundle directories. Shared Color Schemes may remain
referenced. `chrona-default-draft` is unchanged. One combined PR is the public
merge unit, with #471–#475 retained as per-preset provenance and image review
records. This resolves the packaged-resource test-list conflict without
discarding any member. The merged library and test list must include the union
of all five; no mechanism, schema or corpus resource is part of #485.

At requested 1600 × 900, the output canvas may grow. The criterion examines
both CLI diagnostics and persisted Scene diagnostics for **layout failures**:
`W_LAYOUT_*OVERFLOW*`, `W_LAYOUT_ROW_DENSITY`, and
`W_SCENE_TEXT_INTERSECTION`. `W_LAYOUT_ACTUAL_INCOMPLETE:tvac` is a truthful
Actual-state fact, and `W_LAYOUT_LABEL_SUPPRESSED` records a declared View
fallback; both are allowed. This distinction is semantic, not a CLI-only
loophole. Neither diagnostic may be hidden or renamed to satisfy the preset
merge. A future unlisted fit, containment or collision failure discovered
during review must be treated as a failure and revisited under its owner.

## Boundaries and migration

Only declarative preset members and their packaging/research evidence change.
View, Theme, Layout, Scene and adapter responsibilities in the original design
are unchanged. The corrected publication topology is one merge of #485 after
current-base review, followed by copied-preset/render acceptance on the actual
merged `main`, CI and a separate acceptance review. The old five-merge plan
is not executed. #476–#483 and #466 own mechanism gaps; their future changes
may prompt separate preset refinements, but do not become hidden #470 fixes.

No living specification or ADR changes: this is issue acceptance and merge
topology, while natural canvas growth and layer ownership are already
normative. The current issue body, rather than the original stricter wording,
is the literal release gate.

**Review:** [whole-architecture correction review](../reviews/current/issue-470-catalogue-preset-integration-correction-architecture-review-2026-09-26.md).
