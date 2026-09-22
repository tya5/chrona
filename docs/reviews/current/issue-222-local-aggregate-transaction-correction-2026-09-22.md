# Issue 222 Local Aggregate Transaction Correction

## Trigger

The Stage-3 bundle writer can validate and stage local resources, but a direct file
writer is not the required `MaterializePresentationPreset` command transaction.  It
does not carry a base revision through the Authoring Command Use Case and Command
Engine, and therefore cannot reject a stale workspace while treating the workspace and
its new resource bundle as one aggregate.

## Aggregate and ownership

The aggregate is the named authoring workspace file together with the exact local files
named by its Stage-3 `presentation.resources` and `presentation.receipt` references.
The Authoring Command Use Case owns all authoring parsing, normalization, closure
validation, and output proof.  It supplies a closed map of canonical candidate bytes
and the workspace base content identity to the presentation-free Command Engine.  The
Engine owns only path validation, compare-and-set, locking, staging, commit, recovery,
and result revision construction; it must not import authoring or presentation types.

`materializePresentationPreset` is a successor authoring command with no mutable
presentation payload.  Its target identifies the workspace aggregate and its
`baseRevision` is the exact current workspace content identity.  The operation is
one-way: explicit workspaces reject the command.

## Local-file commit protocol

The local adapter is a logical aggregate transaction with these observable states:

1. It validates every relative candidate path, reads the target workspace, and compares
   its canonical content identity with the requested base revision under the aggregate
   writer lock.
2. It writes every candidate byte into a private sibling staging directory.  No
   candidate has yet become visible.
3. It rechecks the workspace identity, publishes the complete new resource directory,
   and switches the workspace file last.  Thus a workspace can never reference absent
   local resources.  A failed proof, invalid candidate, collision, or stale base
   publishes nothing.
4. A durable transaction marker records the candidate identities until the workspace
   switch completes.  Startup/retry recovery either completes the already-staged
   switch or removes an unreferenced staged bundle; it never manufactures a mixed
   guided/explicit workspace.

The workspace switch is the visibility point.  A crash before it may leave only an
unreferenced recoverable bundle; a crash after it leaves a complete explicit closure.
Readers therefore observe either the old guided source or the complete explicit source,
never a workspace whose references are missing.  This is the local adapter's concrete
meaning of the Specification 51 aggregate transaction; it does not claim an impossible
single filesystem rename across unrelated paths.

## Required evidence

The implementation must test stale-base injection immediately before commit, destination
collision, invalid/incomplete candidate, and failed byte proof: each leaves the original
workspace and no published bundle.  An accepted command must yield the complete
canonical resource/receipt set, an explicit workspace with no binding, and byte-identical
SVG from the guided and explicit closures.  CLI, GUI, and AI call the same Authoring
Command Use Case; the CLI is not permitted to call a file writer directly.
