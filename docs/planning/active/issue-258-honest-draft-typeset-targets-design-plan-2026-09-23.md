# Issue #258 Honest Draft Typeset Targets Design Plan

## Trigger and published facts

`chrona render` and `chrona render-workspace` advertise `typst` and `tikz`,
but current Draft closure construction probes a host executable to manufacture
their typesetter descriptor.  On a host without that executable the advertised
route rejects with `E_RENDER_TYPESETTER_UNAVAILABLE`.  Immutable Render Context
v0.8 already requires an exact, author-declared typesetter identity for those
targets and remains reproducible without host probing.

## Design objective

Close #258 without a second renderer, hidden host discovery, or a weaker
Context contract.  Establish one explicit Draft target policy, diagnostics, and
help contract for both explicit and guided Draft ingress.  Immutable Context
rendering is out of scope except for regression protection.

## Design work

1. Inventory target declarations in the two Draft CLIs, Draft closure factory,
   typed Render Context contract, and renderer registry.  Record which facts
   are target policy versus renderer implementation.
2. Compare the two admissible Issue outcomes: omit typeset targets from Draft
   help, or retain them only with a complete explicit deterministic descriptor.
   Select the option that preserves the v0.8 Context identity invariant and
   avoids host inference.
3. Define the descriptor ownership, required fields, target-to-engine and
   grammar invariants, missing/invalid diagnostics, and parser/help behavior.
   Ensure the same typed descriptor reaches both explicit and guided Draft
   closure construction.
4. Review the result against Specifications 08, 09, 13, 51 and the completed
   #149 typeset-context design: Layout remains geometry authority, Scene remains
   primitive projection, adapters remain serializers, and Draft remains
   non-evidence.
5. Publish the accepted contract and architecture review before writing an
   implementation plan.

## Completion criteria

The design names one explicit Draft behavior for every advertised target; says
whether an unavailable host binary is relevant; defines exact user-facing
diagnostics; preserves immutable Context closure unchanged; and identifies
focused CLI, closure, renderer, and regression evidence for implementation.
