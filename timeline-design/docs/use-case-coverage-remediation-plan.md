# Use Case Coverage Remediation Plan

**Status:** Draft  
**Depends on:** [14 Use Case Catalog](14-use-case-catalog.md)  
**Purpose:** Turn identified use-case gaps into owned design work before implementation.

## 1. Triage rule

A gap is a **design gap** when the owning specification cannot state deterministic
inputs, outcomes, diagnostics, and authority boundaries. It is an **implementation
gap** when those are specified but no adapter, runner, or UI realizes them yet.

## 2. Remediation order

| Priority | Use case | Classification | Required action | Owner |
|---|---|---|---|---|
| 1 | UC-08 explanatory annotation | Design + implementation | Specify annotation resource/command/anchor diagnostics, then editor fixture | `06`, `08`, `10` |
| 2 | UC-09 multiple views | Design + implementation | Specify multi-context composition and isolation fixture | `13`, `06` |
| 3 | UC-10 Actual reconciliation | Design + implementation | Specify explicit resolve/unresolve commands and diagnostics | `10`, `13` |
| 4 | UC-12 baseline capture | Design | Specify immutable capture command/result; no branch fallback | `10`, `13` |
| 5 | UC-13 target output | Design + implementation | Specify capability requirement negotiation and adapter acceptance artifact | `08`, `09` |
| 6 | UC-11 CLI/automation | Implementation | Reuse existing Command/Context contracts in CLI and CI runner | `09`, `10` |

## 3. Exit criteria

For every design-gap item, its owning document must define a typed input, deterministic
outcome, failure diagnostic, and canonical fixture before an adapter implementation
starts. The Use Case Catalog mapping is then updated from “design gap” to
“implementation gap.”
