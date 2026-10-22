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

Guided and ordinary Draft ingress share declared preset-member acquisition:
safe paths, Theme inheritance/references/expressions, View defaults, member
identity checks and optional Detail/Summary/catalogue resources. The Normalizer
receives these acquired effective documents, not a second raw-file loader.
CLI `render-workspace` and the MCP workspace renderer call one guided-render
use case and forward the same completed font/environment decisions. Diagnostic
codes never contain their explanation or JSON pointer.

The terse plan syntax of Spec 65 is a different compact source with a different owner: a text syntax for
the Project only, compiled by `chrona compile` at the adapter edge, with no presentation binding and no Actuals.
It does not read, produce or extend an authoring workspace, and neither normaliser calls the other.

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

Workspace initialization is separate from editing an existing revision. It
accepts a compact `project` of this schema and a builtin preset ID, copies that
preset through the existing preset-copy acquisition, and prepares/validates
the complete guided bundle privately. It creates a new directory under an
existing parent, containing `workspace.yaml` and the copied `preset/` tree;
the workspace ID is `<project.id>-workspace`. An existing directory, file or
symlink is a collision, never an overwrite. Publication exclusively reserves
the destination, publishes the workspace file last, and removes only its own
new destination on failure. A concurrent reader may see an unfinished new
directory before successful completion; it is not a usable workspace yet.
No CAS/replay or history policy is invented for initialization. Subsequent
edits use the existing Engine transaction. Source serialization preserves
Unicode and author key order; inverse edits create ordinary new revisions.

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

### 4.2 Durable authoring command execution (#902 item2)

CLI and MCP use the same application entry and transaction coordinator. The
authoring use case prepares and validates complete byte candidates, their next
workspace content identity and the exact result before publication. The Engine
owns lock/replay/CAS/recovery and treats candidates and results as opaque data;
it does not interpret authoring operation types or presentation models. Replace
the old pair of write callbacks rather than retaining a second mutation path.

One resolved workspace path, platform-case-normalized for identity, identifies
the transaction, lock and private replay receipts. `target.path` names that
canonical workspace filename. Revision reads follow the same resolution.
Noncanonical target filenames reject as `E_AUTHORING_TARGET_MISMATCH`, naming
the canonical filename needed for retry; alias paths do not create another lock
or receipt scope. This intentionally replaces alias-basename write behavior.
Both ordinary and materializing commands take the existing workspace OS lock.
Under it, recover a pending transaction, look up a receipt, then perform fresh
base comparison, preparation and publication. Exact accepted retries return
the original `authoring-command-result/v0.1` without writes, even after later
commands. A replay is marked (#1892 row 3): the retained result gains
`replayed: true` and `revisionIsCurrent`, true when its `resultRevision` equals
the workspace revision observed now. Both are absent from a fresh application and
from the receipt. Same ID with a different canonical request/target is
`E_AUTHORING_COMMAND_ID_REUSE`; because only an applied command leaves a receipt,
its diagnostic carries `firstApplied: true`, `appliedRevision` and
`revisionIsCurrent` and its detail says the first command was applied. The
fields are additive and optional, so the result version stays v0.1.

Append-only receipts live in a workspace-adjacent private directory, with hashed
command-ID filenames (SHA-256 of the exact UTF-8 ID, never a raw path); they retain the canonical request, request/workspace
identity and exact accepted result. They are the sole replay authority; a
materialization provenance receipt and the temporary transaction marker are not
alternative histories. Validate receipt identities and result before replay;
corrupt/mismatched receipts fail closed with `E_AUTHORING_REPLAY_UNAVAILABLE`.
Check the embedded ID against the selected filename, the canonical request hash,
the canonical workspace scope, and accepted result schema/command ID/base/next
identities. Never overwrite an earlier accepted receipt.
Do not infer old acceptance from current content: receipt-free pre-feature
commands keep their stale-base behavior. No eager workspace/schema migration.

Extend the existing recovery marker with old/new workspace identities and the
new receipt/resource identities. Stage candidates and receipt, publish resources
and receipt first, then atomically replace a changed workspace as commit point.
Before commit, rollback only the transaction's owned new files; after commit,
never remove its resources/receipt or turn accepted work into a rejection.
When the workspace identity is unchanged, atomic receipt publication is the
no-op commit point and the workspace is not rewritten. Recovery distinguishes
those cases, validates owned paths/bytes, and preserves unexpected state with
`E_AUTHORING_AGGREGATE_RECOVERY` rather than guessing or deleting unrelated files.
For a no-op marker, a final receipt matching its recorded digest proves commit;
absence is precommit, and a mismatch is recovery failure.
Legacy markers may roll back only when the old workspace identity and owned
resource paths/bytes prove that safe. Without a recorded new identity/receipt,
a changed workspace cannot prove commit: preserve state and report recovery
required, never fabricate an accepted receipt.

Post-commit marker cleanup is not mutation acceptance. A verified committed
marker permits accepted replay even if cleanup must wait; new mutations require
recovery/cleanup first. Logical refusals retain the authoring result contract;
I/O failures that prevent a safe observation/commit must not fabricate acceptance
or a pre-write rejection. This is cooperative local process-recovery, not a
distributed transaction or a guarantee against arbitrary shell edits/power loss.

## 5. Successor boundaries

This document does not add a compatibility parser, GUI workflow, external-sync
behavior, or a new renderer.  Issue 148 may add terse source syntax only as a parser
into `authoring-workspace/v0.1`; it cannot create another normalized model, preset
resolver, override grammar, or materialization operation.  The detailed decision and
acceptance rationale is recorded in
`docs/reviews/current/issue-222-progressive-authoring-design-2026-09-22.md`.
