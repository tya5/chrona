# Issue #54 opt-in example-closure correction design plan

## Status

The prior strict-example proposal is withdrawn before implementation. It would make
canonical examples silently stricter than the #44 resource-reference contract and force
authors to add hashes merely to use the documented materializer.

## Authoritative decision

Examples use the same opt-in content-identity semantics as every ordinary render context.
A missing `contentIdentity` is valid. When a pin is supplied, the materializer and reader
verify it against the exact copied bytes; they never recompute, rewrite, or remove it.

## Design completion sequence

1. Reconcile #44, Revision Store, Closure Resolver, materializer, and font metrics under one
   optional-pin rule.
2. Define the materializer invocation policy: it must not unconditionally select the CLI's
   strict-identity mode.
3. Define diagnostics for supplied wrong resource/font pins, while preserving normal
   resolution diagnostics for an unpinned optional asset.
4. Define evidence rules: generated SVGs remain byte-reproducible from unpinned canonical
   examples; a separately pinned fixture proves supplied-pin rejection.
5. Review boundaries and publish an implementation plan.

## Acceptance

- All five unpinned canonical contexts materialize in check mode without `--write`.
- An added wrong resource pin fails with `E_CONTENT_IDENTITY` in check and write modes.
- An added wrong font pin fails with `E_MATERIALIZER_FONT_IDENTITY`.
- Context bytes remain unchanged in the copied closure.
- No generated SVG changes.
