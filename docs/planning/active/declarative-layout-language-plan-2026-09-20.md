# Declarative Layout Language Plan — 2026-09-20

**Status:** L24-D1–L24-D3 complete; implementation planning authorized.
**Milestone:** M24 — Intent-oriented layout authoring
**Purpose:** Replace number-heavy presentation authoring with a reusable, deterministic
layout language while preserving the existing semantic and rendering authorities.

## 1. Product outcome

A human or AI author can express common document and visualization layouts through
composition, intrinsic sizing, alignment, distribution, and bounded relative placement.
The author does not calculate coordinates and normally does not enter raw distances.
Explicit numeric values remain an escape hatch, not the primary authoring experience.

The design combines four proven ideas without adopting any implementation wholesale:

- Vega-Lite-style composition and repetition;
- CSS Grid/Flex-style tracks, intrinsic sizing, alignment, and distribution;
- a closed subset of ConstraintLayout-style anchors, guides, and barriers;
- Chrona's existing measured text, deterministic diagnostics, and source-linked Scene.

Primary references are the Vega-Lite composition documentation, W3C CSS Grid and Box
Alignment specifications, Android ConstraintLayout documentation, and the Cassowary
paper. They are research inputs, not normative dependencies.

## 2. Non-negotiable boundaries

1. View continues to own fact selection, grouping, ordering, and logical annotation
   anchors. Layout cannot introduce or suppress facts.
2. Theme continues to own concrete visual tokens. Layout may reference reusable spacing
   tokens but may not duplicate colors or typography.
3. Scene continues to own resolved coordinates. Authoring resources never persist
   authoritative coordinates.
4. There are no external users to preserve. The prototype `layout-profile/v0.1` and
   number-heavy layout portion of `presentation-settings/v0.2` are replacement inputs,
   not compatibility contracts. The final design has one composition authority and no
   parallel legacy path.
5. The runtime is deterministic for identical resources, metrics, sources, and viewport.
6. Scripts, arbitrary expressions, renderer fragments, and unrestricted linear
   constraints are excluded.
7. Required content never disappears to satisfy a layout preference. Unsatisfied,
   cyclic, ambiguous, or overflowing constraints diagnose with stable IDs.

## 3. Required authoring capabilities

The design phase MUST close all of the following before implementation begins:

| Area | Required vocabulary |
|---|---|
| Composition | `row`, `column`, `grid`, `overlay`, `flow`; bounded `repeat`/`facet` design decision |
| Sizing | `content`, `fill`, `fr`, `min-content`, `max-content`, `fit-content`, `minmax`, aspect ratio |
| Alignment | logical `start`, `center`, `end`, `stretch`, `baseline` on inline and block axes |
| Distribution | `start`, `center`, `end`, `space-between`, `space-around`, `space-evenly` |
| Relative placement | parent/sibling anchors, named guides, content-derived barriers, optional bias |
| Spacing | named spacing-token references; explicit numbers only where the schema permits them |
| Safety | safe overflow, finite fallback candidates, cycle/over-constraint/unknown-reference diagnostics |
| Reuse | immutable imports, named templates, stable-ID overrides, no whole-array replacement for one edit |
| Output | resolved layout manifest with provenance, measured inputs, bounds, and diagnostics |

Physical aliases such as `left` and `right` may be accepted only at migration edges.
The normative language uses `inline-start`, `inline-end`, `block-start`, and `block-end`
so writing direction is not silently encoded into reusable profiles.

## 4. Design phase and publication gates

### L24-D1 — Research and use-case closure

- Record the comparison with Vega-Lite, CSS Grid/Flex/Box Alignment,
  ConstraintLayout, Flutter, Graphviz, and Cassowary.
- Define representative author tasks: centered title, table/timeline split, intrinsic
  legend, baseline-aligned labels, sibling-relative note, barrier after variable labels,
  responsive flow, and reused organization spacing.
- Classify each task as container, intrinsic-size, alignment, relative-placement, or
  out-of-scope behavior.

**Exit:** research and use cases are published; no proposed field lacks a user task.

### L24-D2 — Authority, grammar, and resolution design

- Specify the successor resource, reusable token/template resources, imports, stable-ID
  overrides, and the boundary with resolved Presentation Settings.
- Specify measurement, track sizing, placement passes, tie breaking, precision, and
  writing-mode behavior.
- Specify anchor/guide/barrier reference rules and prohibit arbitrary equations.
- Specify stable diagnostics and the resolved Layout Manifest.

**Exit:** normative specification, ADR, schemas, examples, and semantic negatives agree.

### L24-D3 — Replacement and whole-design review

- Define removal/replacement of prototype Layout Profile and duplicated layout settings,
  CLI/resource-closure integration, package ownership, and rollback behavior.
- Delete superseded schemas, runtime branches, fixtures, and tests rather than retaining
  adapters or aliases that would weaken the final model.
- Audit View/Style/Theme/Layout/Scene/Output authority and reusable-file boundaries.
- Review determinism, accessibility, overflow, internationalization, and renderer
  independence.

**Exit:** a design review explicitly authorizes implementation and records no open
product or semantic decision.

The three design gates are committed and published before L24 implementation planning
starts. The `L24-` prefix prevents collision with the historical M22 D24 gate. If an
implementation question exposes missing semantics, implementation stops, the owning
design artifact is amended and reviewed, and that amendment is published first.

## 5. Implementation-planning gate

Only after L24-D3 passes, create a separate implementation plan that maps every normative
rule to modules, schemas, fixtures, tests, examples, migration, and documentation. It
must define small independently publishable slices and their rollback boundaries. No
implementation code may be included in the design commits.

## 6. Expected implementation slices

The implementation plan may refine names but must preserve this dependency order:

1. replacement schemas, value objects, canonical hashing, and semantic validation;
2. token/import/template resolution and stable-ID override merge;
3. intrinsic measurement and container/track solver;
4. two-axis alignment, distribution, baseline, and safe overflow;
5. bounded anchors, guides, barriers, cycle detection, and diagnostics;
6. Layout Manifest, presentation/CLI integration, obsolete-path removal, and examples;
7. inherited conformance, property tests, visual acceptance, reuse review, and release.

## 7. Acceptance criteria

M24 is complete only when all of the following are true:

- the standard review page can be authored without absolute coordinates;
- centered and edge-aligned content changes position when its measured size or container
  changes, with no author recalculation;
- a barrier follows the widest referenced label deterministically;
- normal examples use named spacing tokens instead of raw layout distances;
- one stable-ID override does not require replacing sibling arrays;
- cycles, unknown references, required overflow, and contradictory constraints fail with
  stable diagnostics;
- repeated resolution produces byte-identical canonical manifests;
- tests for retained product semantics remain green; tests that assert superseded layout
  contracts are replaced by new-contract evidence rather than preserved;
- human and AI-authored resources traverse the same validation and solver path;
- the final review finds no Project/View/Theme/Scene authority duplication.

## 8. Explicit exclusions

- arbitrary algebraic constraints or user-selected solver strengths;
- freeform absolute positioning as authoritative state;
- executable expressions, callbacks, SVG, CSS, or renderer-specific fragments;
- semantic data selection through layout rules;
- silent clipping or automatic removal of required content;
- responsive behavior dependent on host state not declared in Render Context.
- compatibility shims, legacy aliases, or dual layout authorities retained only to keep
  unreleased prototype inputs working.
