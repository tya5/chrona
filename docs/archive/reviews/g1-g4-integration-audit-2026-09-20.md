# G1–G4 Base-Design Integration Review

Target revision: `82e59f6e13fde8f6582f538da24b7523854c2cde` (published `main` at review start).
Scope is G1–G4, not a review of Specifications 11–14.
Status: Remediation required. Evidence in this review does not support the former
combined G1–G4 completion judgment.
Method: Independent Astra review plus source tracing, regression runs, and design
validator execution by the primary owner. No implementation change.

## Conclusion

The direction of consolidation is sound, but it does not yet reach Specification 08's
boundary in which a renderer consumes a placed Scene. The central error was treating
the existence of a function as equivalent to effective settings on public output. G4
stopped at calculators and did not connect independent-lane visualization. G3 retained
unimplemented purpose-specific contracts. The 164 passing tests prove regression of
existing cases, not comprehensive conformance to Specifications 29–31.

Retain the pure Date-only axis, comparison-mark, settings-resolution, placement-
candidate, and lane-assignment functions; the prohibition on completing Actual from
planned; Theme/Detail/Layout authoring ownership; fixed-reference checks; and existing
sample regressions. A full rewrite is unnecessary.

## Validation performed

| Validation | Result | Interpretation |
|---|---|---|
| `PYTHONPATH=src python -m pytest -q` | 164 passed, two existing warnings | Existing cases only |
| `validate_presentation_g2_g4_design.py` | AssertionError at line 23 | Expected set retained a removed negative diagnostic |
| `validate_shared_presentation_foundation.py` | Passed | Wire-structure check |
| `validate_presentation_settings.py` | Two schemas, four positive, fifteen negative, and 82 inventory groups passed | Design structure only, as documented |
| Project a bodyless highlight box | `E_PRESENTATION_LABEL_INPUT` | Decoration-only purpose incorrectly requires text measurement |
| Resolve explanatory-arrow source/target anchors | `E_PRESENTATION_ANCHOR_UNSUPPORTED` | Two-endpoint input reaches single-anchor processing |

Python ran in an adjacent Chrona work environment's venv and imported the fixed target
revision above. Other than test counts, the evidence is static or from the explicit
probes shown; comprehensive visual QA was not performed.

## Findings

P0 blocks completion/design approval. P1 repairs declared functionality or structure.
P2 improves change locality and verifiability for extension.

