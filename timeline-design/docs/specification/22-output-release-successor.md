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
