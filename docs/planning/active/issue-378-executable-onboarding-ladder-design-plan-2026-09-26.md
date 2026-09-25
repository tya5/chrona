# Design Plan — Executable Onboarding Ladder (#378)

**Status:** In design.

## Starting point

Rungs 1–2 are complete through #377 and #376: a three-file editable starter
renders with the package-owned draft default.  The remaining #378 work is not
a single documentation edit.  It comprises a reusable appearance selection
surface (rung 4), a clean author-facing customization mechanism (rung 5), and
a progressive Project learning path (rung 3).  Designer authoring is a
parallel supplier track, not a compulsory sixth step for a first-time user.

## Current-state audit required before design

1. Inventory the two committed explicit presets and the gallery's five
   appearance/treatment sets; map each to exact View, Theme, Color Scheme, and
   Layout resources, resource roots, and installation/reuse authority.
2. Audit current Theme and View schemas/contracts/closure loading against the
   existing Layout `extends` model.  Measure which Theme and View fields vary
   across shipped resources and distinguish a bounded override from unsafe
   generic document merging.
3. Map every Project feature named in the literal issue acceptance to an
   existing, materializable corpus example and identify the smallest ordinary
   Draft fixture for an executable learning step.
4. Audit the documentation checker and wheel topology so every proposed rung
   has an executable command without depending on an untracked checkout path
   or declaring a Draft as immutable evidence.
5. Review the designer track separately: contract ownership across Theme,
   Color Scheme, and Layout; the Gantt-native vocabulary gaps; schema/runtime
   agreement; and a public Scene evaluation boundary.  Do not fold its work
   silently into first-run inheritance.

## Expected design decisions

- A shipped-preset library has one typed manifest/catalogue authority and
  references ordinary resources through safe roots.  It must not duplicate
  gallery Contexts or turn materialized evidence into mutable templates.
- Theme/View customization, if necessary after the audit, is an author-source
  inheritance/override contract with a finite eligible field vocabulary,
  explicit base reference, deterministic merge/identity rule, cycle/rejection
  policy, and no relationship to guided-authoring governance overrides.
- The tutorial uses independent source fixtures and rendered outputs per
  concept.  It progresses from raw Project semantics to optional Actuals,
  scenarios, snapshots, and extensions without requiring a user to edit a
  corpus-scale document.
- The designer supplier track is planned separately once its bounded contract
  gaps are evidenced; it does not block the bootstrap preset library.

## Publication and implementation shape

Publish the English onboarding design and whole-architecture review before
code.  Its implementation plan must separate: (1) preset library/catalogue,
(2) bounded Theme/View inheritance if the audit proves it required, (3)
progressive tutorial fixtures and documentation gate, and (4) release review.
The preset-library and its commands publish atomically; inheritance receives
its own schema/contract/materializer plan and cannot be hidden in a guide-only
change.

## Completion criteria

The accepted plan will demonstrate all literal #378 rungs through stable
commands: starter render and edit/re-render; each tutorial feature; every
shipped preset; and a visibly distinct five-line derived Theme if inheritance
is selected.  It will also state the separately-owned designer-track successor
and preserve the Draft/evidence, source/Store, View/Theme/Layout/Scene, and
package-resource boundaries.
