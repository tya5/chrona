# I310 Design Correction: Identity-Safe Inside-Label Obstacles

## Trigger

The standalone `inside` placement routine correctly checks that text fits its
anchor.  In the composed Surface, however, the generic collision pass adds
every mark to the obstacle set, including the label's own host mark.  An
inside candidate therefore necessarily intersects an obstacle and cannot be
selected, even when it fits.

## Corrected design

Layout represents collision obstacles with placement identity as well as
geometry.  A plot-label request names its host-mark placement identity.  When
evaluating its `inside` candidate, Layout excludes only that exact host
obstacle.  It keeps every other mark and every already-placed required text
as an obstacle.  All non-`inside` candidates use the complete obstacle set.

This is not a global relaxation of mark/text collision checking: two marks
with equal geometry but distinct identities still block one another.  The
exemption is therefore identity-safe and limited to the geometric relationship
that defines an inside label.

## Architecture review

The correction is wholly within Layout's completed-placement responsibility.
View continues to request a finite side ladder; Scene receives only the
selected rung; Theme/Scheme still own ink contrast; renderers receive no
collision policy.  A typed obstacle record replaces an ambiguous bare
rectangle at the Layout boundary, preserving both deterministic placement and
the existing quality invariant for unrelated geometry.

## Implementation amendment

Add a renderer-neutral typed Layout obstacle record and an optional host-mark
identity on plot-label requests.  Update the shared label placer and the
Surface composer to apply the exact exemption only for `inside`.  Cover a
successful composed inside label, a colliding distinct mark rejection or
fallback, and preservation of ordinary outside-label collision behaviour.
