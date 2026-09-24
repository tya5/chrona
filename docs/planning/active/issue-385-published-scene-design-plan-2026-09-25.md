# Design Plan: Published Inspection Scene (#385)

**Status:** Proposed

## Objective

Decide how Chrona publishes a complete renderer-neutral inspection Scene as
`scene-v0.1`, without turning a derived layout result into authoring input or
promising geometry stability that Layout does not own.  The resulting contract
must support deterministic inspection, corpus measurement, and a separately
implemented external adapter.

## Public-state inventory

The current runtime constructs and renders `SceneSurface`; `RenderedReview`
returns that surface with its rendered artifact.  The model also declares
`PresentationScene`, `SceneManifest`, and `ContentFamilyCounts`, but no
current render path constructs or serializes that document-level object.
`chrona render` and `chrona render-review` emit only target artifacts.

The current surface already carries completed primitive geometry, text layout,
paint, slots, rows, groups, scale evidence, and icon payloads.  It lacks
typed table columns and typed cell-to-row/column links.  Layout computes table
column positions and widths before emitting cell text, then discards that
structure at the Scene boundary.

Two direct role literals remain in `scene/v05_builder.py`: variance direction
and a scale legend's planned role.  They contradict the semantic registry's
stated ownership before roles become a public vocabulary.  Raster icon bytes
are currently a runtime payload although icon assets already carry immutable
content identities through the closure.

## Questions to resolve in design

1. Define the document root, required/optional fields, canonical ordering,
   numeric/date representation, and JSON Schema validation boundary for
   `chrona/scene/v0.1`.
2. Decide whether the public document is assembled as a new typed projection
   from completed `SceneSurface` or whether the unused document model becomes
   the runtime result.  Do not let serialization duplicate geometry,
   measurement, paint, or adapter policy.
3. Define explicit inspection-only stability: Scene is derived,
   non-authoritative, and geometry is stable only for a pinned Chrona/layout
   version and immutable closure.
4. Define a consumer capability declaration and the diagnostic for a consumer
   that cannot consume a Scene capability.  Reuse the existing visual
   capability vocabulary only where its meaning actually matches; do not make
   a renderer target registry into an external-adapter registry.
5. Close the semantic registry holes by introducing semantic bindings or a
   bounded role-selection helper, rather than moving literals into a different
   Scene branch.
6. Define `SceneColumn` and typed primitive table references.  Preserve stable
   existing internal scene IDs only as opaque identities; consumers must not
   parse them to recover table structure.
7. Decide raster-icon representation.  Compare an inline encoded byte payload
   with an immutable asset reference; assess self-contained inspection,
   closure reproducibility, privacy, artifact size, and third-party adapter
   access.  The design must select one representation and provide its
   validation rule.
8. Specify draft and immutable CLI emission separately, including an explicit
   output path and the rule that scene emission neither changes artifact
   rendering nor becomes public materializer evidence by itself.
9. Specify how #375 consumes serialized Scenes for content-family counts and
   visual-role histograms without reimplementing Scene construction or reading
   SVG metadata.

## Required architecture review

Review the proposed boundary against these ownership rules:

```text
Project / View / Theme / Layout -> completed Scene -> target adapter
                                  -> inspection serializer -> scene-v0.1
```

* Project, View, Theme, and Layout remain the owners of semantic choice,
  appearance, and geometry respectively.
* The serializer may translate completed typed values to the public document;
  it must not measure text, route relations, resolve Theme tokens, or infer
  table structure from identifiers.
* Scene output is never accepted as Project, Context, View, Theme, Layout, or
  materializer input.
* A consumer may inspect provenance and geometry but cannot treat it as a
  stable editing protocol or bypass command/revision authorization.
* Scene asset references must preserve the existing immutable closure and
  must not expose a path whose bytes are not identity-verified.

The review must also assess #375, #383, and #142 as consumers, while keeping
their implementation out of this issue except for the Scene contract and the
#375 input hand-off.

## Design deliverables

1. English `scene-v0.1` design with schema and serialization mapping.
2. Whole-architecture review that records authority, stability, capability,
   table, and asset-reference decisions.
3. An implementation plan split into independently publishable slices.

## Tentative implementation slices (subject to accepted design)

* **I385-0 — Scene closure repair.** Close semantic registry holes; add typed
  table columns and references; make the raster representation decision
  executable; characterize existing artifact bytes.
* **I385-1 — Public Scene contract.** Add schema, serializer, validation,
  deterministic JSON emission from draft and immutable render paths, and
  focused negative/round-trip-free tests.
* **I385-2 — Evidence and consumption seam.** Materialize representative
  Scenes, add an external-consumer fixture that reads Scene alone, and expose
  the deterministic statistics interface #375 will consume.  Do not implement
  #375's report in this slice.
* **I385-3 — Release gate.** Run focused tests, full pytest, conformance,
  public materializer checks, generated SVG/Scene diff review, installed-wheel
  smoke, and Ubuntu/macOS/Windows CI; publish an acceptance review.

## Exit criteria

Design is ready for implementation only when it names a single source of each
public Scene field, a single serializer owner, a non-authoritative stability
contract, a typed table model, an asset identity policy, and the exact CLI and
validation behavior.  Implementation begins only after the design and its
architecture review are published.
