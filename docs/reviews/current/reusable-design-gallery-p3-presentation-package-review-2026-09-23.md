# Reusable Design Gallery P3: Presentation Package Architecture Review

**Status:** Accepted  
**Date:** 2026-09-23  
**Authority:** Specification 62, Specifications 13/21/51/55/58/59, #343, and
the Reusable Design Gallery Foundation plan (GDF-3).

## Decision

A Presentation Package is a declarative bundle of existing ordinary resources,
not a presentation extension registry.  Its manifest is the only canonical
source for package members; a package-aware lock is the immutable acquired
identity consumed by guided authoring.  Gallery metadata remains downstream
documentation and cannot resolve a package.

The first implementation profile deliberately has no package dependencies,
remote registry, or executable member type.  This is a structural boundary,
not a temporary fallback: a later dependency or plugin capability needs an
independent accepted design under Specification 21.

## Whole-architecture review

| Concern | Decision |
| --- | --- |
| Semantic authority | Packages cannot carry Project/domain semantics, scheduling, or new semantic registry entries; they select existing View/Theme/Scheme/Layout contracts only. |
| Presentation authority | View owns content/grammar, Layout owns geometry, Theme/Scheme own appearance, Scene remains derived. A package does not add an override bag or renderer configuration. |
| Closure identity | Selector and cache path are convenience. Exact manifest/member identities and lock are declared closure/provenance inputs; no mutable lookup can occur during render. |
| Source topology | Package source, project corpus, docs gallery, runtime resources, and conformance fixtures have separate roots and one canonical owner per resource. |
| Materialization | Stage 3 copies ordinary resources and records `derivedFrom`; it removes, rather than masks, the package inheritance edge. |
| Offline/security | Acquisition verifies declarative bytes before use. Offline absence fails explicitly; raw SVG, code, network fetch, and host defaults are excluded. |
| Capability scope | A package may use only already-supported host visual capabilities. #345 precedes any richer treatment. |

## Consistency with existing specifications

Specification 21 already requires verified immutable package acquisition and
forbids `latest`, arbitrary code retrieval, and mutable package references.
Specification 51 already defines guided normalization and one-way explicit
materialization.  Specification 59 closes the semantic registry against
package-defined visual semantics.  Specification 62 specializes those rules
for a reusable presentation resource bundle without weakening any of them.

## Required implementation boundaries

1. The package-aware contract is a clean successor; no parallel legacy guided
   resolver survives.
2. Local package acquisition is sufficient for the first release only when its
   stored lock/reference is provider-neutral and verifies the same immutable
   data that a future private registry would provide.
3. Existing corpus fixtures either retain explicit source or migrate atomically
   with a verified package and materializer evidence.
4. A package never becomes materializer output, and generated SVG never becomes
   a package member authority.

## Conclusion

P3 completes the reusable-design boundary.  P4 may now review P1–P3 together
and determine whether #345 is needed for the initial gallery directions.  No
package schema, lock command, resolver, or gallery fixture is authorized until
the separately published implementation plan.
