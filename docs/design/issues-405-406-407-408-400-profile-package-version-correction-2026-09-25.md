# Design Correction — Project-Format Package Requirement (#405, #406, #407, #408, #400)

**Status:** Accepted correction before I1 publication.

`chrona/profile/v0.3` replaces v0.2 and pins `requires.projectFormat` to
`timeline/v0.7`. A package requirement is an immutable compatibility statement,
not a permissive hint, so the v0.2 schema is not widened to admit both project
formats. Package resources and all references to them migrate atomically with
the Project/View source contracts. This keeps project capability verification
at closure resolution and does not leak format compatibility into Layout.
