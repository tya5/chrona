# Issue #357 — Catalog-neutral Performance Design Correction

## Reason for correction

The prior package-projection correction improves only Chrona's bundled Material
catalog.  That contradicts #350: a user-imported Iconify catalog and the
bundled catalog are the same ordinary, identity-pinned catalog resource.  A
second package-only format and reader are therefore rejected.

## Corrected architecture

`chrona.resources` owns the safe YAML/JSON codec because every production layer
may already depend on Resources.  It selects `CSafeLoader` with a SafeLoader
fallback; a payload whose first non-space byte is `{` is decoded by `json.loads`.
JSON remains valid YAML and does not create a catalog version or reader family.

An icon catalog closes in two stages:

1. **Catalog envelope closure:** validate version/kind/id, set, aliases,
   provenance, icon-name map, and entry-alias map; retain each entry's raw,
   normalized document value by canonical name.
2. **Selected entry closure:** after the typed View identifies direct and
   encoded references, resolve aliases, validate each selected entry against
   the existing entry definition, and expand its compact command stream.

The catalog resource remains identity-pinned and the importer validates every
source icon at write time.  Runtime selection does not trust a package or skip
validation: it defers entry validation until the only point where that entry
can affect Layout/Scene.  Unknown references still compute candidates from the
closed complete name index.

Materialization decodes each catalog once.  Its raster-copy scan receives the
same decoded catalog document used by closure, or an explicit raster descriptor
derived at envelope closure; it never re-parses bytes merely to discover that a
vector-only catalog has no raster assets.

## Required changes

| Slice | Result |
| --- | --- |
| C357-1 | Move the safe codec under Resources; restore inward import legality. |
| C357-2 | Remove package projection artifacts and readers. |
| C357-3 | Add generic envelope/selected-entry catalog contracts and use View-selected names for closure. |
| C357-4 | Make importer/catalog generation emit deterministic JSON YAML-subset resources. |
| C357-5 | Prove bundled and user-imported large catalogs use the same path, reproduce public bytes, and pass all release gates. |

## Acceptance

- A one-byte-different catalog never receives special treatment because no
  special package path exists.
- A selected malformed entry fails with the existing catalog diagnostic; an
  unselected entry does not incur geometry expansion.
- Bundled Material and a separately imported catalog both meet the recorded
  performance path without a provider-dependent branch.
- Import-direction, full suite, corpus materializers, wheel smoke, and CI are
  green.
