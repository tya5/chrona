# Issue 145 Network Title-Placement Implementation Amendment

## Authority

This amendment implements the merged network title-placement design correction
and completes N145-3A before N145-3B Scene work resumes.

## Scope

1. Extend the typed network Layout entry point to consume the resolved `title`
   slot bounds and measured heading run in addition to its current network
   inputs.
2. Return a complete title `TextPlacement` in the same closure as the node
   labels and relations.  Validate required title source, slot fit, typography,
   baseline, asset identity, and viewport containment in Layout.
3. Add focused source/layout tests for deterministic title placement and
   overflow/missing-input diagnostics.  Confirm table/timeline title output is
   unchanged through the existing materializer byte checks.

## Acceptance and publication

The completion PR requires focused tests, full pytest, conformance, import and
reachability gates, public materializer checks, and generated-SVG diff review.
After it is merged, N145-3B may consume the completed closure; it must not add
title measurement or coordinate logic.
