# Design Plan — Detail-Panel Readability (#445)

**Programme:** #454 P0 / D454-3 and I454-P0-4.  
**Entry state:** #439/#443 paint and axis composition (`cef5b60b`) and #435
boolean-table presentation (`a292afd9`) are published on `main`.  This plan
does not treat their CI release review as evidence that #445 is complete.

## Problem statement and current-state audit

#445 records a severe overlap in `controller-z-ja/executive`: group details
and milestone digest entries are each placed as independently measured,
single-line text at the first baseline of adjacent narrow slots.  Current
`surface_composer.py` still performs that placement for every `notes`,
`group-details`, and `milestones` source.  It records available inline bounds
but does not use them to derive lines or a block allocation.

The current Controller-Z Japanese layout declares `visible-overflow`, rather
than the historical `diagnose` cited in the issue.  That is a #449-compatible
visible disposition, but it does not authorize one panel to obscure another;
the side-panel content remains unreadable.  The scope is therefore completion
of the `group-details` and `milestones` panel blocks, not a global, implicit
change to every text slot or an adapter-specific clipping rule.

## Goals

1. Make detail and digest text a measured multiline Layout result, constrained
   to its own slot inline bounds.
2. Allocate a deterministic block extent from the finished lines, typography
   line height, and declared panel spacing before Scene projection.
3. Preserve every completed text fact: source content, lines, bounds,
   baseline, selected family/weight/asset identity, slot, and overflow
   disposition.
4. Prevent adjacent panel overprint in all affected public materializers and
   make the Japanese executive slide readable.

## Design questions and evidence to collect

| Question | Required evidence / decision boundary |
| --- | --- |
| Which sources receive block composition? | `group-details` and `milestones` only; notes, legends, table cells, labels, and annotations retain their owned policies. |
| Who owns wrapping? | Layout calls its existing measured `wrap_text`; Scene and adapters receive only completed lines and cannot choose breaks. |
| What establishes a panel's available rectangle? | The Layout Manifest slot allocation plus Layout-owned post-measurement panel allocation; no View coordinate, renderer viewport, or Scene list order becomes authority. |
| How are adjacent blocks kept disjoint? | Layout computes a shared panel-band allocation/required block extent and validates completed text bounds against their assigned panel. |
| What if the requested canvas is too short? | Layout completes an expanded canvas and emits a typed #449-compatible visible-overflow warning.  It never silently clips, drops, or overlays a neighbouring slot. |
| How are oversized individual tokens treated? | Reuse the slot's declared finite overflow disposition after measured wrapping; record the disposition in completed placement/warning rather than adding an implicit renderer fallback. |
| Does this alter content semantics? | No.  Review-detail validation, ordering, milestone formatting, typography selection, and source identity stay unchanged. |

## Architectural review criteria

- Intent → Layout → Scene → adapter remains one way.  No Scene, SVG, Typst,
  or TikZ line-breaking/relayout may be added.
- The feature composes existing typed `TextPlacement` and `Rect` facts; it
  does not introduce renderer-neutral prose layout in the Review resolver.
- The existing explicit overflow taxonomy stays finite.  A warning represents
  completed Layout geometry, not a recovery instruction for an adapter.
- The solution does not widen #445 into #446's general slot-containment
  evaluator.  #446 will consume the completed artifacts as a later gate.
- All produced geometry is rounded/contained with the existing Layout
  tolerance and is included in `_completed_canvas` before Scene construction.

## Design deliverables and publication order

1. Publish this plan, then a focused English design defining panel-band
   allocation, line/baseline sequence, containment invariants, and overflow
   records.
2. Publish an architecture review against the programme design, #449 visible
   fit policy, completed-placement model, and #446 boundary.
3. Publish an implementation plan naming source code, fixtures, generated
   evidence, focused tests, and release checks.
4. Only then implement one atomic #445 source/corpus/materializer change.
   Run focused tests and public materializers locally; batch CI verification
   with the other P0 changes rather than polling individual commits.
