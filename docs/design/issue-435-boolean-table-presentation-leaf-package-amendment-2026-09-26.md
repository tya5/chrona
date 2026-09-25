# Issue #435 Boolean table presentation leaf-package amendment

## Finding

Python imports a package initializer before a submodule.  Although
`presentation.model.table_presentation` itself has no dependencies,
`presentation.model.__init__` imports authoring services, which import
contracts.  Contracts therefore still cannot import a child of that package.

## Amended decision

Place `BooleanPresencePresentation` in
`chrona.presentation.table_presentation`, whose parent package is intentionally
empty.  The module remains dependency-free.  Contracts, review content, and
surface formatting import that leaf directly; `presentation.model` does not
participate in the formatter type's import path.

## Architectural consequence

This is the narrowest dependency-safe location for a presentation-wide value
that is constructed at contract ingress and consumed at content normalization.
It preserves all earlier ownership decisions and adds no compatibility or
renderer behavior.
