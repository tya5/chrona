# Gantt Comparison Groups and Legend — I58-4 Acceptance Review

**Status:** Accepted for publication after I58-3 merge `38517ff`.

## Architectural consistency

View alone selects `grouping.presentation`; its absence is `band`. Layout rejects
an enabled header without the declared theme capacity, reserves and measures each
header, and is the only producer of legend swatch/text geometry. Detail Profile
selects legend entries, while Layout Profile selects the legend slot. The CLI
passes the immutable detail closure to ingress; Scene projects accepted placements
only. This preserves ADR-0031 and Specification 50 §3.4.

## Evidence

- Focused Scene/normalization tests pass; group headers require explicit capacity
  and legend entries emit role-derived swatch/text pairs only when a slot exists.
- Full suite: `251 passed` (seven pre-existing jsonschema deprecation warnings).
- Five public materializer byte checks pass after regenerating only HALCYON
  programme-board evidence.
- The 1920×1080 programme-board PNG was rasterized and visually reviewed: group
  bands are headed, legend labels fit, and no new clipping or overlap is present.

## Resource scope

Only HALCYON programme-board gains the useful header and legend declarations.
Existing Controller-Z group-header output is made explicit in its View resources;
no renderer or example-specific branch was added.
