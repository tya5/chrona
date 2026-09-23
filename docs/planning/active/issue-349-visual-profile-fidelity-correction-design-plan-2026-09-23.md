# Design Plan: Visual Profile Fidelity Correction (#349)

**Status:** Active — design planning
**Issue:** #349
**Corrects:** Specification 63 / I345 initial v0.6 delivery
**Blocks:** #350 portable icon catalogs

## Objective

Make every declared visual capability truthful for its exact target route before
an icon catalog depends on the same profile mechanism. A required treatment
must either reach the artifact with declared semantics or reject before any
artifact is written. Deterministic bytes alone are not fidelity evidence.

## Verified findings

- The current generic v0.6 profile declares SVG, PNG, and PDF equally capable.
  The ReportLab/svglib PDF route drops SVG `feDropShadow`; required shadow is
  therefore silently omitted.
- `gradientTransform="rotate(angle)"` in object-bounding-box space does not
  preserve a visible angle on non-square primitives. The Scene contract has no
  coordinate policy for a gradient.
- Specification 63 names value, fidelity, and limit diagnostics which current
  code cannot emit. Its two-to-eight stop contract is also not authorable;
  current Theme bindings construct exactly two stops.
- The draft render route selects baseline unconditionally, preventing an author
  from previewing a required rich treatment, and loses structured capability
  diagnostic path/message evidence at the use-case boundary.

## Design decisions required before implementation

1. Replace the generic rich target admission with exact target profile IDs and
   declared capability subsets. SVG and PNG may admit only the subset proven by
   their concrete renderer. PDF must remain baseline-only unless an adapter
   faithfully renders every capability it claims; it must never inherit SVG
   capability merely by consuming SVG bytes.
2. Define a canonical linear-gradient coordinate policy. The completed Scene
   value must carry finite endpoints in the Layout coordinate plane, derived
   before adapters from a declared angle about the primitive (or canvas) centre.
   Adapters serialize those endpoints; they do not reinterpret angle or bounds.
3. Align the public contract and authoring syntax. Either provide a bounded
   authorable two-to-eight stop model or reduce this first profile to its actual
   two-stop vocabulary. Fidelity is per treatment, not a role-wide accidental
   setting.
4. Assign each bad input to one stable diagnostic with its precise resource
   pointer: malformed value, unsupported fidelity, and declared limit are
   distinct contract failures. Carry the diagnostic message and pointer through
   `RenderFailed` and public render surfaces.
5. Add visual-profile selection to draft rendering, defaulting explicitly to
   baseline. It must use the same profile resolver as immutable Context render,
   without making a CLI or renderer select fallback policy.

## Whole-architecture constraints

- Color Scheme remains the sole concrete-colour authority.
- Layout owns bounds; Scene derives completed visual geometry from those bounds;
  adapters serialize completed values only.
- An adapter may not import Theme, Scheme, profile policy, or resolve assets.
- The correction may remove the false PDF-rich claim rather than preserve it.
  No compatibility shim may silently reinterpret old `v0.6` Context data.
- #350 cannot define icon asset/target semantics until this target fidelity
  contract is published and accepted.

## Design gates

| Gate | Evidence required |
| --- | --- |
| D349-1 | target capability matrix and PDF admission decision, including PNG/PDF characterization |
| D349-2 | gradient coordinate, stop, fidelity, diagnostic, and draft-preview contract amendment |
| D349-3 | whole-architecture review against Context → Theme/Scheme → Layout → Scene → adapter and #350 dependency |

## Planned implementation sequence

| Slice | Scope | Acceptance |
| --- | --- | --- |
| I349-1 | profile/schema migration and structured diagnostics | no false target admission; rich draft preview uses exact profile |
| I349-2 | completed gradient geometry and fidelity/stop resolution | non-square fixtures preserve declared angle; all named diagnostics fire |
| I349-3 | target adapters, materializer evidence, and release | PDF required-rich rejects artifact-free; SVG/PNG prove treatment presence; full suite and CI pass |
