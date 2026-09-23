# Design Correction: Optional Detail Regions and Context Closure (#350)

**Status:** Design complete — amends the Detail Profile and Layout Closure correction before I350R-4 acceptance.

## Finding

Extending the shared Controller Z executive layout with required detail sources
made the public `plan-only` context fail for the right reason: it selects a
smaller, ungrouped projection while binding an executive Detail Profile whose
group and milestone references are outside that View's selected projection.
The failure must not be hidden by filtering invalid references or by adapter
fallback.

## Corrected contract

A detail source slot expresses where a bound Detail Profile section can be
placed; it does not require every View using that layout to bind a Detail
Profile.  Controller Z's `group-details`, `milestones`, and `observations`
slots are therefore optional source regions with diagnostic overflow when they
are populated.  When a Detail Profile is bound, every section it declares
still requires a matching layout source.  When a layout declares a required
detail source, the profile must provide that section.  These two rules retain
strict closure without treating absent optional presentation content as an
error.

The `plan-only` Context removes the incompatible Detail Profile binding.  It
continues to use the shared layout but produces no detail placements.  Its
View, selection, and schedule semantics are unchanged.

## Architecture consistency review

Detail remains the sole owner of optional detail wording and source selection;
View remains the owner of schedule selection; Layout declares regions and
solves their geometry; Scene projects completed placements.  No layer infers a
replacement profile, drops an invalid profile entry, or changes selected
Project facts.  This is a closure correction rather than a compatibility
path: a bound profile with references outside its View still rejects with its
existing deterministic diagnostic.

## Acceptance

- the four Controller Z public contexts materialize from their declared
  closures;
- executive, elevated, and icons contexts render every section of their bound
  Detail Profile through the shared layout;
- plan-only renders without a Detail Profile and without detail placements;
- a bound section with no source and a required source with no matching
  section both reject before Scene;
- generated public materializer evidence is regenerated and byte-checked.
