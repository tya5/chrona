# Design Correction: Scene Icon Viewport Closure (#385)

**Status:** Accepted correction to the Published Inspection Scene design and
implementation plan.

## Finding

The accepted Scene design requires a public raster icon reference to carry its
verified viewport alongside `kind`, asset content identity, and alternative
text.  The I385-0 implementation preserves identity and payload through
`IconPlacement`, but its placement type drops the `IconAsset.viewport` before
the Scene boundary.  A serializer would therefore have to re-parse PNG bytes
or omit a declared part of the contract.

Both outcomes violate the accepted ownership boundary: a serializer must not
derive data that the typed closure/Layout path already knows.

## Corrected boundary

```text
verified IconAsset(viewport, identity, payload)
  -> Layout IconPlacement(viewport, identity, completed bounds)
  -> ScenePrimitive(viewport, identity, completed paths or raster reference)
  -> serializer
```

Add a required positive `viewport` tuple to `IconPlacement` and populate it
at every Layout visual-placement site from the closed `IconAsset`.  Add the
same typed field to `ScenePrimitive` for icons only.  The Scene primitive
invariant rejects a missing/non-positive viewport for an icon and rejects an
icon viewport on any non-icon primitive.  Vector and raster retain the same
path; only their already-verified metadata now remains available to the
published boundary.

## Architecture review

The correction keeps icon normalization and PNG validation in the catalog
closure boundary.  Layout still owns final bounds; Scene still owns completed
geometry; the serializer merely emits values.  It does not introduce an asset
path, duplicate raster bytes, or make a renderer responsible for viewport
validation.  No authoring, Context, materializer, or external-consumer policy
changes.

## Implementation amendment

I385-0 gains the IconPlacement/ScenePrimitive metadata closure and focused
vector/raster negative tests.  I385-1 may begin only once it can serialize the
stored viewport directly.  The published schema continues to require the
viewport for every icon object.
