# Reusable Design Gallery P2: Curation and Evidence Review

**Status:** Accepted  
**Date:** 2026-09-23  
**Authority:** Specification 58, Specification 55 P1 inspection summary, and
the Reusable Design Gallery Foundation plan (GDF-2).

## Decision

The gallery evolves from a flat slide index into a documentary design catalogue
whose claims are checked against corpus provenance and a derived Design Space
summary.  It remains outside evaluation: neither a catalogue entry nor a
gallery page chooses a View, Theme, Scheme, Layout, target, renderer, or
fallback policy.

The catalogue has two deliberately separate kinds of information:

- machine-checkable finite assertions about source identity, paired comparison,
  Design Space values, and Context target/capabilities; and
- editorial narrative and accessibility rationale, which remain human-reviewed
  documentation.

This separation prevents prose from becoming a weak presentation contract while
still making a gallery useful to someone selecting a reusable design.

## Evidence flow

```text
corpus manifest + Context + materializer bytes
                  │
                  ▼
       effective ordinary resources
                  │
                  ▼
    PresentationDesignSummary (P1)
                  │
                  ▼
  gallery catalogue assertions + narration
```

The direction is one-way.  The gallery cannot write to any earlier stage.  A
catalogue validator may reject publication if evidence is missing or a claim is
false; normal materialization remains unchanged.

## Paired-variant rule

Every gallery comparison declares a peer group and one comparison axis.  Its
members pin the same semantic Project/scheduling evidence.  A different
Project, title similarity, or a hand-labelled relation is insufficient.  This
rule makes it possible to identify a presentation difference without confusing
it with different semantic data.

## Accessibility and target review

The catalogue records the target/capability profile actually pinned by the
Context and a concise accessibility rationale.  It cannot claim that colour,
an optional effect, or a raster preview is the sole carrier of meaning.  Any
future capability not supplied by the current Scene contract must first follow
the conditional #345 design path; the catalogue cannot authorize it.

## Acceptance criteria for later implementation

1. Existing v0.1 gallery references migrate atomically to the successor
   catalogue; no compatibility reader remains.
2. Tests reject each invalid evidence edge independently: corpus, Context,
   materializer, summary identity, assertion vocabulary/value, and peer group.
3. A valid paired set proves identical semantic schedule provenance and distinct
   effective presentation provenance.
4. Narrative metadata and accessibility notes have no import path into View,
   Layout, Scene, renderer, or materializer.
5. Generated SVG remains materializer-owned and an empty generated-artifact
   diff remains a release requirement.

## Conclusion

P2 gives gallery entries a reusable-design explanation without giving them
authoring authority.  P3 can now define how the ordinary resources behind an
entry become one declarative Presentation Package.
