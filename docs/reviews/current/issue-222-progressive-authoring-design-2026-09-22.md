# Issue 222 Progressive Three-stage Authoring Design

**Design-plan authority:**
`docs/planning/active/issue-222-progressive-authoring-design-plan-2026-09-22.md`

## Decision

Chrona gains a guided **authoring workspace** with exactly two mutually
exclusive presentation modes: a pinned `PresentationBinding` (Stages 1 and 2)
or a locally owned explicit resource bundle (Stage 3). The workspace is a
source-format facade, not a second scheduler, renderer, or scene model. Its
normalizer constructs the existing typed Project, Actual Set, View, Theme,
Color Scheme, Layout Profile, and Render Context inputs; the ordinary closure,
schedule, View, Layout, Scene, and renderer path then applies unchanged.

```text
authoring workspace + pinned preset package
  -> Authoring Normalizer -> existing typed resource closure
  -> Project -> Scheduler -> View -> Layout -> Scene -> renderer
```

The normalizer is the only component allowed to read guided syntax. It validates
the authored workspace and preset schemas before constructing typed records;
it does not add defaults outside the declared preset, reparse downstream raw
documents, or select a renderer fallback.

## Resource model and ownership

| Concept | Durable owner | Derived/non-owner |
| --- | --- | --- |
| task, planned date, dependency, calendar | normalized Project | preset, View, renderer |
| observed actual | normalized Actual Set | Project schedule, preset |
| compact spelling | `authoring-workspace/v0.1` | scheduler, Scene |
| preset identity/default resource bundle | `presentation-preset/v0.1`, acquired as a declarative package | Project semantics, renderer |
| Stage-2 presentation choice | `PresentationBinding` inside workspace | Project, Scheduler, Layout geometry |
| effective resources/provenance | normalized closure manifest | persistent authoring state |
| Stage-3 local View/Theme/Scheme/Layout/Context | existing explicit resources | preset resolver after ejection |

`authoring-workspace/v0.1` has a closed `project` shorthand, optional
`actuals`, and one `presentation` member. Its task spelling is source syntax
only; it normalizes to Project v0.5 object/relationship values and Actual Set
v0.2 observations, then those exact current schemas provide semantic acceptance.
No compact field may express a resolved date, Scene coordinate, font metric,
route, View geometry, Style selector, or renderer option.

A `presentation-preset/v0.1` is a declarative, versioned package member. It
names immutable default View, Theme, Color Scheme, Layout Profile, target, and
environment references. It cannot contain Project data, executable code, a
relative “latest” dependency, or a renderer-local rule. Package acquisition,
trust, exact version/content identity, compatibility, and explicit upgrades
follow Specification 21; a preset is not profile inheritance and cannot load a
code plugin.

## The stages

### Stage 1 — Start

An author declares tasks/dates/actuals and a `PresentationBinding` containing
one exact preset reference and an optional scheme selection admitted by that
preset. The normalizer resolves the pinned package and produces the effective
resource closure. The first useful timeline therefore needs no authored View,
Theme, Layout, or Context files, but it has the same semantic schedule and
presentation pipeline as an explicit timeline.

Draft rendering may read the workspace and its declared preset reference, mark
all ingress identities `draft`, and create no snapshot or hidden files.
Reproducible rendering requires the workspace and its preset package reference
to be present in an immutable Render Context closure with exact identities.

### Stage 2 — Present

The binding may add only a closed, typed override vocabulary:

* View: declared window, grouping, label/relation/annotation visibility, and
  View-local annotations/anchors;
* Theme: Color Scheme selection from the preset's declared compatible schemes;
* no Project, Actual, calendar, relation, schedule, target-capability, Layout,
  Style, font, or Scene field.

The merge law is structural and field-specific, never a generic YAML merge:

```text
preset defaults < binding overrides < materialized explicit resources
```

The final term exists only during the atomic ejection candidate. A live guided
workspace cannot mix inherited and arbitrary partial explicit resources; that
would make ownership/provenance ambiguous. Unknown override paths, conflicting
members, unsupported scheme, missing preset, incompatible package, and an
attempt to mutate semantic state through Stage 2 are stable diagnostics.

