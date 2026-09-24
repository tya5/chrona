# Issue 366: Draft auto curriculum and caller-correct guidance design plan

## Trigger

Post-hoc review of Issue 365 verified its implementation and identified five
learnability/diagnostic residuals.  Issue 364 needs no follow-up.

## Decisions to validate

1. Publish a directly runnable, committed 30-row Draft Project fixture under
   `examples/controller-z/curriculum/`; it reuses Controller Z's declared View,
   Theme, Scheme, and Layout, but is not a materialized corpus slide.
2. Make `WIDTHxauto` discoverable in both render command help and README, with
   the 30-row command as the executable example.
3. Keep the Layout numeric fact model shared, but select the remediation text
   at the caller boundary: Draft names `--viewport`; immutable Context names
   `environment.viewport.blockSize`.
4. Give `E_LAYOUT_DRAFT_AUTO_UNSUPPORTED` a stable detail containing the
   unsupported surface name.
5. Correct all #365 release/design records to say that the complete inert
   `layoutIntent` object, including `itemStacking`, was removed.

## Constraints

The fixture must be regular authoring input accepted by the public `chrona
render` command.  It must not become undeclared materializer evidence or
extend immutable Context syntax.  Auto sizing remains Layout-owned and Draft
only.

## Next

Publish the design and architecture review, then make an implementation plan
with isolated documentation/fixture, diagnostic, and verification slices.
