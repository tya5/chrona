# Subtree Summary Completion — Architecture Review

## Scope

Review the completion of `scope: subtree` semantics for P4 / issue #127 after
implementation discovery exposed the missing aggregation rule.

## Findings

| Boundary | Decision | Result |
| --- | --- | --- |
| Project Core → View | Core supplies hierarchy and planned facts; View supplies selected primary members. | Pass — no second tree or schedule authority. |
| View → summary normalization | Latest member planned endpoint is one scalar planned-completion fact. | Pass — deterministic, comparison-track independent. |
| summary → Layout | Summary emits semantic text only; Layout owns measurement and placement. | Pass — no geometry in View or summary normalization. |
| Layout → Scene → renderer | `summaryBar` remains a completed Layout shape and Scene primitive projection. | Pass — target adapters do not inspect hierarchy or metrics. |

## Compatibility and extensibility

The new scope is intentionally closed to typed object/planned metrics.  It
preserves existing unscoped object and catalog metrics, but does not retain any
ambiguous implicit subtree behavior.  The explicit scope leaves room for a
later typed aggregation vocabulary without overloading `format` or renderer
roles.

## Decision

Accept the correction.  Amend P4's implementation plan before resuming its
summary-schema and normalization implementation.
