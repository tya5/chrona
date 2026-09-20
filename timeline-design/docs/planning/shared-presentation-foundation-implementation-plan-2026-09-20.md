# Shared Presentation Foundation: Implementation Plan

**Status:** Complete. The former G1–G4 judgment remains historical, while the corrective
D0→D3/I1→I3/V1 sequence is now implemented, validated, and accepted.
**Scope:** Implement the shared foundation only. Do not branch on ASTER, Controller Z,
or image concepts A through D.

## Implementation order

| Unit | Change scope | Result and verification | Publication boundary |
|---|---|---|---|
| G1.1 axis primitives | New pure Date-only axis module and unit tests | Half-open windows, month/quarter/ISO-week/day intervals, tick step, input invariance, out-of-range diagnostics | Publish this unit alone |
| G1.2 settings/metrics closure | Presentation-settings resolver, font metrics, layout solver, negative tests | Revision/hash checks, family×weight measurement, explicit intrinsic inputs for content/fraction/min/max/gap, no implicit fallback | Publish this unit alone |
| G1.3 comparison-mark meaning | New mark/anchor projection and unit tests | Planned/Actual/baseline, span/point, missing observations, negative/zero/positive variance, stable source identity | Publish this unit alone |
| G1.4 Scene connection | Boundary between Scene construction and **all public SVG adapters**; migration adapters for existing Gantt/review/minimal | Adapters do not reinterpret schedule or placement; legacy remains separate and provenance metadata survives | Publish this unit alone |
| G1.5 consumption audit | Setting-mutation table, literal inventory, raster/reproducibility verification | Zero unconsumed G1 settings and zero implicit fallbacks | Publish as G1 completion |
| G2 | Axis-slot integration, labels, comparison mode, group×facet paint | Common A/D presentation from Specification 30 §§6–7 | Publish by unit |
| G3 | Annotation box/leader and explanation slot | One mechanism handles work notes and planned-gate explanations | Publish by unit |
| G4.1 | Stable-lane Scene | Reuse shared label/mark/route occupancy and emit stack metadata | Published |
| G4.2 | Lane-surface adapter | Preserve row correspondence for row-aligned; map independent-lane-track to Scene-derived track geometry and stack offsets | Completed and published |

### G2–G4 design gate

Specification 31 fixes G2–G4 authoring owners, finite algorithms, diagnostics, and
prohibited recoveries. Owner schemas, positive/negative fixtures, and cross-cutting
review exist. Resume G3 visual implementation only after publishing and validating the
following correction across every artifact: exclude only the annotation's own anchor
mark during box candidate checks, restore all marks during routing, and exclude
annotation boxes from lane occupancy. Begin actual G4 vertical offsets only after the
contract for `row-aligned` (one item per row, stack metadata retained) and
`independent-lane-track` (Scene-derived pitch and track bounds) is closed across
specification, schema, fixtures, and review.

### G1.1 completion record

`src/chrona/presentation_axis.py` adds renderer-independent Date-only intervals. It
clips half-open month, quarter, ISO-week, and day intervals and returns labels and
stable indices for natural calendar buckets. Existing SVG renderers do not yet call it.
`tests/test_presentation_axis.py` verifies window boundaries, ISO week-years, tick
steps, invalid inputs, and reproducibility. 135 tests passed with two existing
RefResolver deprecation warnings.

### G1.2 completion record

The base preset verifies not only ID but revision and exact-byte SHA-256, and selects
font assets by family×weight. A `content` region/track diagnoses a missing explicit
intrinsic input; fixed/content, then fraction plus gap/min/max, resolves
deterministically. Five Aster settings files and Controller Z were migrated to the new
font-asset arrays. 139 tests passed with two existing RefResolver deprecation warnings.

### G1.3 completion record

`presentation_marks.py` projects renderer-independent planned, Actual, baseline, and
finish-delta marks for spans and points. A span Actual is accepted only when both start
and finish are observed; missing endpoints are not completed from planned. Variance
keeps its sign, and zero visibility is an explicit policy.

