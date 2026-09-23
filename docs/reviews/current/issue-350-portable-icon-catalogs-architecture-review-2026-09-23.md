# Architecture Review: Portable Icon Catalogs (#350)

**Decision:** Accepted for implementation planning
**Reviewed artifacts:** issue #350, the #350 design plan, and Specification 64

## Boundary review

| Boundary | Decision | Verification obligation |
| --- | --- | --- |
| Resource / asset bytes | `icon-catalog` is an ordinary pinned Context input; asset bytes are separately identity-checked and materialized | mutate, escape, missing, duplicate, and unsafe SVG/PNG fixtures reject before Layout |
| Semantic / Theme | View/semantic binding selects a namespaced icon and occurrence; Theme maps its role only to treatment | Theme cannot carry a path, icon ID, raw SVG, literal colour, or fallback |
| Layout / Scene | Layout reserves icon-plus-text geometry and emits complete icon placements | structural test rejects Scene font metrics, text measurement, coordinate choice, or catalog lookup |
| Scene / adapter | `Icon` has completed normalized vector or raster payload/bounds/accessibility data | SVG/PNG adapters serialize only Scene; no host path reads or target-driven policy |
| Profile / target | one exact v0.7 target profile contains its complete visual/icon capability set | SVG/PNG prove both classes; PDF receives a profile only after characterization; Typst/TikZ/baseline reject |
| Package / gallery | initial catalog is ordinary local closure; package reuse remains subject to Specification 62 acquisition | no package resolver or directory scan is introduced |

## Whole-system consistency

The design preserves the established one-way authority chain. It does not widen Project
semantics, bypass the Resource envelope, introduce a renderer-owned feature, or turn the
materializer into an asset resolver. The only new closure responsibility is generalising
the existing exact-byte font-asset pattern to a catalog-declared, bounded asset list.
That addition is necessary for reproducibility and is deliberately independent of the
deferred Presentation Package acquisition workflow.

`Icon` must remain separate from `Symbol`: reusing Symbol would make a semantic marker
arbitrarily drawable and conceal immutable asset/accessibility requirements. Reusing Path
would lose asset provenance and tempt adapters to resolve styling. A normalized vector
payload provides portable geometry without raw SVG reach-through. PNG remains a closed
byte payload and not a general image feature.

Specification 63 retains authority over generic visual capability fidelity. Specification
64 adds icon capability to one coherent v0.7 target-profile set because icon payload
fidelity is not guaranteed by v0.6 paint profiles. The implementation must not stack a
second profile selector. It must prove SVG and pinned PNG output independently. It must
characterize the actual PDF route for both icon classes; a PDF profile is permitted only
if that evidence passes, while Typst and TikZ remain baseline-only.

## Required implementation constraints

1. Publish schema/typed closure before any renderer or gallery fixture.
2. Parse SVG with a closed parser/normalizer; never use an SVG renderer as validator.
3. Implement both declared `vector` and `raster` source classes before claiming #350;
   no SVG-only public catalog is an acceptable end state.
4. Route all leading-label geometry through Layout; a Scene compatibility branch is a
   design deviation.
5. Add source-to-materializer byte identity evidence and negative capability/security tests
   before closing the issue.
