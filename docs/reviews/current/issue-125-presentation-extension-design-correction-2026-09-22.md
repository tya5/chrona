# Issue 125 Presentation Extension Design Correction

## Trigger

Implementation inspection found that the existing profile package is a
Project-field validator, not a generic presentation package registry.  Adding
`presentationExtensions` to its YAML alone would create a second semantic
authority and cannot prove Theme-role availability.

## Corrected decision

Issue 125 ships no package-defined semantic or column source.  It ships the
complete bounded flexibility path: View intent, Layout fallback ladder, and
typed placement evidence.  The existing closed semantic registry remains the
sole authority.

A future extension feature must introduce a separate immutable presentation
package resource with: a package identity, namespaced semantic/column IDs,
declared primitive/role compatibility, Context reference ownership, generic
closure validation, and an explicit Theme role contract.  It may not reuse the
Project profile package merely because both are called extensions.

## Architecture review

This correction avoids coupling Project domain-profile validation to
presentation vocabulary and preserves the closure -> View -> Layout -> Scene ->
renderer boundary.  It narrows #125 without weakening its stated flexibility
goal: authors can declare deterministic placement preferences, but new visual
meanings remain a separately designed capability rather than arbitrary YAML.
