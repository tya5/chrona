# Issue 145 Network View Envelope Implementation Amendment

## Authority

This amendment applies
`issue-145-network-view-envelope-design-correction-2026-09-22.md` to the
N145-3A plan.  It precedes implementation because the merged View v0.8 schema
does not yet encode its surface-specific authoring contract.

## Added N145-3A work

1. Add View v0.8 discriminator rules which retain required `window` for both
   surfaces, and reject `tableColumns`, `axis`, `markers`, `shading`,
   `timePresentation`, `annotations`, and `annotationPresentation` when
   `surface: dependency-network`.
2. Keep the parsed common `ViewWindow` and existing `ReviewProjection.window`
   unchanged.  Add a structural/network projection test proving that no
   network Layout or Scene adapter reads that envelope or any forbidden
   table/timeline authoring property.
3. Cover accepted network authoring and each rejected property with schema and
   contract tests.  Existing table/timeline fixture bytes are the regression
   baseline.

## Added acceptance

The N145-3A PR may not be accepted until the common projection envelope is
explicitly distinguished from network geometry, all new schema cases pass, and
the focused checks plus full conformance/pytest suite remain green.  N145-3B
continues to require the HALCYON materialization and Scene adapter release
gate; it may begin only after this amendment's N145-3A work is merged.
