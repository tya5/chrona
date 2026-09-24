# Published Inspection Scene Design (#385)

**Decision:** Accepted.

## 1. Purpose and authority

`chrona/scene/v0.1` is a deterministic, renderer-neutral **inspection and
adapter artifact** for one completed review render.  It exposes the data from
which an adapter drew, including provenance and completed geometry; it is not
an authoring format, a replacement Render Context, or a stable editing
protocol.

```text
immutable or Draft closure
        -> projection / content / measurement / Layout
        -> completed SceneSurface
             -> target adapter
             -> scene-v0.1 serializer
```

The serializer is a sibling projection of the target adapter.  It receives a
completed typed Scene and immutable closure provenance.  It must never measure
text, route a relation, resolve Theme tokens, choose a visual role, read an
asset path, or reconstruct table structure from a primitive identifier.

Scene geometry is stable only for the exact Chrona implementation/layout
version and closure identity that produced it.  Consumers needing repeatable
geometry pin both; consumers must not assume coordinate stability across
layout versions.  Scene has no authority to modify Project state.  Edits still
flow through the normal Command and revision-token contracts.

## 2. Runtime model repair

`PresentationScene` is currently an unused historical aggregate while the
runtime constructs `SceneSurface`.  Retaining two competing representations
would make a serializer choose a truth source.  Replace the unused aggregate
with one runtime-produced `InspectionScene` value:

```text
InspectionScene
  provenance        immutable closure identities and render mode
  viewport          final viewport
  capabilities      completed features an adapter must understand
  surfaces[]        completed SceneSurface values
  manifest          derived counts and font/scale evidence
  diagnostics[]     non-fatal render diagnostics only
```

`RenderedReview` carries this value and retains `surface` only as a derived
single-surface convenience until every in-tree caller uses `scene.surface`.
The in-tree renderers continue to accept `SceneSurface`; they do not receive
closure or serializer data.  This removes the unused aggregate rather than
adding a parallel document model.

## 3. Public document and schema

Add `schemas/scene-v0.1.schema.yaml`, registered as a live inspection schema.
The emitted UTF-8 JSON document is a schema-validated projection of
`InspectionScene` with this envelope:

```json
{
  "version": "chrona/scene/v0.1",
  "kind": "scene",
  "provenance": {
    "mode": "draft|immutable",
    "chronaVersion": "…",
    "resources": [{"kind": "view", "id": "…", "revision": "…", "contentIdentity": "sha256:…"}]
  },
  "viewport": {"inlineSize": 1600, "blockSize": 900},
  "requiredCapabilities": ["…"],
  "surfaces": [],
  "manifest": {},
  "diagnostics": []
}
```

All object keys have a fixed serialization order; collections preserve
completed Scene order except that provenance resources are canonicalized by
`(kind, id, revision, contentIdentity)` and capability strings are sorted.
Floats are JSON numbers rounded once by the existing Scene precision policy;
dates are ISO-8601 strings.  There is no YAML output option and no
canonicalization through generic dataclass reflection: an explicit serializer
maps every public field so additions are reviewed as contract changes.

Each surface emits slots, rows, groups, scales, columns, primitives, and
canvas paint.  Primitives retain opaque `sceneId`, source provenance, purpose,
visual role, complete geometry/paint/text/icon data, and typed table links.
Optional fields are omitted rather than emitted as `null`; required geometry
arrays are never inferred by a consumer.  The schema rejects unknown keys,
non-finite numbers, malformed SHA-256 identities, duplicate surface/column
identities, and references to missing table rows or columns.

## 4. Table structure

Add `SceneColumn(column_id, label, bounds)` to `SceneSurface`.  Add optional
`table_row_id` and `table_column_id` fields to `ScenePrimitive`, required
together for `table-cell` primitives and prohibited elsewhere; a table-header
primitive carries only `table_column_id`.  Layout is the only creator of the
column geometry, using the same `place_table_columns` result that places text.

Existing `scene_id` values stay opaque compatibility-free implementation
identities, not a public table encoding.  In particular, a consumer must use
the typed links rather than split an identifier.  This corrects the real
structural loss without assuming that a currently controlled column id can
remain parseable forever.

## 5. Semantic and asset closure

