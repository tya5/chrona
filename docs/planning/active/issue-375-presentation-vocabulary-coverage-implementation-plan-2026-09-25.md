# Implementation Plan: Presentation vocabulary coverage (#375)

**Status:** Accepted.

**Implements:** [Presentation vocabulary coverage design](../../design/issue-375-presentation-vocabulary-coverage-design-2026-09-25.md)

## I375-0 — Complete the Scene slot-ownership boundary

Add a required placement-owned primitive slot identity and publish
`chrona/scene/v0.2`.  Register v0.2 as live and v0.1 as historical/
transitioning; update the explicit serializer, validator, CLI emission,
materializer, external adapter fixture, and focused tests.  No builder derives
slot ownership from primitive purpose or geometry.

**Files:** Layout placement dataclasses/composer, Scene model/builder/
serializer, `scene-v0.2` schema and inventory, CLI/materializer/adapter tests.

**Acceptance:** every v0.2 primitive names one declared surface slot; invalid
or cross-surface links fail serialization; source-boundary tests show Scene
does no placement inference; current command output bytes are unchanged except
for the explicit Scene artifact version.

## I375-1 — Complete corpus Scene evidence

Add `expectedScene` declarations to every manifest slide and create all v0.2
Scene artifacts exclusively through the public materializer.  Update the
fixture adapter to consume a capability-free v0.2 corpus Scene.

**Files:** five manifests, checked-in generated Scenes, adapter fixture and
integration tests.

**Acceptance:** materializer byte checks all declared SVG and Scene artifacts;
missing Scene evidence is an explicit failure; generated Scene review confirms
only intended v0.2 artifacts changed.

## I375-2 — Build the read-only coverage report

Implement `tools/presentation_coverage.py` with complete manifest/Context
discovery, live-schema finite-vocabulary traversal, v0.2 Scene validation, and
declared/placed/realized slot aggregation.  Generate
`docs/gallery/presentation-coverage.md`; add deterministic `--check` and unit
tests for sorting, missing evidence, schema-version selection, and no-SVG /
no-producer-import boundaries.

**Acceptance:** report is byte deterministic and names the required four
detail-slot sources from real evidence, plus currently uncovered live Layout
overlay vocabulary.

## I375-3 — Publish the gallery seam and release gate

Link the generated presentation report from the gallery index and conduct a
separate generated-artifact review.  Run focused tests, all materializer byte
checks, report `--check`, conformance, full pytest, reachability/import-
direction checks, installed-wheel smoke, and three-platform CI.  Publish an
English acceptance review and close #375 only after CI succeeds.

## Deliberate boundaries

* #382 owns adding an overlay/guides/anchor/barrier corpus set after this
  report identifies the absence.
* The report consumes current Scene artifacts; it does not introduce an SVG
  metadata parser or make coverage a render success condition.
* No reader is retained for scene-v0.1 in the current coverage path.
