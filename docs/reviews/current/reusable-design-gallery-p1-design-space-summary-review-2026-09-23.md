# Reusable Design Gallery P1: Design Space Summary Review

**Status:** Accepted  
**Date:** 2026-09-23  
**Authority:** Specification 55, Specification 51, Specification 58, and the
Reusable Design Gallery Foundation plan (GDF-1).

## Decision

The gallery is the first bounded consumer of the Presentation Design Space.
It consumes a read-only `PresentationDesignSummary` derived from a complete,
validated effective View, Layout Profile, Theme, and Color Scheme bundle.  It
does not introduce a Design Space document into the render closure, a new
presentation resolver, or a generic author override map.

The summary is intentionally an inspection projection.  It records the four
selectable Design Space dimensions and the immutable identity of every owning
resource.  It omits any value that cannot be represented as stable authored
intent.  Omission is preferable to guessing, because a gallery classification
must never become an alternate policy source.

## Boundary review

| Boundary | Evidence | Decision |
| --- | --- | --- |
| Project/Actual → presentation | Design Space owns presentation intent only. | Summary has no semantic facts, observations, schedules, or resolved dates. |
| View → Layout | View selects content; Layout derives placement. | Summary may expose declared View and Layout intent, never row geometry, label coordinates, or routes. |
| Theme/Scheme → Scene | Theme/Scheme resolve appearance before Scene. | Summary reports declared role/token vocabulary and resource identity, never completed Scene paint or renderer literals. |
| Guided → explicit | Specification 51 normalizes a guided workspace to ordinary resources and Stage 3 ejects to them. | Summary accepts the effective ordinary bundle for either origin; it never replays guided operations or retains an inheritance edge. |
| Gallery → materializer | Specification 58 makes corpus Context/materializer evidence authoritative. | Summary is documentation/inspection data and cannot select an output, target, or materializer behavior. |

## Version correction

Specification 55 referred to View v0.8 and Theme v0.3 while the live resource
contracts are View v0.10 and Theme v0.4; Color Scheme v0.2 is now named
explicitly.  This correction changes no ownership or compatibility policy.

## Acceptance criteria for later implementation

1. A paired fixture with one Project/schedule and different ordinary
   presentation resources produces different summaries and closures.
2. Summary construction is deterministic for equal effective resources and
   identities.
3. Summary construction neither imports Layout/Scene/renderer nor changes
   materializer bytes.
4. Incomplete, identity-inconsistent, and unrepresentable inputs report the
   specified inspection diagnostics without changing normal render behavior.
5. Gallery catalog validation consumes summary evidence only after corpus and
   materializer provenance have been established.

## Conclusion

The Design Space now has a constrained consumer without becoming a new layer
of presentation authority.  P2 may define gallery curation around this output;
implementation remains prohibited until the package and gallery design work is
also accepted.
