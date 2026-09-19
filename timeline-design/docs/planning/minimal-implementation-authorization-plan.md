# Minimal Implementation Authorization Plan

**Status:** Authorized design plan
**Authority:** Current specifications `02`–`17`; the final design-readiness review
authorizes this plan but does not replace any owning specification.

## 1. Purpose and boundary

This plan authorizes implementation of one bounded, end-to-end Chrona slice. It does
not authorize semantic redesign: an ambiguity discovered during implementation must be
recorded as a diagnostic review or ADR and resolved by its owning specification before
code relies on a new interpretation.

## 2. Supported initial profile

- Stable Core v0.1 Date-only temporal and endpoint-bound acyclic scheduling profile.
- Revision Store evaluation through immutable snapshots, beginning with the local
  transactional adapter; Git and content-addressed adapters implement the same contract.
- Canonical YAML/JSON input, schema + semantic validation, deterministic scheduling,
  a Render Context closure, and deterministic SVG output.
- Federation is read-only: resolve a parent-pinned export reference; it never grants
  parent mutation authority over a child Project.

## 3. Ordered implementation slices

| Slice | Deliverable | Acceptance evidence |
|---|---|---|
| 0 | Standard `implementation-delivery` resolved-manifest validation, typed-field Command, and self-hosted roadmap fixture | profile and roadmap fixture validate/schedule deterministically; workflow state cannot affect schedule or Actual; evidence references are immutable and kind/content checked |
| I | **Complete:** Revision Store adapter interface and immutable local snapshot reader, including package-reference resolution | same Project/package resource reference resolves identically twice; Draft access is rejected for reproducible evaluation |
| II | **Complete:** Core loader/validator/scheduler integrated through that reader | pinned Project/package bytes validate and schedule deterministically through the snapshot loader; Draft access has no filesystem fallback |
| IIIa | **Complete:** Render Context root closure resolver and evaluation manifest | project/View/Style/Theme/Scene Profile kind, ID, content, and mixed-revision mismatches reject before rendering; ordered closure is explicit |
| IIIb | **Complete:** Presentation recursive closure edges and cycle diagnostics | declared profile-package edges resolve in deterministic order; path escape rejects before read. The bounded initial profile graph has no recursive edge, so a cycle is structurally unrepresentable and remains rejected by absence of an edge syntax. |
| IV | **Complete:** Command execution through compare-and-set Store write | stale base revision and partial batch fail atomically; accepted command returns a new snapshot |
| V | **Complete:** Deterministic SVG adapter from Scene output | target-capability and accessibility acceptance fixtures pass; SVG never becomes canonical data |
| VI | **Complete:** Read-only Federation resolver | trust, pin, repin, unavailable export, and namespace diagnostics pass; child mutation remains impossible |

Slice 0 may be implemented only after the profile design prerequisites in
`implementation-delivery-profile-plan.md` are complete. Each remaining slice may be
implemented only after the preceding slice's acceptance evidence
passes. Each completed slice is one reviewed commit and is immediately published before
the next begins.

## 4. Explicitly deferred

DateTime/DST scheduling, non-linear scale, GUI/tldraw adapter, CLI/AI adapter,
PPTX/canvas export, collaboration, resource leveling, cost/timesheet/ticket features,
hosted synchronization, universal merge, and arbitrary extension code are not part of
this authorization.

## 5. Completion rule

The minimal implementation is complete only when slices 0 and I–VI have their stated
acceptance evidence, the full conformance runner and pytest suite pass, and a separate
implementation-readiness review confirms that no adapter has become a semantic source
of truth.
