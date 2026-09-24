# Local Storage and Publication Design (#363, #374)

## Decision

Chrona has one local filesystem representation for an immutable revision token:
`snapshot_directory(root, token)`.  `LocalTransactionalStore` will use that
representation for every persisted revision and restart read.  Its externally
visible revision remains `local:<token>`; filesystem encoding is never a
revision or Context concern.

Exclusive baseline and automation-result publication retains the #359
reservation-and-replace protocol.  The protocol guarantees that an existing
destination is not overwritten, but it deliberately does not claim that a
concurrent uncoordinated reader cannot observe the final name during the short
empty reservation interval.  That condition is documented at the shared
writer boundary rather than concealed by a non-portable pseudo-atomic helper.

The Windows authoring lock has an explicit bounded-contention failure.  It is
reported as `E_AUTHORING_LOCK_TIMEOUT` with an actionable detail naming both
the authoring workspace and its lock file.  POSIX retains its intentional
indefinite advisory wait.

## Local transactional snapshot layout

`LocalTransactionalStore` owns a private local sequence and creates the
opaque token `local-<sequence>-<digest-prefix>`.  For a token `t`, it writes:

```text
<root>/tip.json
<root>/revision-<percent-encoded t>/project.json
<root>/revision-<percent-encoded t>/parents.json
```

`tip.json` continues to contain the unencoded token.  On restart the store
loads that token, derives its directory only with `snapshot_directory()`, and
returns `local:<token>`.  This preserves compare-and-set and content-identity
semantics while making device names, colons, percent sequences, and trailing
periods safe at the adapter boundary.

There is no reader for the former `<root>/<raw token>/` layout.  Stores made
before the portable codec are intentionally unsupported and must be re-created
or re-captured.  The user documentation states this explicitly.  A later
diagnostic-quality slice (#371) owns making a resulting `E_STORE_REFERENCE`
describe the resource, expected store identity, and failed reference; it does
not change this migration decision.

## Exclusive publication contract

`LocalBaselineRegistry` and CLI result output share one low-level filesystem
publication helper.  The helper:

1. writes and fsyncs completed candidate bytes under a sibling hidden temporary
   name;
2. claims the final destination using exclusive creation; and
3. replaces that reservation with the completed temporary file, removing both
   temporary and reservation on failure.

The claim is the no-overwrite authority.  On the portable Python/filesystem
baseline there is no single no-replace rename primitive that also works on all
supported platforms.  Moving a hidden candidate with ordinary rename would
allow a competing publisher to be overwritten; replacing the final-name
reservation prevents that race but leaves a bounded interval in which an
uncoordinated reader can see a zero-byte final path.

Consequently the helper documents precisely these guarantees:

- a publication either reports a collision or publishes exactly the candidate
  bytes; it never overwrites a pre-existing completed artifact;
- readers requiring immutable baseline bytes must validate their declared
  content identity and may retry a transient read during concurrent
  publication;
- automation result files are exclusive command outputs, not a live
  concurrently-readable stream; callers consume them after the command exits.

No hard link, platform-specific rename syscall, advisory reader lock, or
hidden dual publication convention is introduced.  A future change may close
the window only by first defining and testing an explicit cross-platform
no-replace primitive; it must not weaken the existing collision guarantee.

## Authoring aggregate lock

The lock remains an operational adapter around the workspace aggregate switch.
It uses a one-byte sibling lock file:

```text
<workspace parent>/.<workspace name>.authoring.lock
```

On POSIX, `flock(LOCK_EX)` waits indefinitely.  On Windows, `msvcrt.LK_LOCK`
has its platform-defined bounded retry.  The Windows adapter catches only the
contention-timeout `OSError` and raises an operational error with the stable
code `E_AUTHORING_LOCK_TIMEOUT` and detail in this form:

```text
timed out acquiring authoring aggregate lock <lock-path> for workspace <workspace-path>; wait for the active authoring command to finish and retry
```

The authoring use case maps that operational error to a rejected
authoring-command result with separate `code` and `detail` fields.  It must not
serialize the exception's combined display string as a diagnostic code.
Unrelated lock-file and filesystem failures retain their existing I/O failure
handling.  Neither lock state nor a platform exception crosses into Project,
Context, scheduling, Layout, Scene, or renderer layers.

## Verification and migration evidence

The implementation must prove:

- transactional write, restart, and parent round trips through encoded
  baseline-style and Windows-reserved tokens;
- a raw pre-codec directory with an otherwise valid `tip.json` is not read;
- documented re-creation guidance is reachable from local-store documentation;
- baseline and CLI output preserve collision rejection and clean reservations
  after success/failure, with the documented visibility contract tested at the
  helper boundary;
- simulated Windows contention produces the stable actionable authoring
  diagnostic, while the lazy imports retain testability on non-Windows hosts;
- all existing materializer and Context evidence continues to use the shared
  codec without a presentation-policy change.

## Non-goals

This design does not migrate old stores, alter revision-token values, add a
public transactional-store command, change Context/schema semantics, or modify
Project, scheduling, Layout, Scene, renderer, or materializer policy.
