# Issue #38 reproducibility repair design plan

## Goal

Restore exact, public materialization for every declared example context without weakening immutable content identity checks.

## Design phases

1. Audit current context schemas, materializer closure copying, identity validation, and acceptance tests.
2. Define authoritative identity policy: references carrying `contentIdentity` must match exact source bytes; resource contexts may omit only where v0.6 explicitly permits it, never as a repair for stale fixtures.
3. Define one manifest-driven acceptance path: each `slides[].context` is selected, copied into its immutable snapshot, and materialized by the public CLI.
4. Review v0.5/v0.6 compatibility, migration of ASTER to v0.6 or retained v0.5 identity correctness, and generated evidence ownership.
5. Publish a cross-boundary design review; only then publish implementation plan.

## Constraints

- No hand-maintained generated SVG.
- No legacy Settings/Theme restoration.
- No bypass of content identity verification.
- Full pytest remains delegated; focused tests and static review are added here.