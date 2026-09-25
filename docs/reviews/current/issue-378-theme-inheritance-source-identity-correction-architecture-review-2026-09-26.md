# Architecture Review — Theme Inheritance Source Identity Correction (#378 I378-2)

**Result:** Accepted.

The correction separates two integrity boundaries rather than weakening either
one. `SnapshotReader` remains responsible for exact stored-resource bytes; the
inheritance resolver remains responsible for semantic identity of the complete
Theme it consumes. Passing the source-byte pin to the reader and checking the
canonical pin after recursive resolution preserves reproducible Context closure
without teaching the reader about Theme semantics.

Keeping ordinary v0.11 Theme closure identity byte-based avoids a gratuitous
change to an existing resource contract. Restricting canonical effective
identity to a derived source is coherent: only that source has no single
complete Theme byte representation to use downstream.

The resolver stays entirely at presentation ingress. Context derives sibling
references from declared store, revision, and safe relative address; it cannot
consult host paths. Layout, Scene, and adapters receive the same ordinary
ThemeContract as before. The correction therefore preserves the repository's
one-way intent-to-Layout-to-Scene architecture and the original decision to
defer View inheritance.
