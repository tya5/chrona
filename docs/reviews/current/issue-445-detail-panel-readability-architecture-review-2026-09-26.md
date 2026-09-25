# Architecture Review — Detail-Panel Readability (#445)

**Design under review:** `issue-445-detail-panel-readability-design-2026-09-26.md`  
**Status:** Accepted for implementation.

## Review matrix

| Concern | Result | Evidence / required guardrail |
| --- | --- | --- |
| Layout ownership | Pass | Existing `surface_composer` already resolves slots, metrics, text placements, completed canvas, and `FitWarning`; the new panel helper belongs there. |
| Scene projection | Pass | The v0.5 builder passes `TextPlacement.lines`, bounds, font facts, slot facts, canvas bounds, and warnings through verbatim. |
| Adapter neutrality | Pass | SVG, Typst, and TikZ already serialize supplied `TextLayout.lines`; none receives Layout Manifest, Theme, font metrics, or overflow policy. |
| #449 fit policy | Pass | `visible-overflow` remains a successful completed result with a finite structured warning and canvas growth.  `diagnose` is not reintroduced. |
| Semantic boundary | Pass | Review Detail Profile retains selection/reference validation only; no coordinate, wrap, or font decision leaks into its resolver. |
| Scope control | Pass | Only `group-details` and `milestones` acquire paragraph-like block composition.  #446 remains the general completed-Scene containment gate. |
| P0 paint work | Pass | Detail text keeps ordinary foreground `paint_order` and obtains no implicit host; #439/#443 relations remain unchanged. |
| P0 boolean work | Pass | The feature neither reads table-format contracts nor changes the #435 View v0.20 ingress. |

## Findings resolved before implementation

1. The historical issue describes `overflow: diagnose`, but current public
   Layout Profiles use the accepted #449 `visible-overflow` vocabulary.  The
   implementation must target current declarations and must not add a legacy
   spelling or error path.
2. A content-sized slot's pre-measurement one-line block size is not a hard
   viewport cap.  Treating it as one would make correct CJK wrapping fail or
   force an adapter crop.  Layout must publish the post-measurement slot block
   extent and include it in the completed canvas.
3. The completion helper must update both final slot geometry and final text
   geometry before the existing canvas calculation.  Updating text alone
   would leave a false containment contract for #446 to inspect.
4. The `SurfacePlacement.assert_valid` generic collision rule intentionally
   exempts `visible-overflow` text.  #445 therefore needs its own panel-pair
   containment/non-intersection invariant rather than weakening or changing
   the global rule.

## Required implementation evidence

- focused unit coverage for CJK wrapping, disjoint detail/digest text,
  overlapping panel-slot stacking, overflow warning/canvas growth, and Scene
  projection of completed lines;
- public Controller-Z Japanese executive reproduction and raster/SVG review;
- regenerated affected public materializers and generated-evidence review;
- structural search/test proving Scene and renderer modules do not import or
  call `wrap_text`, text measurement, or panel allocation;
- existing public materializer checks and CI matrix as the P0 release gate,
  batched with the already-published #439/#443/#435 work.

## Conclusion

The design closes the specific public-output defect through the architecture's
existing completed-placement boundary.  It adds no compatibility debt and
does not preempt #446.  Implementation may proceed only through a published
atomic implementation plan.
