# Issue #592 — surface composer split work record

## Published baseline and design plan

Public base: `a7358bcb72ad72a96cc600f09f3e5cb8dcf22981`. [Issue #592](https://github.com/tya5/chrona/issues/592) is open without comments; [board #454](https://github.com/tya5/chrona/issues/454) places it in P0 before parallel #582–#588 work. The issue cites 3,457 lines; `surface_composer.py` has 3,403 lines on this base. Published Spec 33 gives Layout authority over completed geometry, measurement and routing. `tools/check_module_reachability.py` is registered in conformance; new modules must remain reachable. The composer has nested closures sharing placements, metrics, obstacle state, diagnostics and output order. Exact phase read/write sets and public byte baseline remain unverified; no product change is authorized by this plan.

### Literal issue acceptance

- [ ] `surface_composer.py` contains orchestration only, under about 400 lines. Each concern module has a docstring naming what it owns and what it reads.
- [ ] Every public materializer and Scene is byte-identical, and the full test suite passes unchanged.
- [ ] The module reachability gate covers the new modules.
- [ ] Ownership notes are added to spec 33 (Layout ownership), so future issues can name the module they touch.

### Design questions and architecture boundary

1. Map the existing call graph, nested closures, mutation order and read/write sets. Confirm dependency edges among table/columns, axis, group bands/headers, marks, member labels, lanes, annotations, legend and routes; do not turn shared mutable state into a long argument list or duplicate authority.
2. Select typed phase inputs/results for placements, obstacle registrations, diagnostics and stable identity while preserving byte order. Keep `surface_composer.py` as the ordered coordinator; each concern module states what it owns and reads. Verify no import cycle or View/Theme/Scene responsibility leak.
3. Review the module map against all of Spec 33, source architecture, import-direction rules, adjacent lane/annotation/mark designs and #590's generated-evidence workflow. Add concise ownership notes to Spec 33 without making private module paths into new public semantics.
4. Define a complete byte-identity baseline for all manifest-listed public SVG and Scene outputs, plus focused semantic fixtures. A no-behavior-change split has zero intended generated diff; run focused tests at each extraction and full CI at final acceptance. Check module reachability and import direction after each slice.

### Review and publication slices

| Slice | Publishable result | Evidence |
| --- | --- | --- |
| D1 design | Confirm concern dependency map, typed result contract, orchestration order and whole-architecture review in this record; update Spec 33 ownership notes. | Source-grounded call/read/write map and no semantic/schema migration. Publish before implementation planning. |
| P1 implementation plan | Sequence extraction by dependency in independent reviewable slices; name files, type changes, focused tests, byte baselines, and publication units. | Complete 29-materializer SVG/Scene inventory, reachability/import gates, full CI release gate. Publish before product code. |
| I1…In extraction | Move one coherent concern at a time; preserve composer function and public bytes after each publication. | Focused tests, complete byte comparison, module gate, generated diff = none. |
| A1 acceptance | One literal review, exact review-bearing `main` CI, issue closure and archive. | All four criteria verified directly. |

The next step is the implementation plan; #582–#588 do not run in parallel until #592 completes. #590 and #591 remain separate P0 contracts and must not be solved by this structural split.

### D1 — selected design and architecture review

The reviewed public base is `b7dfd726`; `surface_composer.py` remains 3,403 lines, unchanged from the D1 map at `76f3664e`. Preserve `compose_surface_layout(request)`, `SurfaceLayoutComposition`, diagnostics/identities and output bytes. The composer becomes only an ordered coordinator and final assembler. Each phase receives closed request data and prior typed results; `SurfaceObstacleIndex` is the sole intentional mutable phase service, registering each accepted label/route/annotation before the next search.
The source order (1124–3313) stays: validate and close slots/rows/groups/scale/tracks; table, groups, axis and marks; build label intents; seed obstacles from marks, required text and rules; place as-of rule and lane-required labels; route dependencies and relation labels; place optional labels; emit legend, notes, footer and summary in existing source slots; place annotations; resolve remaining visuals; complete slots/overflow/canvas, lane emissions/hosts, patterns and final `SurfacePlacement`. Resolve #466's phase-5 “decoration” as the residual obstacle-independent visual embellishment phase; fixed-slot source content is emitted when its host is composed and fixed host backgrounds when their extents are known. Spec 33 §3 names `legend`, `notes` and `summary` as sources; they do not enter route obstacles, and code emits them after relation labels but before annotations. Preserve that established order and all bytes.
Pre-route labels follow #466's required-text phase and #467's lane correction: preflight-reserved lane labels are required; automatic/explicit labels and deltas remain optional/post-route. As-of rule labels precede routes so label/rule host constraints are shared. Annotation geometry stays later. Spec 33 §8.2's accepted successor topology is not fully implemented at this base; this split neither changes current behavior nor claims the successor is satisfied.

| Existing block (base line range) | Owner / typed boundary result |
|---|---|
| Validation, slots, rows, groups, scale, tracks (1124–1274) | `surface_base` → `SurfaceBaseGeometry` |
| Columns and cells (1275–1355) | `surface_table` → `TablePlacementBatch` |
| Group labels/bands and axis (1356–1745) | `surface_groups`, `surface_backgrounds`, `surface_axis` → typed placement batches |
| Marks, folded points, progress and summary bars (1746–1874) | `surface_marks` → `MarkPlacementBatch` |
| Label intents and placement (1875–2247) | `surface_member_labels` → ordered request/result batches |
| Dependency paths and relation labels (2249–2442) | `surface_routes` → `RoutePlacementBatch` |
| Legend; notes/footer/summary sources (2443–2611) | `surface_legend`, `surface_content` → typed content batches |
| Annotation boxes/text/visuals/connectors (2612–3137) | `surface_annotations` → `AnnotationPlacementBatch` |
| Text/icon visual requests (927–1121; 3138–3164) | `surface_visuals` → visual placement batch |
| Slot ownership, fit/warnings/canvas, lane emission/host, patterns, final value (3165–3313; helpers 87–1121, 3314–3403) | `surface_completion`, `surface_lanes`, `surface_marks`, `surface_geometry` → final `SurfaceLayoutComposition` |

This assigns `_visual_reservation` (501–523) and visual resolution (927–1121) to `surface_visuals`; detail/footer helpers (524–718) to `surface_content`; background helpers (398–474) to `surface_backgrounds` and `_completed_canvas` (475–500) to `surface_completion`; lane helpers (98–397, 814–881, 3291–3298) to `surface_lanes`; mark helpers/role constants (719–771, 882–901, 3331–3361) to `surface_marks`; axis inset (772–785) to `surface_axis`; base content extent (786–813) to `surface_base`; relation-label helpers (902–926) to `surface_routes`; association validation (87–95) to `surface_member_labels`; rectangle/date conversions (3314–3330, 3362–3369) to `surface_geometry`; folded identity (3370–3374) to `surface_marks`; and comparison anchors (3375–3403) to `surface_annotations`. Shared background IDs belong to `surface_backgrounds`; shared geometry tolerance/paint-order constants (385–397) belong to `surface_geometry`. Every helper and composer block has an owner; the coordinator retains no residual concern.
Typed batches carry ordered placement tuples, stable IDs, decisions, warnings, diagnostics and fit/host facts. Only label, route and annotation phases receive the obstacle index. Moving the 2,190-line body and ~1,100 lines of concern helpers leaves validation, phase calls and final assembly; target coordinator budget is 250 lines plus imports/types. Verify actual LOC in the implementation plan without compressing logic or changing order.
Architecture disposition: consistent with Spec 33 §§1, 3, 8–10, 13, source architecture, #466 obstacle/route order and #467 lane correction. Module names are internal ownership guidance, not public import contracts. No schema/resource migration or intended output diff. Before implementation planning, baseline all 29 public materializer Scene/SVG pairs, inspect generated evidence as a batch, and verify reachability and import-direction compliance for each new module.

### I592-2 boundary correction and whole-architecture review

I592-1 exposed two joins that the owner map did not make explicit. Spec 33 §8.3 now assigns base group extents to `surface_base` and group text/presentation to `surface_groups`; `surface_axis` derives calendar intervals, while `surface_backgrounds` alone completes their Theme-treated geometry. Folded marks return a typed group-header extent update; a pure background operation applies it to the existing header band. The coordinator carries ordered results, not a second placement authority or a shared mutable group/shape list. I592-2 may leave the folded-point caller in the composer until I592-3 moves marks, but it must use the final typed/pure boundary when extracting backgrounds. Preserve the current calendar insertion and folded-header replacement order and all bytes.

This remains a private Layout extraction: Spec 33's Layout ownership, #466 obstacle ordering, #467 lane membership, Theme treatment, Scene projection, adapters, schemas and diagnostics are unchanged. There is no migration or compatibility promise. The 29 Scene/SVG pairs stay byte-identical; diagnostic source-location reports are regenerated when code moves. No unresolved design question remains for I592-2.
