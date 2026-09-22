# Issue 133 View-contract Design Correction

## Trigger

Issue 125 has published `chrona/view/v0.4` as an immutable public contract. Issue 133 needs two new authoring vocabulary values: `totalFloat` table source and `visibility.relations: critical`. Editing v0.4 would make existing content identify different semantics with the same version.

## Corrected decision

Issue 133 introduces `chrona/view/v0.5` atomically. It is a strict replacement: schema resource mapping, inventory, README, all checked-in Views, and schema/closure tests move in one PR. There is no compatibility parser for v0.4. The only syntax changes are `totalFloat` as a table source and `critical` as a relation visibility mode; both have effect only when scheduler analysis is present.

`dependency-critical` is a closed semantic-registry binding and a required Theme role whenever a v0.5 View selects critical relations. It is not a View-defined role and does not introduce a renderer primitive. A context lacking that role fails closure/Theme validation before Layout.

## Architecture review

The correction preserves resource identity, scheduler authority, the closed semantic registry, Theme ownership of appearance, Layout ownership of routes, Scene projection, and serializer-only renderers. It prevents a schema version from becoming an undocumented capability switch and makes critical relation materializability a closure property rather than a late rendering fallback.

## Implementation amendment

Replace Slice 3 with one atomic public-contract slice: v0.5 migration, View normalization/filtering, registry and Theme role validation, completed Layout relation provenance, Scene role selection, fixtures, materializer characterization, and generated SVG review. It may merge only when every current materializable context has either migrated Theme evidence or does not select the critical relation mode.
