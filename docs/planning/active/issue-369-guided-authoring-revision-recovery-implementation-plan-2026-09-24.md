# Issue 369 implementation plan

## I369-1 — Workspace revision and authoring result contract

- Add the read-only `chrona workspace revision WORKSPACE` command.
- Define the versioned authoring-command-result schema and emit
  `commandBaseRevision`, `workspaceRevision`, and `resultRevision`.
- Emit `E_AUTHORING_BASE_REVISION` with expected/received revision fields and
  an actionable detail.
- Add unit and CLI tests for first-command discovery, stale identity, Unicode
  content, result-field meaning, and no mutation by revision inspection.

Acceptance: a fresh workspace can be edited on the first command, stale state
is unambiguous, and generic Store command behavior is unchanged.

## I369-2 — Store scaffold and materializer recovery

- Make `init` emit the copied Context Store identity exactly and initialize the
  referenced immutable snapshot closure.
- Add an initialized-project Store-reference resolution test.
- Introduce a typed materializer mismatch failure and map it at the CLI boundary
  to guidance that preserves the explicit `--write` gate.
- Test unchanged evidence, mismatch without write, and intended refresh with
  write.

Acceptance: fresh initialization resolves its Contexts, and evidence remains
immutable until a caller explicitly writes reviewed output.

## I369-3 — Public contract and release gate

- Amend Specifications 10 and 51 to distinguish Store revisions from the
  workspace equivalent precondition; leave Specification 35's v0.2 Store rule
  intact.
- Add a concise guided-authoring recovery guide with revision/read/command/
  chain examples.
- Run focused tests, full pytest, public materializer checks, design/structure
  review, and CI. Publish the release review, close #369, then close completed
  #366 and #367 with their published evidence.

Acceptance: documentation names the public recovery loop and no stale Issue is
left open after the verified release gate.
