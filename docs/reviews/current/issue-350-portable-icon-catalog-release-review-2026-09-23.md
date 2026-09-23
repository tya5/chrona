# Release Review: Portable Icon Catalogs (#350)

**Decision:** Accepted

## Requirement audit

| Requirement | Evidence | Result |
| --- | --- | --- |
| User-extensible catalog with SVG and PNG | `icon-catalog/v0.1`, namespaced IDs, Controller Z `icons.yaml` | accepted |
| Immutable assets and materialized closure | content identity checks, path rejection, asset copying tests | accepted |
| No raw SVG at adapter boundary | closed SVG normalizer and `NormalizedVectorIcon`; serializer tests | accepted |
| Layout-owned leading label and mark geometry | View v0.11 binding and completed `IconPlacement`; materializer fixture | accepted |
| Scene projection only | Scene receives Layout placement payload/bounds; no asset path or source SVG field | accepted |
| Accessibility | decorative SVG is hidden; meaningful raster icon has catalog alternative and SVG accessible name | accepted |
| Exact target profiles | v0.7 SVG/PNG admit icon capabilities; baseline/PDF/Typst/TikZ reject | accepted |
| Public reusable evidence | Controller Z icons slide contains vector leading label and raster mark, with pinned asset bytes | accepted |

## Verification

- focused icon/profile/materializer/vocabulary batch: `49 passed`;
- full suite: `505 passed, 11 skipped`;
- wheel build: passed; isolated wheel schema-resource smoke: passed;
- public materializer regenerated `examples/controller-z/generated/icons.svg` and
  materializer/closure acceptance passed.

## Fidelity decision

SVG and pinned resvg PNG have direct implementation/evidence. The current PDF route was
not granted a v0.7 icon profile: no claim is made without independent vector and raster
characterization. This preserves #349's target-exact contract. PDF, Typst, and TikZ fail
required icon capability negotiation rather than omitting or approximating it.

No generic Image primitive, package resolver, raw SVG/CSS/XML, network lookup, or
renderer-local asset resolution was introduced.
