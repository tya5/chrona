# Implementation Plan: Presentation evidence and inspection (#390)

**Status:** Accepted.

**Implements:** [#390 evidence design](../../design/issue-390-presentation-evidence-design-2026-09-25.md)

## I390-1 — All-Scene delivery ownership check

Replace the `ScenePrimitive`-only scanner with an AST-backed inventory of every
public `presentation.scene.model` dataclass and field.  Add a finite owner
manifest classifying each field as adapter, inspection, or derived consumer and
requiring a named live consumer for every field.  Add focused positive, stale
manifest, missing-field, and missing-consumer fixtures.

**Acceptance:** no Scene model field escapes inspection; legitimate serialized
inspection evidence is not falsely required in SVG; an unowned new field fails.

## I390-2 — Prior-art matrix and visual-review contract

Add the curated source metadata and generated matrix under
`docs/research/presentation/`, deriving rows from I391's registry.  Validate
row completeness, disposition/reason, source-link shape, and unknown external
facts.  Document the visual acceptance record in corpus/review contribution
policy and add a template/fixture that links generated gallery evidence without
becoming runtime input.

**Acceptance:** every ceiling row has a reviewed Chrona disposition; matrix
generation/check is deterministic; presentation implementation reviews record
the exact generated artifacts assessed by a human.

## I390-3 — Verification and release

Run focused checker/matrix tests, generated-document checks, conformance,
structural gates, full pytest, wheel smoke, and CI.  Publish the acceptance
review and close #390 after all platforms pass.
