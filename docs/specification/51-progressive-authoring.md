# Progressive Authoring

**Status:** Proposed
**Depends on:** [05 Project Format](05-project-format.md), [06 View Model](06-view-model.md), [09 Application Architecture](09-application-architecture.md), [10 Command Model](10-command-model.md), [13 Presentation Format](13-presentation-format.md), [21 Extension Lifecycle](21-extension-lifecycle-successor.md)
**Owns:** the compact authoring-workspace source facade, its normalization boundary,
presentation-preset binding and materialization transition.

## 1. Purpose and boundary

Progressive authoring gives a new author a short source format without introducing a
second Project, scheduler, presentation pipeline, or Scene model.  It has exactly two
presentation modes: a guided pinned `PresentationBinding` (Stages 1 and 2), and a
locally owned explicit resource bundle (Stage 3).  Existing explicit projects are
already Stage 3 and never require migration.

The sole reader of guided syntax is the Authoring Normalizer:

```text
authoring workspace + pinned preset package
  -> Authoring Normalizer -> typed resource closure
  -> Project -> Scheduler -> View -> Layout -> Scene -> renderer
```

No downstream component may read compact syntax, infer a preset, or retain workspace
coordinates.  Scene, routes, font metrics, resolved dates, and View geometry remain
derived output.

## 2. Source and resource contracts

`authoring-workspace/v0.1` is a closed document with compact `project`, optional
`actuals`, and exactly one mode-discriminated `presentation` member. Guided mode carries
a binding; explicit mode carries exact local View, Theme, Scheme, Layout, Render Context,
and receipt references and has no binding or inheritance edge. Project spelling normalizes to
Project v0.5; observations normalize to Actual Set v0.2.  Those existing schemas remain
the semantic acceptance authority.  The compact document cannot express derived or
renderer-local state.

A `presentation-preset/v0.1` is a verified declarative package member containing exact
immutable View, Theme, Color Scheme, Layout Profile, target, and environment references.
It contains no Project data, executable code, `latest` reference, or renderer-local
fallback.  Registry acquisition, trust, compatibility, content identity, and upgrade
rules are owned by Specification 21.

The planned schema set is deliberately closed and versioned:

| Contract | Owner and purpose |
| --- | --- |
| `authoring-workspace/v0.1` | compact semantic source and one mode-discriminated presentation member |
| `presentation-preset/v0.1` | immutable declarative default-resource package member |
| `presentation-binding/v0.1` | exact preset identity plus the closed guided override vocabulary |
| `presentation-materialization-receipt/v0.1` | non-rendered provenance for a completed Stage-3 ejection |
| successor authoring-command registry | typed workspace commands and one atomic multi-resource materialization transaction |

The schema and fixture files are an implementation prerequisite, not a claim that the
current runtime accepts these kinds.

## 3. Stages and precedence

Stage 1 binds one exact preset and optionally selects a compatible colour scheme.  It
may be evaluated as Draft without hidden snapshots or files; reproducible evaluation
requires an immutable closure containing the workspace and preset identities.

Stage 2 permits only typed presentation overrides: View window, grouping, visibility,
View-local annotations/anchors, and a preset-admitted Theme scheme selection.  It may
not change Project, Actual, calendar, dependency, schedule, target, Layout, Style,
font, or Scene state.  Its structural merge law is:

```text
preset defaults < binding overrides < materialized explicit resources
```

The last term exists only for the atomic candidate created when leaving guided mode;
a live guided workspace cannot partly inherit and partly own arbitrary resources.

Stage 3 is entered only by `MaterializePresentationPreset`.  The command resolves the
pinned preset and binding once, atomically writes canonical local View, Theme, Scheme,
Layout, and Render Context resources, switches the workspace to `explicit`, and writes
a receipt.  The receipt records preset and binding identities, normalizer version, and
generated resource identities; it is provenance, never a fallback inheritance edge.
The explicit workspace is evaluated only through its ordinary explicit resource closure;
the Authoring Normalizer never reads explicit mode.

## 4. Mutation, closure, and evidence

All CLI, GUI, AI, and automation mutation uses the Command Engine. An Authoring Command
Use Case applies the closed source intent and normalizes the complete candidate before
passing canonical byte candidates and the base revision to the Engine; the Engine owns
CAS/transactions and must not import or interpret authoring or presentation types. The successor
closed command family is `setWorkspaceTask`, `setWorkspaceActual`,
`selectPresentationPreset`, `setPresentationOverride`, and
`materializePresentationPreset`.  It validates the complete normalized candidate,
uses one compare-and-set transaction across named canonical files, and rejects stale
bases, collisions, incomplete closure, illegal override, or output-proof failure
without writing any part of the candidate.  Undo/redo creates ordinary new revisions.

A guided closure records workspace content identity, preset package ID/version/content
identity, binding identity, normalizer grammar version, effective resource identities,
and Draft versus immutable origin.  Equal immutable inputs, target, and environment
must normalize and render identically.  Materialization must prove byte-equivalent
output in that same target/environment and does not silently upgrade the preset.

Required implementation evidence includes malformed and untrusted preset fixtures,
override rejection, deterministic guided render/provenance fixtures, atomicity and
stale/collision cases, Stage-2-to-3 byte equivalence, closure validation, and public
materializer coverage.  A screenshot or hand-authored SVG is not sufficient evidence.

### 4.1 Workspace revision recovery

Before the first `authoring-command/v0.1` mutation, a caller obtains the
workspace-local compare-and-set precondition through:

```text
chrona workspace revision WORKSPACE
```

The command validates the workspace and prints its canonical workspace content
identity. That value is the command's `baseRevision`; it is not a Revision
Store token. An authoring command result has the separate
`authoring-command-result/v0.1` contract: `commandBaseRevision` records the
supplied value, `workspaceRevision` records the value observed by the writer,
and `resultRevision` is the accepted next value. A stale result carries
`E_AUTHORING_BASE_REVISION` with both expected and received identities. This
file-local rule is the equivalent precondition allowed by Specification 10 and
does not modify the Store-command rules in Specification 35.

## 5. Successor boundaries

This document does not add a compatibility parser, GUI workflow, external-sync
behavior, or a new renderer.  Issue 148 may add terse source syntax only as a parser
into `authoring-workspace/v0.1`; it cannot create another normalized model, preset
resolver, override grammar, or materialization operation.  The detailed decision and
acceptance rationale is recorded in
`docs/reviews/current/issue-222-progressive-authoring-design-2026-09-22.md`.