### G1.4 completion record

`PresentationScene` constructs axis intervals, ticks, and comparison marks from the
View window; the table/timeline SVG adapter converts them to coordinates and SVG.
Scene input emits half-open axis intervals unchanged, fixing a terminal month dropped
by the legacy renderer. A one-ended Actual emits no Actual mark and is not completed
with a planned endpoint. ASTER reference SVG was regenerated. 148 tests passed.

### G1.4 reopening record

The G1.5 static consumption audit found that `render_review_svg` and `render_svg` still
generated axes and planned/Actual marks directly. The original wording "existing
Gantt" did not satisfy Specification 29's all-public-SVG-path condition. G1.4 remained
open until both adapters consumed `PresentationScene` with the same missing-Actual and
half-open-axis contracts.

This reopened item is complete. Review/minimal adapters now receive axes and marks from
`PresentationScene`, and a single-point display uses
`layout.scale.singlePointSpanDays`. 149 tests confirm that every public SVG path crosses
the same Scene boundary.

## G1.1 contract

`presentation_axis.py` converts Date-only `[windowStart, windowEnd)` to a finite list
of renderer-independent axis intervals. Each interval has only `start`, `end`, `level`,
`label`, and `index`; it has no coordinates, colors, fonts, SVG strings, or locale
fallback.

- Weeks use ISO-8601 and start Monday.
- Month/quarter/week/day boundaries do not extend outside the window; first and last
  intervals are clipped to it.
- Labels derive from natural interval boundaries, not renamed from the clipped start.
- `end <= start`, unknown levels, and non-positive `tickStep` return stable ValueErrors.
- Tick step filters the interval list only; it changes neither the window nor label
  meaning.
- Equal input produces equal ordered values without mutating input objects.

G1.1 does not yet connect to existing renderers, so it changes no existing PNG pixels.
This deliberately fixes the isolated semantic contract before treating a setting as
supported.

## Interruption rule for G1.2–G1.5

If implementation finds a new ownership, schema, or migration conflict between
Specifications 30 and 29, pause the affected unit and update/publish specification,
schema, fixtures, and this plan first. Do not accept sample-specific appearance
branches, implicit environment-font fallback, or SVG-side replacement.

## Completion judgment

A unit is not complete until it:

1. Tests normal, boundary, and invalid input.
2. Proves that existing semantic values and input remain unchanged.
3. Reproduces deterministically from the same input.
4. Reviews and publishes only its target diff, non-force.
5. Does not report unsupported scope as complete.

### Former G3/G4 completion record (withdrawn)

G3 connected common annotation boxes/leaders to SVG with explicit facet anchors. Box
placement excludes only its own anchor mark; leader routing restores all obstacles.
G4 implemented a stable-lane Scene preserving group order, independent lane-track
geometry, and the stack-offset adapter. The full suite passed 164 tests on 2026-09-20,
with two existing DeprecationWarnings.

This record does not prove shared-Scene consumption on public outputs,
purpose-specific projection, application of lane geometry, or fixture/validator
synchronization. Because the integration audit reproduced R01–R04 as P0, this section
MUST NOT be used as completion evidence.

### Restored completion record after remediation

Completion is restored only on the corrective evidence, not on the withdrawn record
above. Every public settings-backed SVG route selects a completed `SceneSurface` whose
primitives already own temporal projection, rows/lanes, measured text, ports, finite
routes, annotations, summaries, and stable identity. The V1 manifest adds immutable
viewport, selection, font, normalized-family, and per-surface scale evidence without
becoming an authoring resource. Missing scale evidence diagnoses rather than invoking
an adapter fallback.

The implementation parent is `b32b1237ee60a0da892372acc150009dc69c91b0`.
The final suite passes 179 tests with two existing deprecation warnings, the complete
conformance runner passes, and the acceptance review records structural, behavioral,
and image evidence. No G1–G4 corrective implementation scope remains.
