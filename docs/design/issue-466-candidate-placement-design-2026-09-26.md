# Design — Data-Declared Annotation Candidates (#466)

**Plan:** [candidate design plan](../planning/active/issue-466-candidate-model-design-plan-2026-09-26.md). **Prerequisite:** [accepted shared obstacles](../reviews/current/issue-466-shared-obstacle-prerequisite-acceptance-review-2026-09-26.md). **Supersedes:** the provisional candidate and balloon sections of the [general placement design](issue-466-general-placement-design-2026-09-26.md), but not its obstacle phase or connector-topology corrections.

## Use cases and ownership

The same View contract must express (a) a rail callout, (b) an adjacent callout, (c) an in-plot balloon without an annotation rail, and (d) plot-first/rail-second fallback. HALCYON-1 programme-board's three notes are Project semantic annotations, currently copied into a `notes` slot; a View must select them by stable Project annotation ID instead of duplicating their text. The source note remains a Project fact. View chooses presentation purpose, facet, endpoint and ordered placement candidates. Theme chooses appearance. Layout measures text and owns the complete box/tail/leader geometry and decision. Scene projects; adapters serialize.

## View resource and source identity

`chrona/view/v0.23` is the new candidate-authoring contract. v0.22 remains a separately validated legacy input and normalizes to the same typed candidate model. v0.23 annotations have stable View-local `id`, `purpose`, exactly one of `text` or `projectAnnotation`, an anchor and a non-empty `candidates` array. A Project reference is `{projectAnnotation: <stable-id>}`; it resolves to a selected Project annotation with a non-empty text and an object anchor. The View anchor for this form supplies `facet` and `endpoint`, with optional `rowId`/`itemId`; object identity is inherited, never restated. A View-local text annotation uses the existing full `{kind: object, id, facet, endpoint}` anchor. A missing Project ID, unsupported Project anchor, missing selected object or duplicated View annotation ID is a stable ingress error, not a skipped note or guessed target. A reference inherits text only; Project `kind` does not choose a View `purpose` or placement. `sourceRef` of a placed presentation annotation is its View annotation ID, while a typed `projectAnnotationRef` carries provenance through Layout/Scene. Deleting the View annotation does not mutate Project data.

Project notes not selected for a View annotation remain in the notes source/slot. A selected Project annotation is consumed once, not additionally copied into the notes slot. This is a presentation projection rule, not mutation of the Project. A View with plot candidates needs no `annotations` or `notes` slot if no unselected notes are to be shown. A candidate that names a missing slot is an invalid resource/context combination before placement. An absent optional slot cannot silently become the plot.

Example (new resource version):

```yaml
version: chrona/view/v0.23
kind: view
id: halcyon-02-programme-board
body:
  # The ordinary surface, selection, rows, comparison, visibility and axis fields remain.
  annotations:
    - id: window-balloon
      purpose: note
      projectAnnotation: window
      anchor: {facet: planned, endpoint: at}
      candidates:
        - id: plot-near
          region: {kind: plot}
          search: {kind: nearest-free, maxPositions: 256, maxInlineEm: 18}
          obstacles: {classes: [mark, text, label-visual, dependency-route, leader-route, annotation-box, port, rule]}
          connector: {kind: tail}
```

The grammar has no free coordinate, renderer-specific path or implicit resource lookup. Candidate IDs are unique per annotation and stable in diagnostics. `region` is one of `plot`, `content`, `slot` with a declared source name, or `intersection` of two named regions. Layout resolves each to a finite rectangle after slot allocation. `search` is `row-aligned`, `adjacent` (one logical side) or `nearest-free`; `maxPositions` is an integer 1–1024, and `maxInlineEm` is a positive finite text width bound for plot/content searches. `obstacles.classes` is a nonempty closed set of index classes. Plot/content search cannot omit mark, text, label-visual, dependency-route, leader-route, annotation-box, port or rule: a declaration that does so is invalid, not a weakened safety mode. Legacy rungs normalize to the same four-field data contract with the shared obstacle policy already accepted in O2. `connector.kind` is `none`, `leader` or `tail`; `tail` requires a balloon-capable Theme role and is never silently painted as a line.

v0.22 `rail`, `above`, `below`, `start` and `end` expand to named candidates with the exact current region, search, obstacle and connector behavior. `suppress` remains a terminal outcome, not a fake candidate. The old `callout.placement` preference is inserted first exactly as today. This normalization-only implementation must leave every committed materializer byte-identical to the accepted O2 baseline. v0.23 does not carry the old side/ladder spelling: authoring a new candidate list is an intentional migration, not a parallel hidden policy. New v0.23 View resources may coexist with v0.22 resources in a render context only under their own schema versions.

