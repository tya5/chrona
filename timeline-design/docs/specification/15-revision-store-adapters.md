# Revision Store Adapters

**Status:** Proposed  
**Core Specification:** v0.2  
**Owns:** provider-neutral persistence boundary, immutable snapshot identity,
Revision Store capabilities, adapter responsibilities, and revision/content identity
rules.

## 1. Purpose

Chrona is Git-friendly, not Git-dependent. Canonical sources SHOULD remain
line-oriented text so Git is excellent for authoring, review, branches, and durable
history. However, loading a Project, evaluating a View, editing from the GUI, or
consuming a federated export MUST NOT require a Git working tree, a Git executable, or
a Git commit.

This specification defines the **Revision Store** boundary used by those operations.
Git is one adapter behind that boundary.

## 2. Terms

| Term | Meaning |
|---|---|
| Store | A named persistence provider configured by the host. |
| Address | A stable key for a resource within one Store, such as a normalized project path or database record key. |
| Snapshot | An immutable, internally consistent set of resources exposed by a Store. |
| Revision token | An opaque identifier for a Snapshot in its owning Store. It is not ordered or comparable outside that Store. |
| Content identity | A digest of exact normalized bytes, normally `sha256:<hex>`. It is portable across Stores. |
| Draft | Mutable workspace state not yet bound to an immutable Snapshot. |

An evaluation reference therefore names **Store identity + Address + Revision token +
Content identity**. A path alone, a branch name, a database "latest" pointer, or a
host default is never a reproducible reference.

## 3. Common protocol

All adapters expose the following conceptual operations. Concrete APIs may be local,
HTTP, CLI, or embedded, but MUST preserve these meanings.

| Operation | Required behavior |
|---|---|
| `resolveSnapshot(selector)` | Resolve an explicit immutable selector to one Snapshot; reject moving selectors in reproducible mode. |
| `read(snapshot, address)` | Return bytes and metadata for an Address from that exact Snapshot. |
| `describe(snapshot)` | Return provider ID, opaque revision token, and snapshot scope metadata. |
| `verify(resourceRef)` | Read the named resource and verify its expected content identity and declared stable ID/kind. |
| `write(address, expectedRevision, change)` | Optional mutation. Atomically compare the current revision with `expectedRevision`; return a new immutable Snapshot or a conflict. |
| `snapshot(draft)` | Optional draft publication. Materialize the selected draft state as one immutable Snapshot. |

`write` MAY be implemented by a transaction, compare-and-set, append-only event,
or creation of a new bundle. Hidden last-writer-wins behavior is prohibited. Stores
that cannot mutate simply do not expose `write`.

## 4. Required capabilities by operation

| Chrona operation | Required Store capabilities | Not required |
|---|---|---|
| Parse/validate an explicit revision | immutable `resolveSnapshot`, `read` | history, branches, mutation |
| Reproducible schedule/render | one snapshot boundary, `read`, `verify` | Git checkout, current working tree |
| GUI/CLI/agent canonical edit | `read`, atomic `write` or explicit merge | Git commit/branch |
| Review/history UI | adapter-provided `history`/`diff` capability | universal history model |
| Federation consumption | immutable `resolveSnapshot`, `read`, trust verification | shared repository or filesystem |
| Offline package viewing | read-only immutable `read`, `verify` | network or mutation |

The engine only asks for the first column. A host MAY offer extra UI when an adapter
reports `history`, `diff`, `branching`, `signatures`, or `locking` capabilities.

## 5. Standard adapter profiles

| Adapter | Snapshot boundary | Mutation | What it preserves / gives up |
|---|---|---|---|
| Git | one immutable tree commit | commit/merge guarded by expected commit | branches, reviewable diffs, distributed history; requires Git only inside this adapter |
| Local transactional | transaction/version row or immutable local snapshot | compare-and-set transaction | responsive local editing and offline storage; no universal branch/merge history unless supplied |
| Content-addressed package | signed manifest/content digest | read-only | portable, cacheable, offline reproducibility; no in-place edit or branch semantics |
| File workspace + snapshot store | snapshot produced from selected files | writes through the snapshot/local-store policy | text editing without a Git runtime; a raw "current file" is a Draft, never an immutable evaluation input |

The local adapter MAY store YAML/JSON documents, SQLite rows, or another format. The
canonical serialization rules in `05-project-format.md` remain applicable whenever it
stores canonical text; a database representation MUST serialize equivalently at the
format boundary.

## 6. Evaluation closure and caching

A reproducible Render Context and an evaluation manifest MUST record, for every
resource, the Store/provider identity, immutable revision token, normalized Address,
and content identity. The primary Project and all related resources MUST resolve from
one declared snapshot boundary or from individually pinned immutable snapshots.

The cache key includes these identities and engine versions. Implementations MAY use a
revision token for local invalidation, but MUST use content identity when comparing
resources across Stores. They MUST NOT infer equality from token spelling.

## 7. Commands and concurrency

`baseRevision` is a Revision Store token in the target Store. The Command Engine passes
it unchanged to `write`; it neither parses nor fabricates Git syntax. On mismatch the
adapter returns a stable conflict result. An adapter may offer an explicit merge
proposal, but applying it creates a new Command/revision and is never implicit.

Interactive editing may maintain a local Draft and compute fine-grained scene deltas.
Only accepted semantic commands create canonical snapshots. This preserves the
reactivity rule: changing one object does not require rebuilding unrelated UI state.

## 8. Federation and trust

A child publishes an immutable Timeline Export through any readable adapter profile.
The parent pins its provider-neutral resource reference; consuming it does not mutate
or directly open the child workspace. Trust policy is keyed by adapter type and source
identity (for example Git repository identity, a configured local-store namespace, or
content-package signer), then verifies the pinned revision and content identity.

Git submodules, moving branches, checked-out child folders, and unpinned "latest"
database records are all invalid federation inputs.

## 9. Invariants

1. Core semantics and renderers depend on the Revision Store protocol, never a Git API.
2. Every reproducible evaluation names immutable inputs and exact content identities.
3. Revision tokens are opaque outside the Store that issued them.
4. A mutable Draft is not silently substituted for an immutable Snapshot.
5. Canonical mutation has compare-and-set semantics or an explicit, auditable merge.
6. Git-specific features are optional capabilities, not semantic requirements.

## 10. Versioning

The existing v0.1 schemas that require `git:<sha>` remain valid only for their stated
legacy format. A provider-neutral `revision-ref` schema and successor command,
presentation, and federation schemas will be introduced under RA-5. They MUST encode
the fields in section 2 rather than a free-form revision string.

## 11. Non-goals

This specification does not define replication, user permissions, a universal merge
algorithm, database schema, credential storage, or a hosted synchronization service.
It only makes their persistence contract substitutable.

## 12. Collaboration successor boundary

A hosted collaboration adapter replicates immutable snapshots and may retain an
append-only Command/audit log, but it still exposes the section 3 Store protocol.
Every proposed write carries its observed base revision. On divergence the adapter
returns a stable conflict or a separately identified merge proposal; it MUST NOT
advance a Project with last-writer-wins. A merge result identifies all parents and its
normalization policy, then becomes a new immutable Snapshot only after an explicit
resolution Command.

Replication and presence are transport state. A replica reports the exact revision it
knows and does not treat a remote moving tip as a reproducible evaluation input.

## 13. Extension acquisition successor boundary

An extension registry/source is a Store-like immutable content provider only for
declarative package resources. The Evaluation Closure Resolver verifies its provider,
address, pinned revision, and content identity before activating a package. It must not
replace a missing package with a local installation or moving registry version. Host
code-plugin installation is outside this resource protocol.
