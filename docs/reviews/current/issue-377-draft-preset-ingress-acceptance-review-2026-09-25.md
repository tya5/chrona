# Acceptance Review: Draft preset ingress and packaged default (#377)

**Decision:** Accept for release.

## Delivered boundary

`chrona render` accepts a named `presentation-preset` and resolves its four
ordinary members before constructing the existing typed Draft closure.  An
explicit member path takes precedence over the corresponding preset member.
The resolver accepts paths only beneath the explicit preset root and validates
each declared member identity; it does not discover a repository or introduce
an alternate render pipeline.

When neither a preset nor an explicit member is supplied, the CLI reads the
wheel-owned `chrona-default-draft` preset.  Its View is project-generic: it
selects spans and points, derives its window from selected planned dates, and
does not contain a project object ID, domain field, calendar, or date literal.
Actuals remain optional.

The bundled HALCYON Theme, Scheme, and Layout remain appearance/composition
resources.  Their use by the default does not make HALCYON semantic data part
of a user's Draft closure.

## Architecture and safety review

| Concern | Evidence | Result |
| --- | --- | --- |
| Authority | Preset ingress resolves ordinary resources then uses `resolve_draft_render`; it does not create a Context or snapshot. | Pass |
| Path containment | `_declared_child` resolves every declared member beneath a caller-supplied root; no parent traversal or repository fallback is admitted. | Pass |
| Precedence | Resolver tests compare preset closure identities to explicit members; CLI flags remain higher priority. | Pass |
| Packaging | `importlib.resources` owns the default resource lookup; the wheel contains the preset and generic View exactly once. | Pass |
| Scope | The existing large `init` corpus is not silently shrunk or fitted.  Its minimal-first-render successor remains #376. | Pass |

## Verification

* Focused preset, CLI, and public-preset tests: `56 passed`.
* Full regression: `777 passed, 19 skipped`.
* `python conformance/run_conformance.py`: pass.
* Import direction, module reachability, Scene delivery, diagnostic inventory,
  declared-value inventory, and executable documented-command checks: pass.
* Wheel build and size check: pass (`2,510,125 < 5,000,000` bytes).
* Installed-wheel smoke: a fresh virtual environment installed the wheel, then
  rendered a checkout-external Draft with no presentation flags; the SVG was
  non-empty.  The package resource and generic View were both resolved from
  `site-packages`.

The default is intentionally a Draft convenience, not reproducible evidence;
immutable Context rendering and guided workspace rendering remain unchanged.
