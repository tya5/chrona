# #350 Icon Ecosystem Architecture Review

**Decision:** accept Specification 64 v0.2 as the required successor design;
do not resume the v0.1 implementation path.

## Boundary review

| Boundary | Decision | Prohibited regression |
| --- | --- | --- |
| Local collection → catalog | Importer normalizes a supplied local Iconify JSON file atomically. | Network/package lookup, raw SVG after ingress, partial output. |
| Catalog → Context | Context v0.11 pins a validated catalog set, not one ambient catalog. | Alias ambiguity, unpinned discovery, runtime import. |
| View → Layout | View v0.12 selects direct/encoded visuals and logical side; Layout accepts only resolved requests. | Theme asset selection, schema targets with no projection, Scene lookup. |
| Theme/metrics → Layout | Theme supplies ratios; successor font metrics supplies cap-height; Layout computes all advances/bounds. | Absolute author coordinates, line-box heuristic, renderer typography. |
| Layout → Scene | Layout produces bounds, paint-mode/stroke completion, and reading order. | Scene text measure, side selection, wrapping, or role lookup. |
| Scene → adapter | Adapter serializes normalized completed paths or closed raster bytes. | SVG interpretation, asset filesystem read, target fallback. |

## Whole-system consistency

- **Project/Actual/Snapshot:** no icon changes source facts, selection, or
  scheduling. Field encoding maps an already exposed View field to an existing
  visual catalog reference and rejects unknown values.
- **Colour Scheme and Theme:** assets are monochrome `currentColor`/`none` only.
  Theme resolves treatment and ratios, while label and mark roles remain
  separate. Literal asset colours cannot bypass Scheme authority.
- **Font metrics and Layout:** cap-height is unavailable in v0.1, so an exact
  successor resource is mandatory; approximate cap alignment would violate the
  design goal. Layout owns remeasurement after both visual sides reserve space.
- **Scene/model:** per-path mode and completed stroke are Icon-owned payload,
  distinct from general Layout relation paths. This avoids widening routing
  semantics merely to ingest icon artwork.
- **Output profiles:** SVG/PNG only remain exact; #349's PDF rich-paint
  rejection is unaffected. A future PDF/Typst/TikZ claim needs separate design
  and direct evidence.
- **Materialization/packages/Design Space:** catalog files and static PNG bytes
  close like other Context inputs. The importer is explicitly outside render and
  package acquisition; Design Space can expose only validated View requests.
- **Schema evolution:** render-context v0.11, view v0.12, icon-catalog v0.2,
  and font-metrics v0.2 replace predecessors. Schema inventory must name each
  predecessor as transitioning with a removal slice; no compatibility parser is
  retained after corpus migration.

## Requirement audit

R350-01/02 are resolved by bounded ingestion and per-path normalized paint;
R350-03/04 by catalog-set closure/import/default; R350-05/06/07 by complete
typed target inventory and side-aware slots; R350-08/09 by metric/paint
ownership; R350-10/11 by public evidence/draft ingress; and R350-12 by the
mandatory requirement matrix and release checklist. No row is rejected or
deferred at this design stage.

## Preconditions for implementation planning

Before implementation starts, publish an implementation plan that assigns every
R350 row to independently reviewable slices and names:

1. actual corpus fixtures and importer deterministic tolerance;
2. schema/resource removal and migration sequence;
3. each label/mark target's source projection;
4. successor font metric generation and cap-height evidence;
5. public bundled catalog/notice generation and artifact-size limits; and
6. focused, full, materializer, conformance, wheel, generated-output, and CI
   acceptance evidence.

