# Issue #371 — Diagnostic Actionability Design Plan

**Status:** Proposed

## Purpose

#370 established a deterministic diagnostic inventory gate.  #371 makes its
human classification truthful and makes selected high-volume ingress failures
actionable, without turning repository-quality tooling into product policy.

## Published facts

- The policy lists every bare ingress code with a generic `reason`, but cannot
  distinguish an adequate identifier from a deliberately deferred improvement.
- `tools/diagnostic_inventory.py` assigns ingress from a fixed module prefix;
  `E_ACTUAL_REQUIRED` is raised in `presentation/model/projection.py` but is
  reachable from the public render use case and currently appears internal.
- `E_CLOSURE_KIND`, `E_STORE_REFERENCE`, and `E_MATERIALIZER_CONTEXT` are
  high-frequency bare diagnostics at locations that already possess relevant
  resource/reference facts.
- The declared-value inventory labels authoring `baseRevision` as
  `product-bookkeeping`, although `chrona workspace revision` produces the
  user's asserted optimistic-concurrency value.
- A first import-graph prototype shows that the legacy 53-code policy is an
  incomplete subset: every bare construction imported by the public CLI is a
  candidate, not only `E_ACTUAL_REQUIRED`.

## Design questions

1. Define a policy vocabulary that separates `sufficient` bare diagnostics
   from an ordered `backlog` without allowing a generic reason to hide work.
2. Derive the full user-facing candidate population from the same static import
   graph as the module-reachability gate, while keeping tool scripts and
   test-only paths out of the public CLI population.
3. Define structured details for the three selected codes at their owning
   boundaries, without moving closure/store/materializer policy into CLI or
   creating code-specific formatting in a renderer.
4. Reclassify `baseRevision` as an immutable assertion and retain its exact
   live producer command.

## Planned design work

### D371-1 — Quality-policy and reachability contract

Publish the policy schema/validation and generated-report design.  Each bare
code receives `disposition: sufficient | backlog`; only `sufficient` requires
a substantive reason explaining why identifier-only output is complete.  The
report must render backlog entries with code, site count, and owner-oriented
next action.  CLI reachability is derived from `chrona.app.cli` and
`chrona.__main__` imports, not directory prefixes; non-CLI reachable modules
remain separately reported rather than silently reclassified.
The policy must classify that full derived population rather than retaining a
legacy 53-code ceiling.

### D371-2 — Owning diagnostic-detail contracts

Specify exact resource/expectation/actual facts for `E_CLOSURE_KIND`,
`E_STORE_REFERENCE`, and `E_MATERIALIZER_CONTEXT`.  The closure owns resource
kind/type facts, storage owns store/reference facts, and materialization owns
manifest/context/reference facts.  Details must remain safe, deterministic,
and structured through existing exception/result boundaries.

### D371-3 — Whole-architecture review

Review the design against Core diagnostics, operational and storage adapters,
use cases, CLI rendering, immutable closure, materializer, tool-only policy,
and the import-direction rule.  Reject runtime reads of quality policy,
presentation-layer diagnostic formatting, broad allowlists, and source-path
prefixes as a substitute for public reachability.

## Implementation-plan requirements

The implementation plan must publish independently reviewable slices for:

1. full-population policy migration, generator/report/backlog validation, and focused negative
   tests;
2. static CLI-reachability classification with a regression proving
   `E_ACTUAL_REQUIRED` is gated or explicitly backlog-dispositioned;
3. closure/store/materializer detail ownership with focused behavior tests and
   generated inventories;
4. `baseRevision` policy correction, full gates, public materializer checks,
   wheel smoke, generated-report review, and three-platform CI.

No compatibility policy format or blanket code exemption may remain after the
accepted migration.

## Acceptance

- Every policy entry has a valid disposition and the generated report presents
  the backlog separately.
- Selected high-volume diagnostics state resource, expectation, and actual
  facts at their owner.
- CLI reachability, not source directory, governs ingress classification; the
  public `E_ACTUAL_REQUIRED` path is accounted for.
- `baseRevision` is `pinned-deliberately` with `chrona workspace revision` as
  producer.
- Focused/full tests, all quality gates, materializer byte checks, wheel smoke,
  generated-report review, and Ubuntu/macOS/Windows CI pass.
