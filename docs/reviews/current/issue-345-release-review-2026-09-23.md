# #345 Portable Visual Capabilities Release Review

**Decision:** accepted for the initial `chrona-output/visual/v0.6` profile.

## Delivered scope

- Closed renderer-neutral `LinearGradient`, `DropShadow`, and `StrokeFinish`
  Scene values, resolved only from Theme/Scheme bindings.
- Exact Context profiles: baseline is unchanged; v0.6 is admitted only for
  SVG, PNG, and PDF; required unsupported treatment rejects before an adapter.
- Deterministic SVG definitions and SVG-derived PNG/PDF characterization.
- A public Controller Z Elevated direction, produced by the materializer from
  the same Project, Actual, View, and ordinary resources as Executive.  Its
  visual treatment is decorative group containment; labels, source metadata,
  and table structure remain the accessibility authority.

Rectangular clipping is deliberately deferred by the published design
correction: present Layout has no typed containment/group placement that can
own its geometry.  No raw target syntax, asset, package acquisition, generic
filter, or renderer-local fallback was introduced.

## Release evidence

- Focused materializer/gallery/adapter checks: `30 passed`.
- Full parallel suite: `486 passed, 9 skipped`.
- Conformance, traceability, reachability, primitive-delivery, View-dispatch,
  and import-direction checks: pass.
- Public materializer: all 10 declared corpus slides reproduce.
- Wheel build and installed-wheel smoke: pass.

The acceptance run initially found that applying a gradient to marks carrying
inside labels made the solid-colour contrast predicate inapplicable.  The
fixture was corrected to apply its decorative treatment to group decoration;
the rerun passed without weakening the accessibility gate.
