# M7 Interactive Editing Progress Review

**Date:** 2026-09-19  
**Status:** In progress — reconciliation slice accepted; milestone not complete

## Design-conformance review

This slice uses only the complete contracts in [Command Model](../specification/10-command-model.md),
[View Model](../specification/06-view-model.md), and [Presentation Format](../specification/13-presentation-format.md).
It closes no M7 exit criterion by reinterpretation: the client produces a previewable
proposal, and a separately revisioned Actual-store Command performs the only mutation.

| M7 requirement | Current result | Design evidence |
|---|---|---|
| Gesture-to-Command boundary | Pass | `propose_actual_resolution` returns stable IDs and base revision only. |
| Explicit Actual reconciliation | Pass | `resolve_actual_observation` accepts only an unmatched identity and a supplied known Project ID. |
| Stale/conflict behavior | Pass | Actual-store CAS rejects a mismatched base revision with `E_CONFLICT`. |
| No implicit alignment | Pass | Source identity is preserved as result provenance; titles are never inputs. |
| No plan or Scene mutation | Pass | The Actual store is independent; no Project, scheduler, or Scene argument is accepted. |
| Actual undo/redo interaction | Pass | Reconciliation is reversible only through a current-revision Command; undo and redo each create a new Actual revision. |
| Annotation editor | Not started | Requires the View-definition command executor. |
| Client conflict/rollback presentation | Not started | Requires an interactive controller over the Command result surface. |

## Changed-code classification

| Path | Classification | Reason |
|---|---|---|
| `src/chrona/actual_commands.py` | shared service | Revision-bound Actual alignment command and explicit CAS boundary. |
| `src/chrona/gestures.py` | adapter | Creates an inspectable request only; no direct mutation. |
| `tests/test_actual_commands.py`, `tests/test_gestures.py` | acceptance evidence | Covers resolution, stale conflict, invalid targets, and non-repeatable alignment. |

## Next implementation slice

Complete the Actual-store undo/redo command history, then implement the View-local
annotation command path. M7 is not eligible for its final reuse review until all rows
above marked `Not started` pass with full conformance inheritance.
