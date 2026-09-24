# Issue 369 design plan

## Problem statement

Guided authoring applies a workspace-local content identity as its optimistic
concurrency precondition, but exposes neither a way to obtain that identity nor
a result/diagnostic vocabulary that distinguishes it from a general Revision
Store token. A newly initialized project also writes a Store identity that does
not resolve its copied Contexts. Finally, expected materializer drift has no
caller-facing recovery guidance.

## Scope and sequencing

1. Inventory the authoring command, CLI, result/diagnostic conventions, command
   specifications, `init` template, Store reference resolution, and
   materializer failure boundary.
2. Define a workspace-specific revision inspection command and a typed result
   vocabulary that never presents the actual workspace revision as an echo of
   the supplied command precondition.
3. Define the mismatch diagnostic, its expected/received identities, and the
   exact distinction between a workspace content identity and a Revision Store
   token. Amend the relevant specifications and user guide.
4. Define one initialization invariant: `init` emits the immutable snapshot
   closure referenced by every copied Context and a Store identity that resolves
   it. Define the
   materializer mismatch remediation without weakening byte verification.
5. Review the design against the command, operational-store, progressive
   authoring, materialization, and application-boundary architecture. Publish
   the design and the review before implementation.
6. Publish an implementation plan with independently reviewable slices for the
   public CLI/contract, local Store scaffold, documentation, and verification.

## Required evidence

- A fresh guided workspace yields its revision through a public, read-only CLI
  operation; using it permits the first command without reverse engineering a
  JSON codec.
- A stale command result names both the workspace revision expected by the
  writer and the command revision received by it.
- General immutable Store commands retain opaque Store-token semantics.
- A freshly initialized project has a Store configuration whose identity
  resolves its copied Context references.
- Materializer drift remains a failure without `--write`, but its failure tells
  an author how to refresh declared generated evidence.
- Focused CLI/use-case/Store/materializer tests, full pytest, public
  materializer checks, architecture review, and CI pass before closure.
