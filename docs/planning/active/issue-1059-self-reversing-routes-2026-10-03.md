# Issue #1059: relation routes never reverse over their own line (work record)

Plain bug fix confined to Layout relation routing plus one Scene check; steps 1 to 4 of the sequence are combined here and the failing test came first. Regression of the #1030 side entry. Acceptance review follows the merge.

## 1. Baseline (read on `d4b081cf`)

- The side-entry stub candidate (#1030) exposes a tip `start - stub` (11 px) left of the target's start and runs the final leg tip to start. The route search ends at the tip and does not know which side it arrives from, so a source that drops less than one stub before the start overshoots to the tip and turns back over the same line.
- Committed Scenes: 58 of 564 relation paths self-reverse (27 controller-z, 2 controller-z-ja, 13 HALCYON-1 slides, four on target B). Reproduced synthetically only with a gate source (its bottom-tip port lets the search pick the reversal); bar sources already jog.

## 2. Literal acceptance (copied from #1059)

1. A general route invariant enforced in Layout and tested: no emitted relation path has three consecutive collinear points with opposite directions; more generally no segment overlaps a previous segment of the same path.
2. Synthetic fixtures: a source dropping inside the stub distance and the mirrored `end` case; a gate source and a bar source; a case where (a) fits; a case where only the fallback (c) fits under `maxBends`. Each asserts the invariant and a horizontal mid-height entry whenever a non-reversing route exists.
3. A Scene-derived corpus gate counts self-reversing relation paths and must be 0 after regeneration.
4. Target B regenerated: `pdr-structure`, `optics-detector`, `delivery-integration`, `psr-shipment` show no tail behind the arrowhead.

## 3. Design

- **Invariant** (`routing.py`): `route_self_overlaps` (any two segments overlapping along a line, adjacent reversal included). `relation_route_quality` rejects an overlapping route and `select_lane_relation_route` records the attempt as `no-route-found` with the new `E_LAYOUT_ROUTE_SELF_OVERLAP`; the next candidate then applies, which is the unchanged order, i.e. fallback (c).
- **Repair (a)** (`repair_self_reversal`, called in the lane selector and in `compose_surface_routes` before the quality check): a reversing L (drop, tip on the near side, back) becomes drop part of the way, jog sideways to the tip's coordinate, drop to the tip, enter. The jog level is tried from the target side (8 px before the entry line) back toward where the drop began in 4 px steps; both new segments must be free of mark, text and label obstacles, the endpoints' own marks excepted. No repair, no emission: the invariant rejects the route.
- **Scene gate** (`scene/perceptibility.py`): typed error `E_SCENE_RELATION_PATH_REVERSES` (and `W_SCENE_...` sentence) counts relation `Path` primitives with a self-overlap; it runs in the existing `scene-perceptibility` conformance check over every manifest Scene, like `E_SCENE_RELATION_PATH_DUPLICATE`.
- **Layers.** Layout owns routes, Scene only observes; no schema, View, Theme or Project change; no corpus datum edited. Only paths that reversed change (58 of 564).

## 4. Implementation plan (one slice)

Files: `routing.py`, `surface_routes.py`, `perceptibility.py`, `diagnostic_messages.py`. Tests: `test_relation_route_invariant.py` (gate source across windows, bar source, mirrored end, honest extra bend and the `maxBends` fallback), `test_perceptibility.py` (gate, adjacent reversal, later overlap, swatch exclusion). Generated outputs: derived-sync after merge. Mutation checks run: repair disabled (7 tests fail); repair and invariant disabled (7 fail).

## 5. Evidence

Before/after over all 54 slides (committed vs regenerated): self-reversing paths 58 to 0; exactly those 58 paths changed, on 43 slides; paths ending horizontally 335 to 330; total bends 964 to 1073 (each repaired path gains its jog). Images read: the four target-B relations at 4x (pdr-structure, delivery-integration and psr-shipment now jog and enter horizontally; optics-detector enters vertically on the bar corner, the fallback, without a tail) and before/after tiles of the changed relations of controller-z annotations (one per identical-change group of 28), controller-z-ja executive, programme board, image notes, editorial lanes, tvac-slip, mission brief and overlay briefing. Not read image by image: the other halcyon gallery variants and controller-z slides of those groups (measured).

Open: five relations that ended horizontally before now end vertically (the repair finds no free jog); #1060 (`entry: side`, back-route through the row gap) is the follow-up for abutting chains.
