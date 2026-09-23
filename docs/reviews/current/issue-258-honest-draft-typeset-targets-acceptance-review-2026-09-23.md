# Issue #258 Honest Draft Typeset Targets Acceptance Review

**Status:** Accepted  
**Date:** 2026-09-23  
**Design:** [#258 design](issue-258-honest-draft-typeset-targets-design-2026-09-23.md)  
**Implementation plan:** [#258 implementation plan](../../planning/active/issue-258-honest-draft-typeset-targets-implementation-plan-2026-09-23.md)

## Delivered behavior

`chrona render` and `chrona render-workspace` retain every advertised target.
Their Typst/TikZ route now requires explicit `--typesetter-engine`,
`--typesetter-version`, and `--typesetter-adapter-grammar` switches.  The
common Draft closure receives a typed `TypesetterIdentity`; it no longer runs
an executable or derives an identity from the host.  Missing, partial, or
non-typeset descriptor input fails deterministically as
`E_RENDER_TYPESETTER_DESCRIPTOR`; complete but target-incompatible descriptors
continue through the Render Context v0.8 schema boundary.

Explicit and guided Draft ingress share this behavior.  Immutable Context
rendering is unchanged: its descriptor remains pinned in the Context and never
uses these Draft switches.

## Acceptance evidence

| Gate | Result |
| --- | --- |
| Focused Draft closure, target registry, and CLI tests | `39 passed` |
| Full test suite | `457 passed, 7 skipped` |
| Schema and architecture conformance | pass |
| All eight public materializers | byte-identical; generated SVG diff empty |
| Built-wheel isolated smoke | pass |

The structural closure test proves that the Draft closure module contains
neither executable probing nor `--version` invocation.  The CLI test proves an
explicit Typst Draft source can be rendered without depending on an installed
Typst executable; guided ingress records an equally explicit TikZ descriptor.

## Scope review

The change does not add a Context version, persisted descriptor resource,
typesetter compilation, native reflow, target-local geometry, fallback target,
or compatibility branch.  It preserves the existing Layout → Scene → adapter
boundary and makes help-advertised Draft reachability honest.