### Stage 3 — Design

`MaterializePresentationPreset` is an explicit, one-way Command. It resolves
the pinned preset plus binding overrides once and atomically writes local View,
Theme, Scheme, Layout, and Render Context resources in canonical order. It
changes the workspace presentation mode to `explicit` and stores a non-rendered
materialization receipt containing source preset identity, binding identity,
normalizer version, and generated resource identities. The receipt is review
provenance, not a fallback inheritance edge.

The command must produce byte-identical output for the same target/environment
and must not silently update a preset. It rejects if the candidate cannot be
fully materialized, any destination conflicts, the base revision is stale, or
its output-equivalence proof fails. Rejection writes nothing. Undo/redo creates
a new revision through ordinary Command semantics; it never rewrites history
or restores a mutable package version. An existing explicit project is already
Stage 3 and is never forced through a workspace or preset migration.

## Command and client contract

All clients submit typed commands to an `authoring-workspace` target whose base
revision covers its named canonical files. New closed commands are:

| Command | Permitted target change |
| --- | --- |
| `setWorkspaceTask` / `setWorkspaceActual` | Stage-1 compact semantic source only; normalized candidate must pass current Project/Actual validation and scheduling. |
| `selectPresentationPreset` | Exact preset identity only. |
| `setPresentationOverride` | Stage-2 closed View/Theme/annotation override only. |
| `materializePresentationPreset` | Atomic Stage-2 → Stage-3 resource bundle and receipt. |

The Command Engine validates the complete normalized candidate, performs one
compare-and-set transaction, and returns the authored and normalized change
sets plus preset provenance. GUI dragging yields a semantic or View annotation
proposal, never a coordinate write; CLI and AI have no bypass. A command
targeting an explicit Stage-3 bundle uses existing Project/Actual/View commands
and cannot re-enable implicit preset inheritance.

## Provenance, determinism, and diagnostics

Every resolved guided closure records workspace content identity, preset package
ID/version/content identity, binding override identity, normalizer grammar
version, effective resource identities, and whether the origin is draft or
immutable. Scene nodes retain their ordinary Project/View source provenance;
they do not acquire facade-specific coordinates or become canonical records.

For identical immutable workspace, preset package, environment, and target,
normalization and output are byte-reproducible. A preset upgrade is a separate
explicit Command that changes the pinned identity and is reviewable before
rendering. No resolver follows a mutable branch, registry latest, host theme,
font, locale, or editor state.

## Use cases and acceptance design

Add UC-22 through UC-28 under **Progressive Authoring and Presentation**:

| ID | Goal | Evidence |
| --- | --- | --- |
| UC-22 | Start a plan-vs-actual timeline | compact fixture → normalized closure → deterministic draft and immutable render |
| UC-23 | Change plan/actual data | semantic Command acceptance/rejection; no presentation mutation |
| UC-24 | Adapt for an audience | Stage-2 override fixture; Project/schedule identity unchanged |
| UC-25 | Edit a presentation annotation | View-owned command and no semantic/Scene-coordinate mutation |
| UC-26 | Inspect effective provenance | closure manifest with preset/binding/effective identities |
| UC-27 | Materialize a preset | atomic resource diff and byte-equivalence fixture; undo/redo/stale/failure cases |
| UC-28 | Retain an explicit project | explicit fixture bypasses workspace resolver and has no preset edge |

Acceptance requires schema/contract fixtures for malformed workspace/preset,
unknown or untrusted/incompatible preset, illegal override, duplicate receipt,
stale materialization, collision, and failed output proof; deterministic
Stage-1/Stage-2 output and provenance fixtures; command atomicity; byte
equivalence across Stage 2→3; materialized resource schema/closure checks; and
public materializer coverage. No acceptance is satisfied by a GUI screenshot or
hand-authored SVG.

## Scope boundary and #148

#222 designs the workspace source model and transitions only. #148 may define
a terse textual front-end **only** as a parser into `authoring-workspace/v0.1`;
it may not create another normalized Project form, preset resolver, override
grammar, or materialization behavior. Implementation begins only after this
design and its architecture review are merged; #148 follows #222's future
implementation acceptance, not merely this document.
