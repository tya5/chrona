# Issue 256 Presentation Prefer-ladders Design Review

## Decision

Issue #256's required capability is already implemented by the published
Issue #125 correction and later inside-label work.  This review accepts that
capability as Specification 59 and rejects the issue's obsolete premise that
Layout has no ladder or registered extension point.

## Evidence against the current implementation

| Requirement | Published implementation | Owner |
| --- | --- | --- |
| Typed per-object intent | `presentationIntent` in View v0.8 and immutable row/item contracts | View/projection |
| Ordered prefer-ladder | validated `visibility.fallback` plus item/row preference prepending | View/Layout |
| Deterministic selected rung | `PlacementDecision` and `TextPlacement.selected_rung` | Layout |
| No Scene retry | completed placement projection and structural tests | Scene boundary |
| No raw extension geometry | closed `semantic_registry`; profile packages validate domain fields only | host vocabulary |

The original Issue #125 proposal to reuse a profile package as a presentation
extension registry was superseded by the published extension-boundary
correction.  Reviving it for #256 would make package schema validation a
second authority for Scene and Theme vocabulary, contradicting Specifications
11, 49, and 59.

## Whole-architecture review

The accepted contract preserves the direction of authority: Project and
profiles define domain facts; View declares preference; Layout makes all
geometry and quality decisions; Scene turns complete placements into standard
primitives; Theme resolves appearance; an adapter serializes.  No compatibility
path, renderer inference, or package-driven code execution is introduced.

## Consequence

There is no new dynamic registry implementation to write.  The implementation
phase is an acceptance audit of the live contract and non-default public
evidence.  Any future proposal for package-defined presentation vocabulary
must first introduce a separate immutable presentation-resource design and
complete its closure, Theme-role, and Scene-version contracts.
