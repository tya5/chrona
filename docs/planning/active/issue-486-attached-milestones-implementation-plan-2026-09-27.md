# Implementation Plan — Attached Milestones (#486)

- **A486-1 (data, now):**
  - `attachesTo` in `project-v0.7` (objects and overrides);
  - post-schedule validation, with the four errors and the warning;
  - tests for each, plus schedule equality with and without attachment.
- **A486-2 (automatic rows, with the next View version):**
  - `rows.points: attached` as the default;
  - the Projection fold, with `predecessor` falling back to inference;
  - the required member label (title · date · delta).
  - Tests: host-row placement, `own-row` restore, the label text, and byte-identity of every committed slide apart from version provenance.
- **A486-3 (lanes, after #467 L3):** pin attached points to their host's lane in the allocator; a lanes test.
- **A486-4 (evidence and acceptance):** two gates attached to HALCYON-1 `campaign`, regenerated evidence with each changed slide reviewed, then the literal acceptance review.
