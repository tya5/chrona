# Revision Store Adapter Remediation Plan

**Status:** Active  
**Version:** 0.1  
**Purpose:** Remove Git as a required runtime or semantic dependency while preserving Git as a first-class persistence and review adapter.

## 1. Finding and decision

The current v0.1 design correctly requires immutable evaluation inputs and meaningful
text diffs, but several contracts encode a Git commit and repository as if they were
the only way to provide those properties. This conflicts with the product principle:
**Git-friendly means line-oriented, reviewable text; it does not mean that a GUI,
server, or evaluator requires Git.**

`15-revision-store-adapters.md` is the authoritative replacement boundary. Existing
v0.1 Git-shaped schemas remain historical compatibility artifacts; they are not the
long-term cross-layer contract.

## 2. Completion conditions

1. Core evaluation, commands, presentation, and federation depend on a `Revision
   Store` protocol, never on Git commands, branches, or commit syntax.
2. A Git adapter, a mutable local/transactional adapter, and a read-only
   content-addressed adapter have explicit capabilities and failure behavior.
3. Every reproducible evaluation still binds one immutable store snapshot and exact
   content identities; a working file is snapshotted before reproducible evaluation.
4. Federation pins a child export through the same provider-neutral reference and
   applies trust by adapter/source identity.
5. Versioned schemas, fixtures, and review evidence prove both Git and non-Git paths.

## 3. Work packages

| ID | Work | Primary owner | Exit evidence | Status |
|---|---|---|---|---|
| RA-1 | Define the common Revision Store protocol, identifiers, capabilities, and invariants | `15` | normative contract and adapter matrix | Complete |
| RA-2 | Record why Git is optional and which Git capabilities remain optional | ADR-0013 | decision/rationale | Complete |
| RA-3 | Generalize architecture, command, quality, project-format, and presentation ownership | `05`, `09`, `10`, `12`, `13` | cross-links and no mandatory Git path | Complete |
| RA-4 | Generalize federation source, pinning, and trust contracts | Federation design | provider-neutral export reference | Complete |
| RA-5 | Add v0.2 reference/command/presentation schemas and Git/local/content fixtures | `schemas/`, `fixtures/` | validation runner passes in CI | In progress — common reference schema drafted |
| RA-6 | Perform cross-document review against the completion conditions | review | traced findings and disposition | Pending |

## 4. Compatibility and migration

- Do **not** reinterpret a persisted `git:<sha>` value. It remains a valid Git-adapter
  revision in v0.1 documents.
- New provider-neutral contracts receive new minor-format versions. Readers MAY
  support both during migration; writers select one format per document.
- A Git implementation maps a repository tree commit to one immutable snapshot.
  It does not gain privileged semantic status.
- A local editable workspace is a draft source, not a reproducible evaluation input.
  It becomes one only after the selected Revision Store creates an immutable snapshot.

## 5. Risks and controls

| Risk | Control |
|---|---|
| Generic tokens hide comparability assumptions | Treat tokens as opaque outside their owning store; use content identity for cross-store equality. |
| Multi-file reads become inconsistent | Require one immutable snapshot boundary for every reproducible closure. |
| Non-Git mutation falls back to last-writer-wins | Require compare-and-set or an explicit merge policy. |
| Federation accidentally trusts arbitrary URLs | Configure trust per adapter/source identity and verify the pinned content identity. |
| Legacy schemas silently claim support | Keep v0.1 Git-only limits explicit and introduce versioned successor schemas. |
