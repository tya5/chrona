# Design Plan: Portable Visual Capabilities (#345)

**Status:** Active — design planning
**Issue:** #345
**Depends on:** Specifications 07, 08, 12, 34, 46, 55, and 62

## Objective

Admit a bounded renderer-neutral visual vocabulary that gives reusable
presentations visibly richer treatments without turning SVG syntax, a renderer,
or a package into authoring authority. The first release must demonstrate the
complete chain from Theme/Scheme intent to completed Scene capability to target
serialization and deterministic rejection.

## Verified starting point

- `ScenePaint` is already completed from the resolved Theme/Scheme boundary;
  SVG v0.5 serializes solid fill/stroke/dash/opacity only.
- Existing Scene geometry is deliberately closed to Rect, Symbol, Path, and
  pre-measured Text. PNG/PDF serialize the SVG Scene; Typst/TikZ are distinct
  adapters. Canvas and PPTX are not current Chrona adapters.
- Context target capabilities are explicit but unversioned feature strings.
  The renderer registry treats them as output requirements, not as a visual
  profile with limits.
- Color Scheme is the sole concrete-color authority. No accepted asset closure
  or package acquisition consumer exists yet.

## Admission decision

The first portable visual profile admits only capabilities with a concrete
gallery use case and an implementable current SVG/PNG/PDF path:

| Family | Admit in v0.6 | Reason |
| --- | --- | --- |
| Paint | `paint.linear-gradient` | expressive surface differentiation using existing Scheme-bound colors |
| Effect | `effect.drop-shadow` | bounded elevation without geometry or semantics changes |
| Composition | `clip.rect` | deterministic viewport/card containment |
| Stroke | `stroke.line-cap`, `stroke.line-join` | portable finishing of existing Paths |
| Metadata | existing link/source/accessibility metadata | retain existing contract; no new interaction behavior |

The profile explicitly defers radial gradient, arbitrary pattern, Image,
Ellipse, transform, path clip, mask, blend mode, glow, blur, arbitrary filter
graph, text-on-path, animation, scripting, foreignObject, raw CSS/XML, and
network assets. An ellipse can currently be represented by a completed Path;
Image awaits a closed asset/store contract; remaining effects lack a target
fidelity contract. No deferred item may be emulated with SVG escape hatches.

## Required design work

1. Define versioned portable capability IDs, parameter limits, profile identity,
   required/optional fidelity, and stable diagnostics.
2. Extend completed Scene paint/effect/clip values compositionally; preserve the
   current small geometry set and pre-measured text boundary.
3. Define Theme token/role binding for gradient stops and shadow colors using
   only existing Color Scheme intents; prohibit literals and renderer syntax.
4. Define target negotiation before serialization. SVG/PNG/PDF v0.6 support
   the admitted profile; Typst/TikZ reject required uses. Optional omission is
   a resolved Scene policy, never adapter discretion.
5. Define capability-specific accessibility and complexity invariants.
6. Amend Design Space and Package specifications with capability declarations
   as a deferred package contract, not a new resolver.
7. Add use-case/traceability, representative Scene fixtures, SVG/PNG/PDF
   characterization, and negative capability tests.

## Planned design and implementation sequence

| Stage | Scope | Acceptance |
| --- | --- | --- |
| D345-1 | Capability/profile/fidelity/diagnostic and ownership design | no raw-SVG or color-authority leak; review accepted |
| D345-2 | Scene compositional contract and Theme/Scheme binding design | layout/Scene/renderer seam and limits are closed |
| D345-3 | Whole-architecture review and traceability | current/future target distinction and deferred families are explicit |
| I345-1 | Schema/typed capability profile and Scene data closure | invalid literals, limits, and unsupported requirements fail before rendering |
| I345-2 | Theme resolution and Scene projection | gradients/shadows/clips/stroke finish are completed Scene data only |
| I345-3 | SVG adapter plus PNG/PDF characterization | adapters serialize or reject; no Theme/geometry/policy imports |
| I345-4 | Gallery fixture and release gates | public materializer, full suite, conformance, SVG diff, wheel, CI |

## Design-deviation rule

Adding a geometry kind, an asset reference, an optional fallback, an effect not
listed above, or a target adapter requires returning to D345-1 through D345-3
and publishing the correction before implementation resumes.
