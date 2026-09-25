# Design Correction: Self-contained preset roots (#377)

**Decision:** A preset member path is always relative to its preset root.

The preset document and every View, Theme, Color Scheme, Layout Profile, and
optional icon catalog it names form one local declarative closure.  A preset
cannot reach a parent/project tree, infer a repository root, or resolve a
second path convention.  This makes `presentation-preset/v0.1` equally safe
for draft CLI input, guided authoring, installed-wheel defaults, and a future
acquired package without a compatibility resolver.

The current Controller Z documents are migrated into self-contained roots with
their member resources.  The former project-root-relative documents are
removed, not retained.  Corpus Contexts continue to own ordinary project
resources; preset evidence proves an independently closed presentation bundle.
Any semantic source duplication is limited to presentation resources and is
intentional bundle ownership, never Project/Actual data.
