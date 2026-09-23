# Issue 314 Colour Scale Design Correction

## Trigger

Implementation inventory found that `category` has two distinct live uses:
field-driven scale candidates and static group-band Theme bindings.  It also
found that Review Detail's authored legend entries describe semantic roles,
not necessarily a category scale.  Removing either generic facility would
break materializable Contexts and incorrectly make scale semantics own all
legend content.

## Corrected contract

Color Scheme v0.2 exposes a named `categories` slot map.  Theme v0.4 may bind
one ordinary role directly to `category:<slot>` for a static semantic role, or
define a scale's exact value-to-slot table.  Both paths resolve through the one
Scheme literal authority; only the latter consumes a View field and produces a
derived legend.

Review Detail semantic legend entries remain.  Scale-derived entries are
separately identified by scale/value provenance and cannot be hand-overridden
or duplicated.  Layout receives their combined, already-resolved content;
Scene projects completed placements and receives concrete paint only.

## Architecture review

The correction maintains one appearance authority while keeping static role
paint separate from data-dependent encoding.  It avoids a false migration that
would either force group semantics through a fake data scale or erase valid
semantic legend information.  The closed scale contract, no-fallback rule, and
Scene/Layout boundaries of Specification 60 remain unchanged.
