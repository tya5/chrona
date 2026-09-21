# M27 Presentation Product-Path Design Closure Review — 2026-09-21

**Decision:** D27-1 through D27-5 are complete. M27 implementation planning is
authorized; implementation itself is authorized only by its subsequently published
implementation plan.

## Cross-boundary result

| Boundary | Review conclusion |
|---|---|
| Project / Schedule / Actual | Read-only semantic inputs. M27 restores their presentation; it neither changes scheduling nor synthesizes Actual facts. |
| View / Style / Detail / Summary | Select visible facts, wording, comparison facets, and optional families. No Scene or renderer is permitted to infer them. |
| Theme / Color Scheme | Resolve all decorative values before Scene construction. Color Scheme remains color-only. |
| Layout | Is the sole geometry-authoring owner and emits the consumed Layout Manifest. M27 does not restore the superseded layout grammar. |
| Scene | Is the only owner of complete primitive families, measurement, ports, routes, bounds, and source/role metadata. |
| SVG / CLI | The CLI invokes one completed SceneSurface path; the SVG adapter serializes and validates it without defaults or policy recovery. |
| Examples / CI | A generic materializer drives the public CLI from manifest-declared immutable input closure and checks canonical output. |

## Design completeness findings

1. The required vocabulary already has normative owners in Specifications 08, 24, 25,
   26, 28, 30, and 33. Specification 36 makes the product binding explicit; no new
   authoring resource or schema is justified.
2. ADR-0028 removes the unresolved serializer choice. `SceneSurface` is the single
   public SVG input. A reduced review compositor is an implementation migration detail,
   not a selectable product behavior.
3. The #30 and #31 defects are policy violations, not isolated formatting bugs: axis
   labels and missing cells must be normalized/measured before Scene serialization.
4. The #29/#33 regression is observable through required primitive families and
   artifact reproduction, so new CI evidence can reject both a missing family and a
   stale expected SVG.
5. No external compatibility claim constrains M27. Old expected SVG bytes are replaced
   only through the declared generic materializer after A27 evidence accepts the new
   semantic output.

## Design conformance checklist

- One Context→ResolvedPresentationInput→Layout Manifest→SceneSurface→SVG route: yes.
- No example/ID/host-state branch: yes by ADR and Specification 36.
- No renderer-owned display policy: yes by ADR-0028 and Specifications 08/24/36.
- Every optional slot family complete-or-diagnose: yes.
- Reproducible CLI-driven example evidence and final full regression gate: specified.
- No unresolved authority, schema, migration, or output-target decision: confirmed.

## Implementation guardrails

Implementation must first add executable evidence for the completed Scene boundary,
then migrate generic composition family-by-family. It must not make a visual-only
example change, regenerate artifacts, or close issues before the relevant A27 proof
passes. Discovery of a missing declared resource field or a required new target reopens
D27-3/D27-4 before code proceeds.
