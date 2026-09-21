# Gantt Comparison Surface Quality — Design Plan

**Status:** Active design plan. No implementation or HALCYON YAML correction is authorized by this document.

**Issue:** #58  
**Trigger:** Visual inspection of the generated HALCYON-1 SVGs after final reproducibility gate #57.

## 1. Decision and product boundary

Chrona produces a self-contained Gantt SVG/PNG. It does not integrate with PowerPoint and does not encode slide-specific output. A generated review chart must remain readable without hand edits.

The path remains:

`Project → View → Style → Theme → Layout → renderer-neutral Scene → SVG/PNG`

Project scheduling semantics and YAML resource ownership are unchanged.

## 2. Evidence-based triage

| Symptom | Immediate source | Classification | Required disposition |
| --- | --- | --- | --- |
| Table values overlap in Mission brief and Launch campaign | Four/five content-heavy columns in the selected Views; Layout scales every measured column to fit and Scene emits unwrapped text | **Core defect**, with YAML pressure fixture | Replace shrink-only placement with a declared feasible-or-diagnose table policy; then tune examples only through valid resource choices |
| Plot labels and variance text collide with marks and each other | Mission/Launch Views explicitly request `labels.placement: plot`; Scene additionally emits a variance primitive | **Both**: YAML requests density; Core lacks collision/duplication policy | Design selectable label policy, collision treatment, and one authoritative delta representation |
| Relations form large rectangles | Mission/Launch Views request `relations: semantic`; router returns a geometrically valid but visually poor path | **Both**: YAML enables relations; Core lacks route-quality acceptance | Define bounded routing lanes, crossing/length scoring, and suppression/diagnostic fallback |
| Group regions have no headings | Programme View groups by owner, but its Theme omits `timeline.groupHeader.blockSize` | **YAML / Theme configuration** | Correct only after the design defines enabled-group header requirements and capacity behavior |
| No legend | all three Layout Profiles omit a `legend` slot | **YAML / Layout configuration** | Add declaratively only where a legend is useful; no renderer branch |

A deterministic SVG and passing byte reproduction are necessary but insufficient: they do not prove visual readability.

## 3. Design deliverables, in order

### D58-1 — use cases and quality contract

Define reader tasks for compact review, programme board, and print view; define non-goals. Establish measurable conditions for table, label, relation, group, and legend readability.

### D58-2 — cross-layer ownership and normative specification

Specify:

- View controls for label and relation intent;
- Theme/Layout metrics for table minima, group-header capacity, relation clearance and density;
- Layout feasibility, allocation, overflow diagnostics and deterministic degradation;
- Scene rules for collision-free text, one delta representation, visible group-header primitives, and route quality;
- renderer obligations limited to serialization.

This document must identify every schema, normalizer, policy binding, fixture, test, materializer, and generated evidence affected.

### D58-3 — schema, diagnostics and fixture design

Define schema changes only if existing declarations cannot express the approved policy. Define stable diagnostics for:

- `E_LAYOUT_TABLE_OVERFLOW`;
- no feasible plot-label placement;
- no acceptable relation route;
- group header requested without required capacity.

Create one non-HALCYON fixture for each policy, plus regression fixtures for the three HALCYON contexts.

### D58-4 — acceptance and visual review design

Acceptance requires:

1. no intersecting table text bounds;
2. no plot-label/mark/text overlap unless the declared policy explicitly permits it;
3. relation routes satisfy the configured quality bound or are omitted with the specified diagnostic;
4. enabled group headers contain visible text;
5. a legend slot emits role-derived swatches and labels;
6. deterministic SVG byte reproduction;
7. a reviewed PNG evidence set at declared viewport sizes.

### D58-5 — design review and implementation plan

Review ownership, Core/Presentation boundary, migration impact, all tracker rows, diagnostics, fixtures and acceptance evidence. Only a completed review may authorize an implementation plan. YAML corrections follow the implementation only when the generated output conforms to the new quality contract.

## 4. Explicit exclusions

- PowerPoint API, bidirectional editing, and export-specific behavior;
- HALCYON-only coordinates, colors, branches or manual SVG edits;
- dashboard/sidebar redesign;
- semantic project changes caused by a presentation repair.

## 5. Completion gate for this plan

D58-1 through D58-5 must be published and reviewed before any source or YAML implementation commit. A newly discovered owner or requirement reopens the relevant design deliverable first.
