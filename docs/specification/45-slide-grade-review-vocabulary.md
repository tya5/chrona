# 45. Slide-grade review vocabulary

## Ownership

The View selects vocabulary and comparison composition; Theme supplies semantic roles and internal geometry; Layout allocates named source slots and internal required extents; Scene derives primitives. Project remains schedule/fact data only. Render Context closure and M28 ReviewRow remain unchanged.

## Overlay tracks

A ReviewRow item declares `track: stacked | shared` (default `stacked`). Members on a shared track use one row-center geometry and deterministic z-order `snapshot < planned < actual`. Snapshot, primary, and actual remain separate ReviewItems and source metadata; overlay changes neither selection nor Actual semantics. The Theme supplies `snapshot`, `planned`, and `actual` roles and opacity/pattern where required.

## Group headers

Consecutive rows with the same non-empty View group form a SceneGroup. Theme metric `timeline.groupHeader.blockSize` reserves an internal header band; Scene emits group-header text spanning table and timeline and indents member table labels. Absence of a group or a zero/omitted header metric preserves the no-header composition. Group headers are derived from View grouping, never persisted in Project.

## Calendar axis and as-of marker

View axis policy chooses one or two semantic levels from existing interval algorithms: year/quarter band and short month/week labels. For the current axis contract, the View selects a finite form and may select an independent name table; Layout formats and measures the completed label as specified by [Axis Name Tables](63-axis-name-tables.md). Scene projects that text without locale formatting. The Actual set's declared observation cutoff, when present, renders an `as-of` line and label; absent cutoff produces no inferred marker. Calendar closures derive from the Project calendar and use Theme `calendar-closed.fill`; they never change schedule dates.

## Legend and mark labels

Detail Profile admits ordered legend entries. Scene emits a role-derived swatch plus label for each entry, retaining source metadata. View `visibility.labels` controls optional mark/member title labels; explicit-row labels from specification 44 are its base behavior, and the same control applies to automatic rows.

## Callout rail

Specification 44 callout rail is the sole object-callout mechanism. #45 adds no alternate annotation resource.

## Failures

Missing required Theme role/metric, missing required slot extent, or unsupported target capability is diagnostic before renderer serialization. Optional vocabulary is omitted only when its View visibility/slot priority permits it. No legacy Settings or deleted Theme contract is restored.
