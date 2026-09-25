# Acceptance Review: Closed presentation capability ceiling (#391)

**Decision:** Accept pending CI.

## Delivered boundary

`presentation.scene.capabilities` is the single typed ceiling for current,
deferred, and deliberately rejected renderer-neutral presentation capability
decisions. Each row states a primitive family, disposition, owning layer,
reason, and design reference. Visual profiles consume admitted IDs from that
registry; target adapters do not import it and cannot select a capability.

The ceiling deliberately does not add a raw `substitute` Theme or Scene enum.
Current rich paint is decorative and has no finite semantic alternative. The
substitution guard rejects every unowned request before adapter work. A future
substitution requires a capability-specific semantic encoding, finite primary
and alternative completion, profile predicate, and pre-adapter resolver in one
design-approved slice.

The generated prior-art matrix is linked from Specification 63 and exposes the
same closed rows as review evidence. It cannot add a runtime capability.

## Architecture review

| Concern | Result |
| --- | --- |
| View / Layout / Theme / Scheme | Occurrence, geometry, treatment, and colour authority remain separate. |
| Scene / adapter | Scene completes data; adapters serialize completed data and do not choose fallback. |
| Fidelity | Required and decorative-optional rich treatment behavior is unchanged. |
| Assets | Icons remain the finite, catalog-owned Specification 64 asset family. |
| Migration | No compatibility alias or target-shaped Scene vocabulary was introduced. |

## Verification

* Capability registry, visual profile, paint, matrix, and Scene delivery
  focused tests: pass.
* Public materializer byte checks: `24 passed`; generated SVG and gallery diffs
  are empty.
* Conformance, import direction, reachability, generated-document, wheel-size,
  and installed-wheel smoke checks: pass.
* Full regression: `780 passed, 19 skipped`.

No renderer-visible policy changes occur in this release; the ceiling makes
future omissions explicit and reviewable without widening the current contract.
