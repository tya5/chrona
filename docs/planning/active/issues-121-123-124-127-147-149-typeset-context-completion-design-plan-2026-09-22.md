# Typeset Context Completion Design Plan

## Trigger

P6 implementation inspection found that D6 requires an exact typesetter
identity and positioned source, but does not specify the valid identity when a
draft is made, the Scene-to-typeset coordinate contract, or the placement of
the `textMode` policy.  These are Context semantics, not adapter internals.

## Scope

Complete D6 before renderer implementation by defining the next Render Context
contract, its draft ingress behavior, and the source coordinate/evidence
boundary.  No renderer, CLI, or schema implementation is included in this
planning publication.

## Completion criteria

The correction must name each target engine and grammar, prohibit an unknown
or unavailable identity in a valid Context, define deterministic coordinates
and font-identity representation, and show that the result preserves the
existing Layout -> Scene -> renderer and immutable-closure boundaries.
