# Design Plan — Progressive Tutorial Boundary Correction (#378 I378-3)

## Finding

The published onboarding design calls every rung-3 concept an incremental
Project fixture. This does not match the product boundary: an immutable
snapshot is a `snapshot-ref` supplied by Render Context `inputs.snapshot`,
and an extension is a Project-declared pinned profile package that must be
present in the same immutable closure. A Draft Project snippet cannot by
itself demonstrate either mechanism. Treating a successful generic Draft
render as proof would hide the actual contract.

## Design work

1. Reclassify each tutorial concept by its owning source and executable
   command: independent small Draft Project/Actual fixtures for Project
   authoring concepts; explicit immutable corpus materialization for snapshot
   and profile-package closure concepts.
2. Review the correction against Project v0.7, Actual Set, Render Context,
   snapshot-ref, extension package, Draft/immutable ingress, and the existing
   #378 onboarding acceptance design. Preserve the intended learning order
   and avoid duplicating large corpus sources.
3. Publish the corrected design and architecture review before implementing
   tutorial fixtures or commands. Then publish a sliced implementation plan
   with executable checks and a literal acceptance matrix.

No new grammar or rendering semantics are authorized by this plan.
