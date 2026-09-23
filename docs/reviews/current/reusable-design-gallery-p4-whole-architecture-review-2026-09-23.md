# Reusable Design Gallery P4: Whole Architecture Review

**Status:** Accepted  
**Date:** 2026-09-23  
**Scope:** GDF-1 through GDF-4: Design Space summary, gallery evidence,
declarative Presentation Package, user reference/acquisition, source topology,
and visual-capability admission.

## Reviewed architecture

```text
human package/preset selector
            │ explicit acquisition only
            ▼
verified package manifest + immutable lock
            │ already-acquired ordinary resources
            ▼
Authoring Normalizer ───────────────► Project / Actual / View / Theme / Scheme / Layout
                                                    │
                                                    ▼
                                              Context → Layout → Scene → adapter

effective ordinary presentation resources ─► PresentationDesignSummary ─► gallery catalogue
corpus Context + public materializer bytes ────────────────────────────────┘
```

The upper render path and lower inspection/documentation path are deliberately
one-way.  A package selector becomes meaningful only through a verified lock;
the summary and gallery observe the effective resources but cannot alter their
selection, geometry, Scene, or target output.

## Requirement-by-requirement audit

| Requirement | Authoritative design evidence | Result |
| --- | --- | --- |
| Design Space has a bounded gallery consumer | Specification 55 §3.1 and P1 review | Pass — summary is pure inspection over complete effective ordinary resources. |
| Existing ownership remains singular | Specifications 55/59 and P1/P3 reviews | Pass — View, Layout, Theme/Scheme, Scene, and adapter responsibilities are unchanged. |
| Gallery is provenance/evidence, not rendering authority | Specification 58 successor and P2 review | Pass — catalogue assertion validation is downstream of corpus/materializer/summary evidence. |
| Reusable resource source has a canonical topology | Specification 62 §3 and P3 review | Pass — package, corpus, gallery docs, runtime resources, and conformance fixtures have distinct roots. |
| User reference is usable and reproducible | Specification 62 §§2/4/5 and P3 review | Pass — short selector, explicit acquisition, verified provider-neutral lock, offline diagnostic, explicit update. |
| Stage-3 ownership is clean | Specification 62 §6 and Specification 51 | Pass — ejection writes ordinary explicit bundle/receipt and removes live package inheritance. |
| Reuse/fork preserves provenance | Specification 62 §6 | Pass — a fork has new package identity and `derivedFrom`; no mutable overlay. |
| Registry/package security does not leak code or network into rendering | Specifications 21/62 and P3 review | Pass — declarative static members only; acquisition precedes evaluation. |
| New visual richness cannot bypass portability | Specification 62 §8 and P2/P3 reviews | Pass — initial gallery is limited to current closed Scene capability; #345 is a mandatory gate for any additional capability. |
| Existing corpus remains materializable during migration | Specifications 58/62 and P2/P3 reviews | Pass — atomically migrate or retain explicit source; never leave a deprecated resolver dependency. |

## Source-tree and reference consistency

The selected topology has exactly one canonical owner for a reusable
View/Layout/Theme/Scheme/Preset: `presentation-packages/`.  An
`examples/<project>/` corpus consumes it through exact identity rather than a
copy.  The corpus owns only semantic inputs, Contexts, manifests, and generated
evidence.  `docs/gallery/` owns curation documentation, and neither a package
path nor a documentation path is evaluation identity.

The reviewed selector/lock split avoids two opposite failures: user-facing YAML
does not need to spell internal package addresses, while rendering does not
trust a human-friendly name, a version range, a cache path, or a registry
response.  This is consistent with the Revision Store/closure rules: verified
manifest and member bytes, not the acquisition mechanism, establish identity.

## Visual capability decision

No initial gallery direction may require gradients, images, clipping, shadows,
filters, arbitrary markers, raw SVG/XML, or other capability outside the
current portable Scene contract.  Such a direction stops at #345 design before
an asset or package member is authored.  This is an affirmative scope decision,
not a fallback: the first reusable gallery proves package/evidence architecture
using existing portable primitives and completed paint.

## Deliberate deferrals

- registry service, remote acquisition, publisher-verification service, and
  commercial distribution;
- package-to-package dependencies and executable plugins;
- Domain/Semantic Packages (#344) and the long-term framework research (#346);
- all #345 capability implementation;
- package, lock, summary, catalog, command, resolver, or gallery-fixture code.

## Implementation entry criteria

The following must be present in the next separately published implementation
plan before code is authorized:

1. exact successor schemas and migration targets with no legacy parallel
   reference reader;
2. locked acquisition/verification diagnostics and owned test fixtures;
3. summary/catalog input boundaries and no-authority structural tests;
4. atomic Stage-3 proof, provenance, and rollback behavior;
5. paired corpus variants using one semantic Project/schedule fixture;
6. full test, conformance, materializer byte, generated-SVG, wheel, and
   cross-platform CI gates for each independent slice.

## Conclusion

P1–P4 form a consistent design basis.  They create no new runtime authority
and leave no unresolved cross-layer responsibility.  The next step is GDF-5
implementation planning; implementation itself remains intentionally unstarted.
