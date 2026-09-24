# Implementation Plan: Published Inspection Scene (#385)

**Status:** Proposed

**Implements:** [Published Inspection Scene design](../../design/issue-385-published-scene-design-2026-09-25.md)

## I385-0 — Complete Scene closure and typed table structure

Replace the unused `PresentationScene` aggregate with the runtime-produced
`InspectionScene`; add `SceneColumn` plus typed primitive table references;
and build the document manifest from completed runtime values.  Route every
variance and scale-legend role through `semantic_registry`; there must be no
Scene-builder role literal after this slice.  Replace public raster payload
serialization with its existing immutable asset identity and enforce the
corresponding primitive invariants.

**Files:** `presentation/scene/model.py`, `scene/v05_builder.py`,
`model/semantic_registry.py`, `usecases/render_review.py`, focused
Scene/semantic/render tests.

**Acceptance:** the render use case returns an `InspectionScene` whose only
surface is the existing completed surface; columns/cells are typed; manifest
counts and sorted capabilities derive from completed data; raster paths never
cross the boundary; and no v05 builder source spells `variance-ahead`,
`variance-behind`, or `planned` as a Scene role literal.

**Publication:** focused tests and structural source assertions in one
implementation commit.  No public artifact is changed in this slice.

## I385-1 — Schema, explicit serializer, and CLI emission

Add the live `scene-v0.1` schema and schema-inventory entry.  Implement an
explicit serializer/deserializer-validation seam that maps every typed public
field and rejects unknown/non-finite/malformed/invalid-reference data.  Add
`--emit-scene PATH` to `render` and `render-review`, preserving the required
target `--output` and non-overwriting write semantics.

**Files:** `schemas/scene-v0.1.schema.yaml`, schema inventory/resource
loading support, `presentation/scene/serialization.py`, `app/cli.py`,
`usecases/render_review.py`, CLI/schema/serializer tests, generated schema
inventory if required by current quality tooling.

**Acceptance:** draft and immutable commands emit byte-deterministic,
schema-valid JSON; a target artifact is byte-identical with or without scene
emission; malformed scene projections are rejected before write; duplicate
output, invalid path, and render failure leave no Scene artifact; and no
serializer imports Layout placement, Theme normalization, or renderer code.

**Publication:** schema and implementation in one atomic commit, with focused
tests and a representative emitted-scene diff review.

## I385-2 — Public inspection evidence and external-consumer proof

Emit checked-in inspection Scenes for representative declared corpus slides
through the public command path.  Add a deliberately out-of-tree,
stdlib-only fixture adapter under `tools/` that consumes Scene JSON alone,
declares static supported capabilities, validates the subset rule, and emits a
small SVG projection without importing `src/chrona`.  The fixture proves that
typed table/scale/provenance data is sufficient to consume the published
boundary; it is not a second renderer or a package runtime.

**Files:** declared generated Scene evidence beside selected corpus artifacts,
`tools/scene_adapter_fixture.py`, integration tests, manifest/evidence docs
where existing corpus policy requires registration.

**Acceptance:** an immutable corpus Scene is reproduced through the public
emission command; the external adapter imports only standard-library JSON/XML
facilities, reads no Project/View/Theme/Layout files, emits a deterministic
artifact, and fails with `E_SCENE_CAPABILITY_UNSUPPORTED` for a missing
capability.  The emitted manifest provides exact content-family and
visual-role counts for #375 without SVG parsing.

**Publication:** generated Scene and external-fixture evidence in one commit;
review its diff separately from generated SVG evidence.

## I385-3 — Release and acceptance gate

Run focused Scene/schema/CLI/adapter tests, full pytest, conformance,
vocabulary/diagnostic/reachability/import-direction checks, public materializer
byte checks, generated SVG and Scene diff review, and installed-wheel smoke.
Verify Ubuntu, macOS, and Windows CI.  Publish an English acceptance review
that checks the ownership, stability, table, asset, and external-consumer
claims against implementation evidence.  Close #385 only after CI succeeds.

## Deliberate boundaries

* #375 owns the presentation-coverage report and consumes I385-2 Scene
  evidence; this plan does not duplicate that report.
* #383 may later replace the fixture with an editorial external adapter; it
  is not an implementation prerequisite for Scene publication.
* #142 may return a Scene after its own agent-interface design; this plan adds
  no MCP service.
* No compatibility reader for historical `PresentationScene` is retained.
