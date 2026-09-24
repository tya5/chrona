# Issues #363 and #374 — Local Storage and Publication Architecture Review

**Decision:** Accepted for implementation planning

## Scope

This review evaluates the local-storage and authoring-publication design
against Chrona's existing immutable-reference and application boundaries.

## Responsibility alignment

| Boundary | Decision | Review result |
| --- | --- | --- |
| Revision identity | `local:<token>` remains opaque and unchanged; encoding occurs only when deriving a local path. | Pass — filesystem safety cannot leak into semantic identity. |
| Storage adapter | `LocalTransactionalStore`, reader, materializer, and Actual storage share `snapshot_directory()`. | Pass — one local path authority, no raw-token branch. |
| Migration | Pre-codec raw stores are explicitly unsupported and re-created; no fallback reader exists. | Pass — avoids ambiguous persistence authority and unjustified compatibility. |
| Publication | One low-level helper preserves exclusive ownership and states its bounded reservation window. | Pass — no false cross-platform atomicity claim or duplicated writer protocol. |
| Authoring operation | The aggregate lock translates only Windows contention into a named result diagnostic. | Pass — platform mechanics stay below use cases while users receive retry guidance. |
| CLI/result boundary | Automation results remain post-command artifacts; immutable baseline readers verify content identity. | Pass — the documented window does not create a second streaming contract. |
| Presentation pipeline | No Project, Context, Layout, Scene, renderer, or materializer policy changes. | Pass — storage remediation stays outside presentation authority. |

## Rejected alternatives

- **Dual raw/encoded lookup:** would make path encoding a compatibility policy
  at every reader and obscure which bytes are authoritative.
- **Silent migration:** changes local storage state without a user-controlled
  capture/recreation event and provides no durable provenance.
- **Hidden temporary then ordinary rename:** removes the empty-file window only
  by reopening the no-overwrite race.
- **Platform-specific rename as the common contract:** would make portability
  depend on unproven filesystem semantics and diverge from the supported Python
  baseline.
- **Raw `OSError` from the Windows lock:** exposes adapter details and leaves an
  author unable to identify the workspace to retry.

## Conditions for implementation

The implementation plan must retain one shared publication helper, expose
`E_AUTHORING_LOCK_TIMEOUT` as a structured authoring-command diagnostic, and
include raw-layout rejection plus Windows-adapter tests.  It must document the
pre-codec break and reservation visibility in user-facing storage guidance.

No unresolved ownership, migration, or presentation-boundary issue remains.
