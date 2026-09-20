# I3 / V1 Acceptance Review

**Conclusion:** Accepted and complete after foreground/background contrast correction
and renewed review of every raster.

**Evidence target:** manifest design
`666007acac8602350db5cbb633c017b35a0d7d2b`; implementation
`b32b1237ee60a0da892372acc150009dc69c91b0`; contrast design
`7840ce833684d304912917929ac36fd7a5074cc7`; corrected implementation
`45fda25b380b8333aadadd5706c2ba6364758d3a`.

The final V1 review finds no open design or implementation decision. All settings-backed
table/timeline, review, and minimal routes serialize a completed `SceneSurface`.
The legacy renderer remains explicitly separate. The manifest is derived inspection
evidence and neither duplicates nor overrides Project, View, Schedule, or Actual.

## Acceptance evidence

| Requirement | Specification / schema | Implementation | Executable evidence | Output evidence |
|---|---|---|---|---|
| G1 Date axis, clipping, ISO boundary, and shared slots | Specifications 08 §4 and 30 §§6–7; `presentation-settings-v0.2.schema.json` | `presentation_axis.py`; `presentation_scene.py` | `test_presentation_axis.py`; `test_scene_joins_axis_ticks_and_marks_without_svg_geometry` | ASTER 01–05 SVG |
| Planned/Actual/baseline, point, and missing Actual | Specifications 09 and 30 §6 | `presentation_marks.py`; common comparison primitives | `test_presentation_marks.py`; `test_surface_primitives_never_fabricate_missing_actual`; `test_point_connector_terminates_at_diamond_and_respects_start_endpoint` | Controller Z and ASTER SVG |
| Bound font assets, Bold, letter spacing, Japanese, long text, finite candidates | Specifications 08 §7 and 30 §7.5; presentation settings schema | `font_metrics.py`; Scene-owned `TextLayout`; `presentation_labels.py` | `test_font_metrics.py`; `test_japanese_item_text_is_measured_once_and_long_unbreakable_text_diagnoses`; `test_presentation_labels.py` | ASTER 01–05 PNG/SVG |
| Callout, note, highlight, explanatory arrow, ports, and leaders | Specifications 09 and 30 §7.5; View schema | `presentation_annotations.py`; Scene primitive and routing projection | `test_presentation_annotations.py`; `test_explicit_facet_annotation_emits_common_box_and_leader`; review/table family test | ASTER routed connectors and annotation fixtures |
| Stable lanes, group order, row-aligned and independent track geometry | Specifications 08 §4.3 and 30 §7.5; shared-foundation schema | `presentation_lanes.py`; Scene row/group/track geometry | `test_independent_lane_tracks_preserve_view_group_order_and_stack_geometry`; `test_independent_lane_tracks_change_svg_bar_offsets` | Settings-mutation SVG checks |
| Table, review, and minimal share completed primitives and preserve setting changes | Specification 08 §5.3 and I3 plan | `presentation_scene.py`; `presentation_svg.py`; public entry adapters | `test_every_public_surface_owns_completed_core_primitives`; review/table/minimal I3-F tests; `test_v2_theme_mutation_changes_gantt_output` | Controller Z; ASTER 01–05 |
| Stable identity and multiple surface instances | Specification 08 §3.3 and §5.1 | `sceneId`, `projectionInstanceId`, `surfaceId` finalization | `test_scene_materializes_stable_primitives_without_adapter_identity`; `test_resolved_table_adapter_serializes_scene_ids_for_every_geometry_family` | SVG `data-scene-id` / `data-source-ref` |
| Closed Scene manifest and adapter-visible scale evidence | Specification 08 §§3.4/4.2; derived Scene-input fixture | `SceneManifest`; `SurfaceScaleManifest`; SVG metadata serializer | manifest closure, preservation, and missing-evidence tests in `test_presentation_scene.py` | Domain/range/origin/unit-ratio metadata in all regenerated SVGs |
| Determinism, input immutability, validators, and image review | Specifications 08/30/31 and conformance fixtures | deterministic builder/serializer and verification scripts | 179 tests; `run_conformance.py`; `verify_presentation_v2.py`; ASTER reproduction test | Five ASTER PNGs plus overview/master visual inspection; Controller Z SVG verification |

## Artifact identities

The corrected and visually reviewed raster SHA-256 identities are:

| Artifact | SHA-256 |
|---|---|
| `01-overview.png` | `12cad74d3edd6752b8b3c8a48bde726c57d08d33de720cfd3188aafdee2d3121` |
| `02-platform-firmware.png` | `8a45688a205a68982229cd1a3c72052dff1a948f240211c268f96ff340d3d921` |
| `03-performance-security.png` | `a7190ca76b416f1b557b40afd7cec5da6ba0cab2ba6ba7ceb8568906a9266828` |
| `04-qualification-production.png` | `d64f8954fcaa2dc5c01d5493458b6adb8eaec6ac1f5e9620b844ae112cbeca5f` |
| `05-master.png` | `cb6445d1b74b195ab422c5d023dbfe52923f7b8738e282d85b65c313f49d224e` |

The regenerated SVG identities at the implementation target are:

| Artifact | SHA-256 |
|---|---|
| `01-overview.svg` | `ca6b38198e057a7c3a15e80ba106bd5177959dd7f3e3a4a6ee44935a2b4aec83` |
| `02-platform-firmware.svg` | `acdb1557fdcb0af3ba08db63a20af672f21cdbba1039b108ebd4b5831532bc87` |
| `03-performance-security.svg` | `25e0824d4becc55bcd567342a6663699eed5183853edbfcea0e885d07d20ca33` |
| `04-qualification-production.svg` | `2292c9bee1d49c280c6979916a21865e514980c5fa110e14a76c0501c39fa611` |
| `05-master.svg` | `535f440f700f332ceceecd80d27b51a2486a8e14be627a702c6521c4cd6300cf` |
| `controller-z-executive-v2.svg` | `74a547399e2eaca325ff3e8ecffd39a3c8900bde3164ac68832440cf65850e2e` |

## Final gate result

- `python -m pytest -q`: 179 passed; two existing `RefResolver` deprecation warnings.
- `PYTHONPATH=src python conformance/run_conformance.py`: PASS for all suites.
- `python scripts/verify_presentation_v2.py`: deterministic Controller Z SVG and raster verification completed.
- ASTER reproduction: all five views reproduce exactly, preserve source inputs, and retain expected item/dependency/Actual counts.

No sample-name branch, renderer-side geometry fallback, unrecorded design exception,
or remaining I3/V1 work was found. G1–G4 corrective completion may be restored.

## Post-acceptance finding: invisible required labels

Manual inspection after publication found that ASTER axis-label Text and its axis-band
Rect both serialized with the same resolved axis color. Table-column-label Text had the
same defect against its table-header band. The strings, bounds, and Scene identities
were present, so structural and reproduction tests passed while the labels were
visually absent. The previous image review therefore did not satisfy V1.

V1 is reopened only for the paint-mapping correction defined in Specifications 08/30,
sample-independent contrast tests, regeneration of affected outputs, and complete
raster review. The geometry, manifest, and adapter ownership conclusions remain valid.

## Renewed contrast review

The correction preserves Scene geometry and typography while resolving foreground Text
with the text paint. Structural tests now compare the serialized `fill` of axis-label
Text against axis-band Rect and table-column-label Text against table-header-band Rect;
both must differ. The five ASTER rasters show every month and the left column heading.
All five were inspected at original resolution, including the 1600×2100 master.
Controller Z likewise shows all five months and `Workstream`. No clipping, overlap,
route, mark, or layout regression was found. The reopening is closed.
