# M26 Operational Review Workflows Design Plan — 2026-09-21

**Status:** C26-D1 complete; normative design is in progress. Implementation is not authorized.
**Owns:** Product reachability for UC-10 (Actual intake/reconciliation), UC-11
(revision-bound CLI/CI automation), and UC-12 (named baseline capture/compare).

## 1. Outcome

An engineering team can import externally observed Actual facts into an explicit
reconciliation queue, capture one immutable baseline, compare named revisions, and run
the same operations from CI without a working-tree default. These operations preserve
the existing Project/Actual/Snapshot authority split and emit machine-readable results.

## 2. Fixed boundaries

| Concern | Owner | Explicit non-owner |
|---|---|---|
| External source bytes and parser | Actual intake adapter | Project scheduler, renderer |
| Observed fact and alignment | immutable Actual-set revision + reconciliation Command | title matching, schedule mutation |
| Baseline identity | immutable Snapshot reference | branch names, generated Scene/SVG |
| Mutation/CAS | Command Engine + Revision Store | CLI flags, CI environment |
| Automation result | versioned JSON result envelope | console prose, renderer state |
| Presentation | existing Render Context/Scene pipeline | intake and baseline selection policy |

No M26 input may silently select a filesystem tip, branch tip, locale-dependent clock,
or renderer fallback. Actual intake never infers Project identity from a title and never
reschedules a Project. Baseline capture records the exact inspected Project revision.

## 3. Design gates

### C26-D1 — Use-case and compatibility closure

- Inventory every existing Actual, Snapshot, Command, CLI, and Revision Store contract.
- Define user-visible success, rejection, idempotency, and retry semantics for UC-10,
  UC-11, and UC-12.
- Decide the replacement/deletion policy for the current loose `propose-set` CLI path.

**Exit:** a source-of-truth matrix and complete input/output examples show no hidden
working-tree or title-matching authority.

**Completed:** 2026-09-21. The compatibility, retry, and replacement decision is
published in `docs/research/operational-workflows/m26-existing-contract-matrix-2026-09-21.md`.

### C26-D2 — Normative resource and command design

- Define a versioned external Actual intake request/report, source provenance, stable
  deduplication key, reconciliation states, and diagnostics.
- Define Snapshot capture result persistence, named baseline comparison input, and
  immutable reference closure.
- Define one revision-bound automation request/result envelope that carries a Command,
  target reference, expected revision/content identity, and declared output artifacts.

**Exit:** owning specification, ADRs, schemas, positive/negative fixtures, canonical
identity rules, and diagnostics agree.

**Completed:** 2026-09-21. Specification `35`, ADR-0024 through ADR-0026, four
versioned schemas, and acceptance/rejection examples establish the single immutable
closure, replay, provenance, and baseline rules.

### C26-D3 — CLI/CI and release design

- Define commands, exit codes, JSON output, output-directory atomicity, and credential
  boundaries for intake, reconciliation, baseline capture/compare, and automation.
- Define deterministic CI examples and acceptance matrix; no command may write a source
  file outside the Revision Store transaction it names.

**Exit:** CLI contract, examples, and acceptance tests are complete; no runtime choice
remains unspecified.

**Completed:** 2026-09-21. The complete CLI, output atomicity, exit-code, credential,
CI containment, and A26 acceptance contract is published in
`docs/planning/active/m26-cli-ci-release-design-2026-09-21.md`.

### C26-D4 — Whole-design review

- Audit Project/Actual/Snapshot/Command/Store/Render Context/CLI boundaries.
- Confirm all UC-10/11/12 behaviors use one Command and immutable-closure path.
- Publish a sliced implementation plan before product code.

**Exit:** design review explicitly authorizes implementation with no unresolved product
decision.

## 4. Non-goals

- GUI editor, automatic entity matching, workflow/ticket synchronization, credentials
  stored in Project files, unbounded connector scripting, or a new scheduler authority.
- PDF/raster output claims, new exporter targets, or extending successor DateTime,
  capacity, or collaboration profiles.

## 5. Stop conditions

Stop before implementation and amend the owning design if an external source cannot
provide a stable identity/provenance record, an operation needs a mutable tip, a retry
could duplicate an observation or baseline, or a CLI result cannot be reproduced from
the declared immutable closure.
