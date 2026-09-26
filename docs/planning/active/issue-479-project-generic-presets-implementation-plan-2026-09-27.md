# Implementation Plan — Project-Generic Presets (#479)

- **I479-1 (View version after #467):**
  - group order `{by: earliestPlannedStart}`;
  - the lone-missing-header rule;
  - `domain: firstAppearance` with Theme `palette`;
  - `labels.placement: both` with its validator.
  - Tests for each, plus a byte check that existing slides stay unchanged apart from version provenance.
- **I479-2 (preset package):** optional `detailProfile` and `visualProfile.preferred`, CLI precedence, and tests.
- **I479-3 (catalogue):** migrate the five presets; HALCYON and starter render tests; a no-HALCYON-value scan.
- **I479-4:** acceptance review.
