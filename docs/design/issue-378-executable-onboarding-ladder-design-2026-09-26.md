# Design — Executable Onboarding Ladder (#378)

**Status:** Proposed for architecture review.

## Audit result

#376 and #377 satisfy literal rungs 1–2.  The remaining gallery appearance
evidence is real but is not a preset library: the gallery is generated from
immutable Contexts and has no rendering authority.  Two ordinary local preset
files exist for Controller Z; the three HALCYON appearance peers are Context
variants, not reusable preset source.  The previously designed
`presentation-packages/` acquisition/lock topology is intentionally
unimplemented, so it cannot be represented as an available user command.

The current Theme and View contracts are complete documents.  Layout's
`extends` implementation demonstrates that inheritance must be typed and
identity-checked, but it cannot be copied: it resolves only a Layout node
override map and does not provide a general document merge.  Guided workspace
`binding.overrides` remains a closed operational governance vocabulary and is
not an author styling API.

## Decision: three separately owned onboarding releases

### 1. Builtin preset library

Chrona ships a finite, package-owned `preset-library/v0.1` catalogue and the
ordinary View/Theme/Scheme/Layout/preset bundles it names.  A new explicit CLI
copy command selects a catalogue id and writes one complete bundle into an
empty user directory.  `chrona render PROJECT --preset DIRECTORY/preset.yaml`
then uses the existing #377 resolver unchanged.  The command is local-only:
it performs neither registry lookup nor package acquisition.

Catalogue entries represent the two Controller Z treatments and the three
HALCYON appearance choices, each as an independently complete ordinary bundle.
They may share package resource bytes internally but are copied as ordinary
user-owned source.  The gallery links each catalogue id to its evidence; it
does not supply resource paths or become an input.  The default preset remains
the no-flag baseline, not an implicit library selection.

### 2. Bounded author-source inheritance

Theme and View inheritance need a dedicated successor design after the library
release.  The required contract is not arbitrary YAML inheritance: it needs a
typed base reference, exact content identity, acyclic resolution, a closed
override vocabulary, deterministic effective identity, and Context closure
representation.  Theme's measured variation supports an initial `values` and
`roles` map override only; all other Theme sections remain complete base-owned
data.  View requires an independent field-by-field audit before any override
surface is admitted.  A five-line Theme example is an acceptance fixture, not
permission to merge View documents generically.

This work does not extend guided-authoring overrides, move geometry into Theme,
or let a renderer resolve inheritance.  Effective ordinary resources must be
closed before Theme resolution, Layout, Scene, and adapters.

### 3. Progressive Project tutorial

The tutorial is an executable sequence of independent fixture directories.
Each directory contains only the Project/Actual additions introduced at that
step and uses the package default or one copied preset.  Its order is fixed
spans; gates; relations and lag; calendars; constraints/deadlines; hierarchy
and rollup; Actuals/progress; scenarios; snapshots; extensions.  Commands
render each step into a disposable output and documentation checking proves
them.  Corpus Contexts are cited as immutable evidence but never copied as the
tutorial's editable source.

## Designer supplier track

An outside designer needs a separate entry guide spanning Theme, Color Scheme,
and Layout, plus reliable schema/runtime vocabulary and public Scene
inspection.  Gantt-native object-type marks and dependency differentiation are
not solved by preset copying or Theme inheritance.  This remains a tracked
successor to #378; it is not a condition that turns the first-run ladder into a
guided-authoring or generic-canvas project.

## Acceptance mapping

The final #378 release records executable documentation evidence for all five
literal rungs.  Rung 4 copies and renders every catalogue entry; rung 5 waits
for the separately reviewed bounded inheritance contract and proves both a
five-line Theme and a visible output difference.  No rung claims package
acquisition, materializer reproducibility, or gallery rendering authority.
