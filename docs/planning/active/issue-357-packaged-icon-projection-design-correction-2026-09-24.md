# Issue #357 — Packaged Icon Projection Design Correction (Superseded)

**Superseded:** the 2026-09-24 review correctly found that a bundled-only
projection violates the catalog-neutral #350 model.  It is retained solely as
an audit record and replaced by
`issue-357-catalog-neutral-performance-design-correction-2026-09-24.md`.

## Discovery

After I357-1/2, ordinary Controller Z materialization is below the target, but
the bundled Material slide is not.  The profile attributes the remaining cost
to full-catalog generic schema validation and eager typed command expansion,
not to repeated schema parsing.  A 6.5 MB catalog with 4,015 vector entries is
decoded and expanded even when a View selects four icons.

## Corrected decision

Ship a generated, renderer-neutral **package projection** beside the bundled
catalog source.  It represents the same normalized catalog as compact,
selected-on-demand contract data and records the source catalog's SHA-256.
The generation command is the sole writer of both source catalog and
projection.  Tests prove source identity, complete entry/alias coverage, and
equivalent selected geometry.

At closure, a projection is eligible only when all are true:

1. the expected kind is `icon-catalog`;
2. the resource payload SHA-256 equals the known packaged catalog identity;
3. the generated projection declares that exact identity; and
4. the catalog ID and version agree with the identity-pinned reference.

The resource may have been copied into a materialized local snapshot; identity,
not store spelling, is the authority.  Any other catalog follows the standard
YAML -> schema -> typed contract path unchanged.  No external YAML is cached
and no user-supplied payload receives package trust.

The materializer recognizes the known vector-only projection and copies its
catalog bytes without parsing them for raster assets.  Unknown catalogs retain
the existing raster-asset scan and validation path.

## Whole-architecture review

| Boundary | Corrected responsibility | Guard |
| --- | --- | --- |
| Generator -> package | Create source catalog and projection atomically from pinned upstream input. | Source SHA and complete coverage tests. |
| Snapshot -> closure | Select projection only by exact payload identity. | No provider/store shortcut. |
| Catalog -> Layout | Resolve only selected paths into completed vector assets. | Same `IconAsset`/Scene contract. |
| User catalog -> closure | Retain generic schema and geometry contract parsing. | No behavior or trust broadening. |
| Materializer -> snapshot | Skip raster scan only for proven vector-only package projection. | Unknown catalogs retain scan. |

## Acceptance additions

- The projected default closes its selected Material assets without generic
  full-catalog YAML/schema/geometry expansion.
- Source and projection coverage/geometry are equivalent for every canonical
  entry and alias.
- A payload differing by one byte cannot select the projection.
- The public Material materialization is under two seconds on the recorded
  development environment; all existing byte and diagnostic evidence remains
  unchanged.
