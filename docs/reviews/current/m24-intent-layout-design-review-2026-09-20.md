# M24 Intent-Oriented Layout Design Review — 2026-09-20

**Decision:** PASS — design complete; implementation may be planned but has not started.

## 1. Reviewed set

- M24 declarative-layout plan and external-system research;
- Specification 33 and its successor notes in Specifications 27, 29, and 30;
- ADR-0023;
- `layout-profile-v0.2` and `render-context-v0.4` schemas;
- complete, relative/barrier, inherited-override, invalid-offset, and Render Context
  fixtures;
- roadmap, status ledger, schema index, authoring guide, and specification index.

The schemas and positive fixtures pass Draft 2020-12 structural validation. The raw
`offsetX` fixture is rejected. Semantic cycle/token/measurement cases are assigned to
the implementation plan because they require resolved resources, not because their
behavior is undecided.

## 2. Use-case closure

| Use case | Design owner | Closed mechanism |
|---|---|---|
| Center relative to parent | Layout | two-axis `place` |
| Align starts/ends and stretch | Layout | logical-axis alignment |
| Align text baselines | Layout + measured source | first/last baseline with required metrics |
| Split remaining space | Layout | `fr` and `fill` after intrinsic/fixed sizing |
| Fit measured content | Layout + metrics | content/min/max/fit-content sizing |
| Distribute peers | Layout | six closed distribution values |
| Follow sibling edge/center | Layout overlay | bounded node anchor |
| Follow widest content | Layout overlay | content-derived barrier |
| Responsive panel wrapping | Layout | deterministic flow |
| Reuse values | Theme | number-token references |
| Reuse compositions | Layout resource | immutable `extends` plus stable-ID overrides |

No accepted task requires x/y coordinates, an arbitrary expression, or a general
constraint solver.

## 3. Whole-design authority review

| Boundary | Result |
|---|---|
| Project/Schedule/Actual | Unchanged; Layout cannot select or mutate facts. |
| View/Layout | View creates selected/repeated sources; Layout only arranges them. |
| Theme/Layout | Theme owns concrete number values; Layout owns where a token is used. |
| Layout/Scene | Layout Manifest contains resolved geometry; Scene remains the source-linked rendering boundary. |
| Context/Layout | Context declares environment and immutable inputs; Layout cannot inspect host state. |
| Renderer/Layout | Renderer sees Scene only and cannot supply missing placement. |
| Preset/Profile | The bundled Presentation Preset is removed; Context references reusable Theme and Layout separately. |

The review found no duplicate authority in the target design. Keeping the existing
Presentation Settings layout branch would create duplication, so deletion is mandatory,
not optional cleanup.

## 4. Determinism and failure review

- inheritance is single-base, immutable, stable-ID keyed, null-free, and cycle-checked;
- measurement precedes arrangement and is never guessed;
- normal flow precedes overlay guide/barrier/anchor resolution;
- anchor dependencies use topological order with stable IDs for ties;
- safe alignment has a specified start fallback; strict alignment diagnoses;
- required content cannot use optional clipping;
- canonical JSON, decimal context, and one final quantization replace `repr` hashing and
  repeated float rounding;
- every unresolved token, source, measurement, reference, cycle, contradiction,
  baseline, and required overflow has a stable diagnostic.

## 5. Reuse and YAML review

The common organization Theme and base Layout are separate files. A variant names only
stable nodes it changes; it does not repeat the root tree or replace a regions array.
Render Context is generated binding evidence, so authors do not hand-maintain content
hashes during ordinary design. Literal distances remain structurally possible for
deliberate optical/export bounds, but built-in examples and acceptance fixtures must use
Theme tokens for ordinary spacing.

## 6. Replacement review

There are no external users, so the review rejects compatibility adapters. The
implementation must delete:

- the v0.1 Layout Profile schema/runtime/fixtures;
- `surface` and named canvas/density lookup behavior;
- persisted Presentation Settings layout authority and Preset inheritance path;
- insertion-order slot allocation and region-name sizing;
- old tests whose only purpose is preserving those contracts.

Retained product semantics and unrelated tests remain mandatory. The new v0.2 profile
and v0.4 Context become the only reachable authoring/evaluation path in one release
commit; an intermediate dual-authority release is prohibited.

## 7. Implementation authorization

No product decision remains open. Implementation planning may now map the normative
rules to modules and independently verified slices. If implementation reveals a missing
choice, work returns to Specification 33 and this review before affected code resumes.