## Finite joint search and fallback

Layout evaluates candidates in declared array order and commits a box and connector atomically to its single `SurfaceObstacleIndex`. Each search yields normalized-coordinate boxes. `nearest-free` starts at the nearest in-region centre to the anchor, then uses a finite lattice whose block and inline step are each half the measured box dimension (at least one geometry unit); ties sort by Manhattan anchor distance, block distance, inline distance, block coordinate, inline coordinate and candidate index. Only the first `maxPositions` positions are examined. The box must be completely inside its region and avoid the candidate's mandatory obstacles with their registered stroke widths and clearances. A plot box and its connector must remain on the anchor's side of an as-of rule when that rule spans the plot; mere non-intersection of the box is not sufficient. The direct tail or routed leader must avoid all hard obstacles except its explicitly named endpoint mark port and its own box. This is one box-plus-connector trial; no accepted box can later be left with an unrouteable connector.

The decision records `candidateId`, outcome, `searchCount` (the number of jointly evaluated box/connector trials, including rejected trials), bounded search limit and the IDs blocking a preferred position. Candidate IDs and counts are reproducible under the declared font identity, Layout metrics and coordinate normalization. A successful second or later candidate emits `W_LAYOUT_ANNOTATION_CANDIDATE_FALLBACK:<annotation-id>:<candidate-id>`; ordinary first-choice fit emits no warning. Explicit suppression remains possible. Otherwise the first declared candidate receives the existing visible-overflow completion and warning; it is not reported as a collision-free fit. A missing source/slot is an ingress error, unlike dense geometry, which follows fallback.

HALCYON 02 must prove three selected Project notes can use plot/nearest-free/tail with no rail slot, and a deliberately crowded copy must prove plot-first/rail-second fallback. These are public, rendered SVG/PNG assertions in addition to Scene geometry checks; the as-of side and every mark, label and dependency stroke are checked with exact obstacles.

## Balloon and Theme

`chrona/theme/v0.12` adds an optional typed `annotationContainer` token binding for annotation box roles. Its finite value declares `outline: rectangle|balloon`, corner radius and tail base width in em. The balloon is one closed, renderer-neutral Layout-owned Path: a box outline with a triangular tail integrated at the nearest eligible edge and tip at the named anchor port. The filled tail interior and its two outline edges are collision-tested as part of the candidate before commitment. Theme supplies fill/stroke via existing semantic paint roles; it does not place or route. A `tail` candidate requires `outline: balloon`, while a leader candidate may use the ordinary rectangular treatment. The Scene primitive retains the annotation purpose, role, source/provenance and paint order; SVG and typeset paths serialize the same completed commands, and PNG derives from SVG. Adapters do not invent a tail.

Themes without an `annotationContainer` binding preserve their current rectangular box and leader bytes for v0.22 resources. No implicit balloon treatment is introduced into old Themes or old View resources. New Theme token use is additive but versioned; a v0.12 Theme that declares a balloon must provide a valid role binding and finite values. Contrast, font identity and primitive-delivery evidence must be regenerated with changed public output.

## Architecture and migration consequences

The Project annotation is the source narrative; View reference and placement are presentation intent. Normalization resolves references before Layout; Layout does not receive a Project dictionary and does not infer text. The Theme binding is selected before geometry, because its tail width and outline affect collision. Layout returns completed Path/Text/decision placements. Scene and adapters have no candidate search, font measurement or obstacle queries. The one obstacle index and O2 route-priority order remain authoritative, including #467's prospective packed rows. No new annotation policy is allowed to perturb existing v0.22 bytes in the normalization slice. Public HALCYON 02 resource and Layout migration are deliberately atomic so that every published context remains materializable. There is no compatibility shim that turns a v0.23 plot candidate into an old side rung.

The design is accepted only with a [whole-architecture review](../reviews/current/issue-466-candidate-placement-architecture-review-2026-09-26.md), normative updates to Specifications 06/07/08/33/44, versioned schema contracts and the subsequent [implementation plan](../planning/active/issue-466-candidate-placement-implementation-plan-2026-09-26.md). If actual HALCYON geometry exposes a contradiction in the fixed tail or search contract, publish a design correction and review before changing code.
