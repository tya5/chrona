# Implementation Plan — Milestone-Only Rows and Fold Policies (#440)

- **K1:** group-header folds packed with `allocate_lanes`, and a test rendering `02` with `group-header` (row 1).
- **K2:** the required fact label for every folded point (row 2), with a corpus test that no folded point lacks a visible name.
- **K3:** `points: key-row` and `keyRow.title`, a key-row Projection and packing, and tests.
- **K4:** `points` as a fallback list, and tests.
- **K5:**
  - the corpus report section and its 25% `--check`;
  - `aster-ssd/overview` moved to `key-row` with `fill` (rows 3 and 5);
  - the other slides over the bound folded, laned, or given a declared reason (row 4).
- **K6:** the literal acceptance review.

K1 to K4 land with the shared next View version, after #467 L3.
