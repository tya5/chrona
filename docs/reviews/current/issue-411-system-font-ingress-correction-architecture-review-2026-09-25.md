# Architecture Review — System-Font Ingress Correction (#411)

**Decision:** accepted.

The `--system-fonts` correction removes a duplicate family/weight authority:
Theme selects faces, while the command only grants volatile host discovery.
That is consistent with the presentation architecture, where Theme supplies
typography intent and Layout consumes an exact metrics model.

`DraftFontResolution` is correctly an ingress/runtime value rather than a
resource contract.  It may cross from draft ingress to Layout measurement and
the restricted PNG handoff, but never into Context, Store, Scene, or adapter
policy.  Thus Layout still owns geometry, Scene remains a completed-placement
projection, and SVG/PNG adapters do not discover or choose fonts.

The review accepts continuing `skip_system_fonts=True`: resvg receives the
one exact file that Layout measured, not permission to select an unrelated
host fallback.  It also accepts the narrower first release surface (draft CLI
SVG/PNG only).  Rejecting PDF/typeset and every immutable workflow is clearer
than implicitly widening font embedding or evidence provenance.

Required implementation tests are: absent opt-in retains declared metrics;
the flag derives every requested face from Theme; a fake resolver proves exact
metadata and byte identity reach Layout/PNG; Context and Scene serializations
contain neither host path nor resolution state; and immutable/PDF/typeset
requests carrying such state fail with `E_FONT_SYSTEM_IMMUTABLE`.
