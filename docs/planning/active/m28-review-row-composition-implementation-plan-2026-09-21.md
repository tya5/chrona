# M28 Review Row Composition Implementation Plan — 2026-09-21

**Status:** Authorized by the M28 design reviews.

| Slice | Scope | Completion evidence |
|---|---|---|
| I28-R1 | View v0.2 and Render Context v0.6 schema/closure recognition; migrate shipped automatic Views/Contexts | schema and closure tests; existing examples render identically |
| I28-R2 | `ReviewItemProjection` / `ReviewRowProjection`; automatic-row construction and table-subject normalization | projection unit tests proving one row can contain several source-agnostic items |
| I28-R3 | Explicit rows, member subtracks, row-height measurement, source/projection identity, table/Scene integration | owner-labelled row with serial tasks plus milestone; bounds/provenance/diagnostic tests |
| I28-R4 | Snapshot-ref closure, independent snapshot schedule, Primary/Snapshot/Actual Review Item resolution | mixed-revision immutable closure fixture; Project-ID and missing-source diagnostics |
| I28-R5 | Public CLI/materializer/conformance acceptance, generated examples, final review and issue disposition | full regression, conformance, materializer reproduction |

Each slice begins from the published Specification 38 and v0.6 closure contract. If an
implementation requires a new source kind, renderer coordinate, theme fallback, or
implicit resource resolution, it stops and returns to design. Publication to `main` is
serial after every slice; GitHub writes use the GitHub integration only.

M28 deliberately implements row composition before an Actual overlay/progress
indicator. Those later policies consume generic Review Items and shared-row subtracks;
they do not add an Actual-only path.
