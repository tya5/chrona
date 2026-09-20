# I1 CLI Entry Remediation Review

**Conclusion:** Accepted. CLI read and render modes now expose the authority boundary
defined by the published remediation design.

## Evidence

- `validate`, `schedule`, and `render` accept either one raw Draft Project path or the
  complete `--snapshot-reference` / `--snapshot-root` / `--store-identity` tuple.
- Snapshot errors remain stable store diagnostics and never fall back to the raw path.
- `render --presentation-settings` reaches the common v0.2 Scene serializer; omission
  remains the explicit `E_PRESENTATION_LEGACY_ADAPTER` path.
- The legacy adapter uses a separate 24-pixel label gutter, a non-overlapping title,
  and muted ten-pixel tick labels.
- The regenerated controller-x SVG is exact golden-file evidence and reflects the
  Project-order scheduler result.
- Every CLI subcommand has a user-facing help description.

The focused CLI/render suite passes 13 tests. Full inherited tests and conformance are
required before publication.
