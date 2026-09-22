# Gantt Comparison Groups and Legend — I58-4 Design Review

**Decision:** Proceed with the I58-4 plan.

| Layer | Decision | Boundary check |
| --- | --- | --- |
| Project | Supplies grouping facts and no presentation geometry. | No group header is persisted in Core. |
| View | Selects grouping presentation. | It cannot choose header coordinates or text metrics. |
| Detail Profile | Selects ordered legend semantics. | It cannot allocate a legend region. |
| Layout Profile | Declares a legend slot. | It cannot select entries or renderer paint. |
| Layout | Reserves header capacity and completes header/swatch/text placement. | It owns measurement and overflow diagnostics. |
| Scene/renderer | Projects accepted placements and resolved semantic roles. | It neither infers a fallback legend nor computes geometry. |

This is consistent with ADR-0031 and Specification 50 §3.4. Header capacity and
legend existence are declarative resource decisions, so HALCYON changes remain
general-purpose evidence rather than example-specific behavior. I58-3 quality
policies remain unchanged; I58-5 alone owns the final cross-slice release gate.
