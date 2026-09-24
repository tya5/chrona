# Issue #357 — YAML Loading Performance Implementation Plan

## I357-1 — Codec and packaged-schema boundary

Add `chrona.yaml_codec.safe_load` with C-loader fallback.  Add a single cached
packaged-schema accessor and migrate the Presentation contract registry and
per-schema validation path.

**Acceptance:** safe fallback and decoded-value equivalence tests pass; repeated
contract validation does not re-decode package schemas.

## I357-2 — Runtime ingress migration

Migrate every production `yaml.safe_load` / direct safe loader use in Core,
Storage, Presentation, Operational, Extensions, Commands, and Usecases to the
codec.  Cache only package-schema consumers that own immutable resources.

**Acceptance:** repository check proves production YAML ingress uses the codec;
external snapshot and file reads remain per-read.

## I357-3 — Regression and performance evidence

Add timing-free call-count/cache tests, run focused and full tests, reproduce
all public materializers byte-for-byte, run conformance and isolated-wheel
smoke, then record local timing samples and GitHub CI in a release review.

**Acceptance:** D357-1 through D357-5 all pass.

## I357-4 — Catalog-neutral selected-entry closure (design correction)

Replace the superseded package projection with generic envelope closure,
selected-entry validation/expansion, and deterministic JSON catalog ingress.
Move the shared codec to Resources so the import graph remains inward.

**Acceptance:** bundled and user-imported catalogs follow one path; no
provider-dependent reader exists; the Material path satisfies the recorded
performance target.

## I357-5 — Post-hoc codec and selection invariants

Make the JSON prefix fast path fall back to safe YAML on JSON decoding failure.
Validate alias targets during envelope closure. Add selected/unselected
malformed-entry characterization tests and document canonical JSON catalog
output.

**Acceptance:** all invariants in
`issue-357-posthoc-closure-correction-2026-09-24.md` pass without a
package-specific path or timing-sensitive assertion.

## Publication sequence

1. Publish this design and architecture review.
2. Publish I357-1 and I357-2 with focused tests.
3. Publish acceptance/release review only after complete verification.
