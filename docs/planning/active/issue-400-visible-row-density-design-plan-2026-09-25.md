# Design Plan — Visible Row-Density Policy Completion (#400)

**Status:** planning; do not implement from the earlier axis-only acceptance.

## Public baseline

The accepted axis work closed the invisible-loss portion of #400: every axis
label outcome is recorded and non-fitting labels diagnose or thin with a
record.  #400 remains open for row density and the finite cross-failure
registry.

Current source has two non-policy row rejection sites:

1. `render_review` rejects a fixed-height draft before a Layout manifest is
   composed whenever the P1 timeline requirement exceeds the viewport.
2. `place_rows` unconditionally raises when allocated timeline block extent is
   below the sum of row requirements.

Both bypass the `overflow` declared by the resolved `timeline` slot.  Merely
removing either check is not safe: `place_mark_tracks` then enforces completed
mark containment and rejects `E_LAYOUT_MARK_OVERFLOW`.  A valid solution must
therefore make the degradation geometry explicit, not replace an early error
with clipping or overlap by accident.

## Questions the design must settle

1. Define the finite failure registry and identify its authoritative owner,
   including row requirement, track/mark containment, table ellipsis, relation
   suppression, and the already-completed axis outcomes.
2. Define the only permitted physical encoding for a policy-authorized dense
   row: whether the surface grows, row/track geometry is deterministically
   compacted, or an explicit clipped presentation primitive is needed.  It
   must preserve item identity, ordering, and an observable warning; it may
   not weaken ordinary mark-containment globally.
3. Define draft versus immutable policy resolution.  Draft `WIDTHxauto`
   remains an explicit grow option.  Fixed draft and immutable output must
   consult the same declared timeline-slot policy, with any path-specific
   default represented as a typed Layout input rather than a use-case
   conditional.
4. Define placement/Scene warning transport and the user-visible diagnostic
   surface.  Warnings must name required/available extent, affected rows, and
   selected policy without serializing an adapter-specific workaround.
5. Decide whether the existing `diagnose|ellipsize-with-source|clip-optional`
   vocabulary is sufficient for a geometric mark failure.  If it is not,
   introduce one finite, truthfully named Layout policy rather than assigning
   unrelated text ellipsis semantics to tracks.

## Required design outputs

The design must contain a policy table, typed data-flow diagram, geometry
invariants, draft/immutable resolution matrix, migration impact for current
profiles, diagnostics/warnings, and a test matrix.  The architecture review
must verify the chain Project/View/Profile → Layout → Scene → adapter and
confirm that Scene and adapters do not choose compaction, clipping, or warning
policy.

## Proposed implementation staging

1. Policy/contract migration and registry-only tests.
2. Layout-owned row outcome and physical placement implementation, including
   structural containment/clip invariants and focused warning tests.
3. Render-use-case handoff, Scene projection, profile migration, and corpus
   materializer evidence in one atomic slice.
4. Full suite, conformance, all public materializers, SVG/PNG visual review,
   wheel smoke, three-platform CI, and acceptance review.

No slice may silently loosen `E_LAYOUT_MARK_OVERFLOW`, create an adapter-local
crop, or leave a fixed-height draft preflight that overrides the selected
Layout policy.
