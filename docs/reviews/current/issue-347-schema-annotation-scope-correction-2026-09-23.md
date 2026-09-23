# Issue #347 Schema Annotation Scope Correction

**Status:** Accepted  
**Date:** 2026-09-23

## Finding

The proposed literal traversal of `then`, `else`, and `not` was evaluated
against every live schema before implementation.  It reports implementation
fragments inside conditional constraints as independently authorable schemas.
For example, a documented command-form rule would additionally require prose
on its internal `payload`, `task`, and scalar assertion fragments; shared
`allOf` overlays would duplicate the same problem.  This is not missing
author-facing documentation.

The existing annotation rule intentionally treats the documented conditional
`allOf` branch as the author-facing unit.  It already traverses ordinary
object properties, item schemas, and unions, and it reaches a conditional
behind a structural `allOf`.  The latter behaviour is covered by the focused
tool test.

## Decision

Do not change the annotation traversal for #347.  A conditional's enclosing
branch description and example remain the single explanation of that rule;
its `if`/`then`/`else`/`not` snippets are validator implementation details,
not separate authoring concepts.  No live-schema annotation is missing under
that boundary.

This corrects the earlier #347 design-review proposal before implementation.
The remaining remediation is limited to closure diagnostic detail, safe CI
efficiency changes, and the #322 historical decision record.

## Architecture review

This keeps authoring documentation attached to a semantic rule rather than
to every JSON Schema applicator fragment.  It preserves the distinction
between schema policy (the documented branch) and validation mechanics (its
subschemas), avoids duplicated and divergent documentation, and changes no
runtime contract or presentation-layer authority.
