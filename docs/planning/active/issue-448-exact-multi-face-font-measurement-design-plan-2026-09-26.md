# Design Plan — Exact Multi-Face Font Measurement (#448)

## Problem

Typography treatment selects a finite `(family, weight)` pair, and completed
text geometry must be measured by exactly the font bytes the target receives.
The immutable Context path already has a multi-face metric catalog, but the
draft-only `--system-fonts` ingress still resolves one face and rejects a Theme
that uses more than one weight.  That makes a normal regular-plus-bold Theme
unrenderable through the system-font workflow and preserves a separate,
smaller font-closure model at the ingress boundary.

## Established facts

- `FontMetricsCatalog.select(family, weight)` is the closed, typed selector
  used by Layout when an immutable Context declares multiple faces.
- `place_text` records the `content_identity` of the metric selected for its
  completed treatment; public HALCYON Scene evidence currently records the
  bold asset for weight-700 placements.
- A `DraftFontResolution` currently contains one `SystemFontFace`, one
  `FontMetrics`, and one `FontFile`; `_draft_system_font_resolution` rejects a
  Theme with multiple requested faces before Layout.
- The PNG registry accepts a tuple of identity-pinned `FontFile` objects, so
  target delivery can already carry a closed set of font files.
- System discovery verifies the exact requested family and OS/2 weight after
  `fc-match`; it must remain an exact lookup, never a host fallback.

## Questions

1. What typed draft resolution represents a deterministic catalog of exact
   installed faces without placing host paths or mutable host state in an
   immutable Context or Scene?
2. How are the Theme's actually selected `(family, weight)` pairs derived
   once, validated, sorted, resolved, and provided to both Layout and the PNG
   renderer?
3. Which boundary rejects a missing requested face, an identity change, a
   duplicate logical face, or a Theme request not represented by the draft
   catalog?
4. What corpus and system-font fixtures prove that each completed placement's
   asset identity matches its selected family/weight and that no 700 placement
   is measured through a 400 face?

## Deliverables

- An English design and whole-architecture boundary review.
- An implementation plan that separates typed catalog closure, draft ingress
  and renderer delivery, and public evidence/release verification.
- Exact multi-face `--system-fonts` support with no default-face fallback.
- A checked corpus identity audit and focused fixtures for regular-plus-bold
  system-font Themes.