| ID | Priority | Finding and evidence | Impact / response |
|---|---|---|---|
| R01 | P0 | `presentation_scene.py:15–22` contains only axes, semantic marks, and lanes; `gantt_surface.py:78–383` performs measurement, placement, purpose interpretation, routing, and SVG generation. This conflicts with Specifications 08 §§3/5/7 and 30 §2. | Shared Scene is incomplete. Consolidate placed primitives and provenance in Scene; restrict renderer to serialization. |
| R02 | P0 | `lane_stack_offset` is defined at `presentation_lanes.py:83` but called only by tests. SVG ignores `lane_tracks` and always renders one item per row in `gantt_surface.py:219–309`. | Independent-lane-track is invisible. Reopen G4.2 and connect it through public SVG. |
| R03 | P0 | The validator really fails at line 23. Specification 31 changed row-aligned to retain metadata, but settings/wire/preset schema text still says stack zero only. | Specification, schema, fixture, and review did not close together. Make design validation a required normal-CI gate. |
| R04 | P0 | `presentation_annotations.py:64–99` applies a single anchor and text box to every purpose; `gantt_surface.py:357–382` does likewise. | Highlight and two-endpoint explanatory arrows cannot render correctly. Split into closed purpose-specific types and projections. |
| R05 | P1 | `gantt_surface.py:238–254,307–308,378–380` contains body/point centers and fixed offsets. `obstacles if b != own` excludes by coordinate equality, not owner ID. The resolver selects the first candidate. | May exclude other marks, route from interior ports, or connect the wrong instance across slots. Use geometry IDs with slot/source/facet/purpose and shape-derived ports. |
| R06 | P1 | `presentation_marks.py:39` renames planned to baseline according to comparison mode; anchor resolution requires exact planned/Actual. Point Actual exists in Scene but Gantt's point branch handles planned only. | Appearance changes break references and discard Actual. Separate semantic facet from visual role; consume the same marks in every public adapter. |
| R07 | P1 | `LaneItem` at `presentation_scene.py:37–44` uses planned dates only. Required labels, Actual, and point-symbol width are absent; a point becomes one-day occupancy. | Temporal intervals cannot detect visible collisions. Use measured occupancy on the common scale without changing point-date semantics. |
| R08 | P1 | `gantt_surface.py:314–321` draws only month/quarter although settings allow week/day. Month display and scale/row dimensions are recalculated in the adapter. | Public G1 display is incomplete despite generated primitives. Complete band bounds and labels in common Scene. |
| R09 | P1 | Gantt calls `resolve_font_metrics` once without weight and reuses it for bold. `actualHeight`, point size, `maxCandidates`, and other settings are unconsumed; fixed values 4/5/9/12/17 remain. | Schema acceptance differs from output. Share measurement and drawing per role and add mutation tests for every setting. |
| R10 | P1 | Annotation routing consumes only `limit`, not `clearance`, `gridOffset`, `portOffset`, or `bendPenalty`. The dependency router is separate. No-path and limit-exceeded share a diagnostic. | Common routing policy is split. Share the search core while preserving `sourceKind` policy and failure reason. |
| R11 | P2 | Stable primitive `sceneId`, slot instances, and input-manifest integration are incomplete. `source_ref` alone cannot distinguish multiple primitives. | Reactive UI and other backends require repeated work. Unify on Specifications 08/09 Scene identity and test locality of diffs. |
| R12 | P1 | `gantt_surface.py:122–124` depends on table/timeline key names instead of slot sources; `:339` controls routing from the legacy profile even for v0.2; `:356,387–391` bypasses the annotations slot and lists Project annotations separately as notes. | Normalized settings and View selection can be bypassed. Resolve by source and validate capabilities before rendering. |

The independent Astra review also classified R01/R02/R04 as completion blockers. Its
findings came from code tracing; the primary owner reproduced the execution evidence at
the same revision.

## Layer-consistency evaluation

| Boundary | Assessment | Design decision required |
|---|---|---|
| Core/Schedule → View Projection | Independence direction is sound | Display mode never renames semantic facets; add no date completion |
| View/Style/Theme/Detail/Layout → resolved input | Owners are separated but output does not consistently honor them | Inventory the sole consumer and scope of each setting |
| Resolved input → geometric Scene | Largest gap | Complete measurement, placement, and routing without requiring adapter reinterpretation of dates or View |
| Scene → SVG / other backend | Capabilities differ among Gantt/review/minimal | Use common primitives and capability validation; isolate legacy at a separate boundary |
| Schema → fixture → test → completion | Current process misses inconsistency | Require not only validator success but evidence that declared settings affect geometry |

## Extensibility and omitted combinations

"Shared" does not mean a new universal DSL or arbitrary plugin framework. Prefer
sharing existing primitives and measurement results. Priority combinations are missing
Actual/point Actual, baseline display plus planned anchor, the same object in multiple
slots, long Japanese or bold text, colocated marks and required-label collisions,
insufficient lane height, route-search limits, and every public SVG path.

Label placement and stack assignment in G4 can also form a cycle; excluding annotation
boxes alone does not prove termination. Specify a normative order, such as evaluating
finite candidates in local coordinates before fixing stacks. Track pitch must cover
the vertical extent of points and required text, not only bars; close the definition of
`markExtent` in the current formula.

## Review-scope limits

Stable promotion of all Core, DateTime/DST, capacity, Federation, and similar work is
out of scope. Do not infer from an old STATUS file that they are unimplemented. These
findings are limited to G1–G4 and connected paths. The remediation order and acceptance
conditions are in the [remediation plan](../planning/g1-g4-integration-remediation-2026-09-20.md).
