# Design Plan: Remove the unreachable historical lane helper (#385 correction)

**Status:** Accepted.

## Trigger

I385-3's required module-reachability gate found
`chrona.presentation.layout.lanes` unreachable from every product entry point.
The module has only test imports.  It predates the current composed-surface
Layout and must not be made reachable merely to satisfy a quality gate.

## Questions

1. Does the live Layout composition own an equivalent lane-stacking policy?
2. Would deletion change a public contract or remove a live rendering path?
3. Is an integration, a staged-module exemption, or deletion the clean
   architectural remedy?

## Required outputs

* A correction design and architecture-alignment review that identifies the
  authoritative owner of live Layout placement.
* A narrowly scoped implementation plan for the selected remedy.
* A separately published implementation and release-gate evidence.

## Guardrails

* Do not add a synthetic production import or a `staged_modules` exemption.
* Do not alter Scene, Layout, or public rendering behavior while addressing
  historical unreachable code.
