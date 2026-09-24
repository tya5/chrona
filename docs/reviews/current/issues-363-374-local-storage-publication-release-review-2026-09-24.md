# Issues #363 and #374 — Local Storage and Publication Release Review

**Decision:** Accept and close

## Requirement audit

| Requirement | Evidence | Result |
| --- | --- | --- |
| One safe transactional-store layout | `LocalTransactionalStore` writes and restart-reads only through `snapshot_directory()`; focused tests cover normal writes, parents, baseline-style, percent-containing, and reserved tokens. | Pass |
| No compatibility reader | A raw pre-codec directory is rejected without fallback; the local-store compatibility guide requires re-creation/re-capture. | Pass |
| Opaque revision preservation | `tip.json` keeps the opaque token and returned revisions remain `local:<token>`; no schema or Context change was made. | Pass |
| Publication ownership | Baseline and CLI result writers use `storage.publication.publish_exclusive`; focused tests prove first write, duplicate rejection, and cleanup after replacement failure. | Pass |
| Honest visibility contract | The shared helper documents the bounded final-name reservation interval and immutable-reader/command-output rules. | Pass |
| Windows lock actionability | Simulated Windows contention returns `E_AUTHORING_LOCK_TIMEOUT` with workspace/lock detail; unrelated I/O errors remain errors; use-case results preserve separate `code` and `detail`. | Pass |
| Architectural direction | `check_import_direction.py` reports 9 packages, 33 edges, all inward after removing the accidental usecase-to-operational dependency. | Pass |
| Presentation isolation | No Project, Context, scheduling, Layout, Scene, renderer, or materializer policy file changed. Public materializer byte checks passed for every declared slide. | Pass |

## Verification evidence

- Focused storage, authoring/use-case, and CLI verification: 82 passing tests
  for codec/publication plus 59 passing tests for lock/result propagation after
  the final boundary correction.
- Conformance, module reachability, Scene delivery, View dispatch, import
  direction, text encoding, diagnostic inventory, declared-value inventory,
  documented-command, and init-template checks passed locally.
- Built primary wheel: `chrona-0.1.0a0-py3-none-any.whl`, 2,372,769 bytes;
  forced installed-wheel smoke passed outside the checkout.
- All declared public materializer slides passed byte reproduction in one
  consolidated batch; no generated SVG was changed.
- GitHub Actions [run 36006322361](https://github.com/tya5/chrona/actions/runs/36006322361)
  passed Ubuntu, macOS, and Windows, including conformance, full parallel
  pytest, wheel build/install, and isolated smoke.

## Migration and compatibility decision

Pre-codec local stores are intentionally not readable.  The release adds no
silent migration or dual reader: users re-create the local store or re-capture
the immutable resource.  This is a pre-release, documented storage-layout
break that protects one unambiguous portable filesystem representation.

## Review conclusion

The completed work centralizes local path and publication mechanics below the
application boundary.  It improves Windows failure actionability without
letting platform details cross into use cases or the presentation pipeline.
No design deviation remains after moving hand-authored guidance out of the
generated CLI reference and removing the reverse import discovered by the
structural gate.
