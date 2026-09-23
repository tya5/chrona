# C-GDF-2 Design Plan: Paired Ordinary Corpus Gallery

**Status:** Complete  
**Depends on:** C-GDF-1, Specifications 32 and 58

## Objective

Create the first two reproducible gallery directions without package,
acquisition, lock, guided-workspace, or Design Summary authority. Controller Z
Executive and Plan-only will share the same Project and Actual inputs while
using independent ordinary View resources and immutable Contexts.

## Architecture and data model

The corpus manifest remains the only source of slide identity and expected SVG.
Each slide names a Context. A successor gallery catalogue is documentation that
names a corpus/slide pair, a comparison-set ID/axis, editorial narration,
declared target/capabilities, and accessibility note. It contains no resource
path, View/Layout/Theme settings, Project/Actual facts, geometry, renderer
option, or package selector.

Validation order is: corpus slide -> Context closure -> equality of Project and
Actual references across pair -> inequality of at least one ordinary
presentation reference -> target/capability assertion -> documentary field
integrity. The catalogue cannot derive output or select a resource. Visual
comparison remains human review of public materializer SVGs; no summary
restatement is introduced.

## Implementation plan

1. Add a Plan-only Context with the existing Project, Actual, Theme, Scheme,
   Layout, font environment, and target; only View changes. Add the declared
   slide and generated materializer SVG.
2. Introduce a `chrona/design-gallery/v0.1` documentary catalogue and a pure
   inventory validator using only corpus manifest/Context documents. Add stable
   diagnostics for duplicate/dangling entry, invalid pair, semantic mismatch,
   missing presentation distinction, target mismatch, and missing narration.
3. Replace the flat gallery index with two Controller Z entries in one paired
   set, then add concise reader narration and accessibility notes.
4. Run public materializer verification for both slides and the final release
   gates. Review generated SVG changes together.

## Acceptance

The two entries share identical pinned Project/Actual references, differ in
their View reference, materialize to declared byte evidence, and validate as a
pair. Changing catalogue prose cannot alter render output. No package code or
new visual capability is introduced.