The scene builder must obtain all roles through `semantic_registry`.
`variance-ahead`, `variance-behind`, and a scale legend's planned role become
declared semantic bindings (or a bounded registry-owned selector where the
roles share a semantic).  No Scene branch spells a role literal after this
slice.  The registry remains the source of Scene purpose/role semantics; the
schema enumerates the emitted values only as a derived contract snapshot, not
a new runtime registry.

Raster icon bytes are not embedded in scene-v0.1.  A public primitive carries
`icon.kind`, `icon.assetIdentity`, `icon.viewport`, `icon.alternative`, and
for raster `icon.encoding: "png"`; the bytes remain in the already
identity-verified closure asset.  This avoids duplicating arbitrary binary
data in an inspection document and lets a consumer obtain a raster only by
resolving the pinned asset identity from its closure.  A Scene that contains a
raster therefore advertises `icon.raster`; a consumer unable to resolve the
identity must reject rather than substitute it.

Vector icon paths have already been completed into primitive coordinates and
are serialized as geometry.  No raw catalog SVG or host filesystem path is
exposed.

## 6. Capabilities and external consumers

`requiredCapabilities` is the sorted union of capabilities required by the
completed scene: `mark.marker-geometry`, `paint.pattern-geometry`,
`mark.symbol-outline`, `icon.vector`, and `icon.raster` when present.  These
reuse the established visual-capability names because they describe completed
Scene feature data, not because a target profile becomes an adapter registry.

An external consumer declares a static `supportedCapabilities` set next to its
own entry point and must require `scene.requiredCapabilities ⊆ supported`.
On failure it reports `E_SCENE_CAPABILITY_UNSUPPORTED` with the missing sorted
capabilities before output.  Chrona v0.1 does not load, register, or execute
external consumers; the declaration is a contract for the out-of-tree adapter
fixture and future package work, not a plugin system.

## 7. CLI and validation

Add `--emit-scene PATH` to both `chrona render` and `chrona render-review`.
It is an additional, explicit output: `--output` remains required and retains
its target-artifact meaning.  Both outputs are written only after successful
render completion; an existing scene path fails with the same non-overwriting
publication discipline as other CLI results.  Draft emission records
`provenance.mode: draft`; immutable emission records all resolved resource
identities.  `--emit-scene` never modifies a Context, snapshot, manifest, or
generated SVG and is not materializer evidence by itself.

The serializer validates its own document against `scene-v0.1` before writing.
The CLI reports schema/serialization failure as `E_SCENE_SERIALIZATION`; a
consumer capability failure is not a Chrona render failure because consumers
remain outside the render path.

## 8. Manifest and #375 seam

`SceneManifest` is constructed once with the completed `InspectionScene`, not
recomputed by SVG analysis.  It contains selected object ids, font identities,
surface scales, `contentFamilyCounts`, and an exact `visualRoleCounts` map.
The public serialization includes both.  #375 consumes checked-in emitted
Scenes through a small read-only inventory tool; it does not import Scene
builder code, parse SVG `data-*` attributes, or calculate roles from source.

## 9. Rejected alternatives

* **Serialize `SceneSurface` ad hoc in the CLI.** It omits provenance and
  manifest ownership and leaves the unused aggregate as a second truth.
* **Make Scene self-contained by base64 embedding raster bytes.** It duplicates
  verified assets, expands artifacts, and bypasses closure identity resolution.
* **Publish only SVG metadata.** It cannot expose scale, slots, table columns,
  typed links, completed text evidence, or role granularity.
* **Use scene IDs as table schema.** It makes string formatting an accidental
  public API and requires consumers to parse producer-local syntax.
* **Create a core external-renderer registry now.** It broadens #385 into a
  plugin/package design before a second adapter proves the boundary.

## 10. Acceptance

* `scene-v0.1` validates and is deterministically emitted from both draft and
  immutable render paths without changing their target artifact bytes.
* Every Scene field has one named producer; serializers and adapters do not
  redo Layout/Theme policy.
* Table columns and cell links are typed and do not require identifier parsing.
* Icons preserve immutable asset provenance without embedding raw raster bytes.
* A standalone adapter fixture consumes a serialized corpus Scene alone,
  declares capabilities, and rejects missing capability support.
* #375 has a stable serialized Scene input for role/content-family reporting.
