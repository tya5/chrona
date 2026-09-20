# I3 / V1 Acceptance Review

**Conclusion:** Reopened. The original acceptance conclusion is withdrawn pending the
foreground/background contrast correction and renewed raster review.

**Evidence target:** manifest design
`666007acac8602350db5cbb633c017b35a0d7d2b`; implementation
`b32b1237ee60a0da892372acc150009dc69c91b0`.

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

The checked-in raster images were not changed by the manifest-only metadata addition.
Their accepted SHA-256 identities are:

| Artifact | SHA-256 |
|---|---|
| `01-overview.png` | `1d831086c928ba4cf2e1a32765f373ced5aa9265920574709086ccd35ffa827c` |
| `02-platform-firmware.png` | `93000de781bfb8448115b2afe63a629449e9069f68010db61094b26b3469c584` |
| `03-performance-security.png` | `94cc02eda0ac233b05bf750c8f31e31a3642166b4a561d4d3bd50e510599f51b` |
| `04-qualification-production.png` | `08a2f5695373c2f49e3d5e713b3d2f600aa748ba8ab6930f331884d4e5a7a768` |
| `05-master.png` | `ae4cb3b0703c8e9781fa31bd7866f8bb5fbe9203a511057b549cbcf62972b4a7` |

The regenerated SVG identities at the implementation target are:

| Artifact | SHA-256 |
|---|---|
| `01-overview.svg` | `126b64dbc6ae609d58f33dcb6224bee969d2e12afea5ce06bbcbecbf58636c02` |
| `02-platform-firmware.svg` | `14b3b839bdb7078c8e9187b1afae7fdef48332333a7ab30ec5f847c96deaa551` |
| `03-performance-security.svg` | `6fc794a27d35a83e751782c635f516d6087d0a15be8c6d951bd7f4094ee9dfaa` |
| `04-qualification-production.svg` | `d02c9e8d8263de7641281d2cceadd0f8988aa7c6a8f1a9d1d67b2f0f229815f0` |
| `05-master.svg` | `e12934c55bc5c070d6de7c491b7edfb0ea7b94c8ffbb71eca25ef653f78a0645` |
| `controller-z-executive-v2.svg` | `d5749fe7971ab85db86468e35320546181a55d5956b22bc9e5bacdb0e36ca03b` |

## Final gate result

- `python -m pytest -q`: 179 passed; two existing `RefResolver` deprecation warnings.
- `PYTHONPATH=src python timeline-design/docs/fixtures/run_conformance.py`: PASS for all suites.
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
