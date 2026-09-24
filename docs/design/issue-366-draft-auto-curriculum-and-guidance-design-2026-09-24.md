# Issue 366: Draft auto curriculum and guidance design

## Architecture decision

The public 30-row example is a Draft curriculum input, not corpus evidence.
It is a declared YAML Project placed below `examples/controller-z/curriculum/`
and is invoked with the existing Controller Z View, Theme, Scheme, Layout, and
optional Actual input.  It therefore teaches the public Draft ingress without
creating an unmaterialized Context or SVG artifact.

The render use case owns caller-specific remediation prose because it is the
only layer that knows whether the finite viewport came from a Draft request or
an immutable Context.  Layout continues to own measurements and extent facts.
For Draft it suggests `--viewport`; for Context it suggests changing
`environment.viewport.blockSize` and rematerializing the Context.  Scene and
renderers receive neither policy.

`E_LAYOUT_DRAFT_AUTO_UNSUPPORTED` is a Layout diagnostic with detail
`surface=<name>`.  The use case does not invent a surface fallback.

The View contract correction removed all of `layoutIntent`: `compactness` and
the also-inert `itemStacking`.  Records must state that migration fact plainly.

## Whole-architecture review

| Owner | Responsibility after this change |
| --- | --- |
| Curriculum/README/CLI help | Discoverability and runnable Draft command |
| Draft ingress | Typed `WIDTHxauto` request |
| Layout | Finite content extent and unsupported-surface diagnostic facts |
| Render use case | Caller-correct remediation language |
| Context | Fixed finite evidence viewport |
| Scene/renderer | Completed placements and supplied finite viewport only |

This preserves the Context/Scene/renderer boundaries established by #365 and
does not add compatibility syntax.
