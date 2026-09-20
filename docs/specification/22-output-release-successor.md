# Output Expansion and Release Successor Design

**Status:** Proposed  
**Owns:** output-target capability declarations, fidelity diagnostics, and release
acceptance boundary.

## 1. Output contract

Every output adapter consumes a completed Scene and declared target capability profile.
It produces derived bytes plus a manifest containing evaluation identity, target/version,
preserved source metadata, and all capability/fidelity diagnostics. SVG remains the
baseline deterministic adapter; PDF, raster, canvas, and presentation targets are
additive adapters, never alternative semantic stores.

## 2. Capability and fidelity policy

A target declares whether it preserves stable scene/source identity, accessible text,
semantic-role distinction, marker/routing treatment, clipping, selectable text, and
declared fonts/metrics. The coordinator rejects a required absent capability or emits a
machine-readable fidelity-loss diagnostic when the request permits degraded output.
It never silently omit a distinction, re-interpret geometry as semantics, or mutate a
Project to fit a target.

## 3. Release acceptance

A release claims an output target only when it passes its declared capability fixtures,
deterministic-output check, accessible alternative check where required, and mapped
UC-01–UC-15 acceptance cases. The acceptance manifest records exact input closure and
target adapter version. Unsupported use cases are explicitly excluded rather than
implied by SVG success.

### 3.1 Release-acceptance manifest

`release-acceptance-v0.2.schema.yaml` is the canonical exchange contract for this
release boundary.  One manifest names one immutable evaluation identity and one output
target/version.  It MUST enumerate every current-profile use case (`UC-01` through
`UC-15`) exactly once.  Each entry is either:

- `accepted`, with one or more reproducible evidence paths; or
- `excluded`, with a concrete reason and an owning unblocking milestone.

An exclusion is a truthful statement of non-delivery, never passing acceptance
evidence.  Consequently, M9 can be marked complete only when no entry is excluded:
the roadmap's M9 exit requires acceptance coverage for all current-profile use cases.
The manifest's `inputClosure` binds the Project, revision, package closure, View,
Actual set, and Scene identities used as the release input.  An adapter MUST emit the
same evaluation identity and target/version in its output manifest; release packaging
rejects a mismatch rather than attaching evidence from a different evaluation.

### 3.2 Release package

`release-package-v0.2.schema.yaml` defines the publishable package boundary. It binds
the output-manifest identity, artifact content identity, and acceptance-manifest
identity to the same release ID, evaluation identity, target, and target version. A
package is `published` only when every use case is accepted and it contains an artifact
identity. A `blocked` package is review metadata, not an artifact release: it names the
same attempted closure and explicit blocking diagnostics but cannot be presented as a
published target. This prevents a successful renderer invocation from being packaged
with evidence for another evaluation or from concealing an excluded use case.

### 3.3 M13 cross-successor acceptance

M13 adds a versioned successor manifest that binds immutable DateTime, capacity,
collaboration, extension, and output closures. It enumerates UC-16 through UC-21 once;
each must be accepted with reproducible evidence. Missing, duplicate, or excluded rows
block publication and never broaden a Date-only/current-profile release claim.
`successor-release-acceptance-v0.3.schema.yaml` fixes the five closure versions at
`v0.2`, and the fixture validator verifies that every referenced evidence path exists.
