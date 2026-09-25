# Issue #435 Boolean table presentation dependency correction

## Trigger

The first implementation probe placed `BooleanPresencePresentation` in
`presentation.model.surface_content` so both resource parsing and content
normalization could name it.  Importing that module from contracts creates the
cycle `contracts → model package → authoring → contracts` (and, through
projection, a second contracts cycle).  That violates the repository's inward
dependency rule before any feature behavior can run.

## Corrected decision

The tagged formatter value belongs in a new dependency-free leaf module,
`presentation.model.table_presentation`.  It contains only the immutable
`BooleanPresencePresentation` value object and no projection, contract,
resource, Layout, Scene, or renderer import.

`contracts.resources` constructs it after schema validation.  Both
`surface_content.display_value` and review-content normalization import the
leaf value directly.  The previous semantic design remains unchanged: raw maps
end at resource parsing, Layout receives strings only, and Scene/adapters have
no boolean behavior.

## Review

This restores the intended dependency direction while making the formatting
value reusable at exactly the two permitted boundaries.  It is a structural
correction, not a compatibility bridge or a behavior-policy change.  The
implementation plan's I435-1 and I435-2 acceptance criteria remain valid.
