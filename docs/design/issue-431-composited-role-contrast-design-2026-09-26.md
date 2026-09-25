# Design — Composited Role Contrast and Corpus Visibility (#431)

**Design plan:**
`issue-431-composited-role-contrast-design-plan-2026-09-26.md`.

## Decision

Contrast policy is a finite presentation-contract concern with two evaluation
boundaries:

1. Theme closure rejects state-text role paint that is below its declared
   floor when composited over the resolved surface ground.
2. A completed-Scene policy evaluator diagnoses visible decoration paint that
   is below its fixed visibility floor over the opaque canvas ground.  Its
   public-corpus report is a checked generated artifact.

The existing `scene.perceptibility` paint observation becomes a consumer of a
small pure composition kernel.  #431 adds policy and reporting around that
kernel; it does not add a second contrast formula, a raster comparison, or
renderer-specific logic.

## Finite role policy

The semantic registry gains an explicit contrast classification for only these
roles:

| Class | Scene visual roles | Floor | Boundary |
| --- | --- | ---: | --- |
| state text | `variance-ahead`, `variance-on-track`, `variance-behind`, `missing-actual-cell` | `required` 4.5:1; explicitly `deemphasized` 3:1 | Theme closure and completed Scene report |
| decoration | `axis-band-decoration`, `row-band`, `calendar-closed`, `group-band`, `group-header-band` | 1.10:1 | completed Scene policy/report |

All other roles retain their existing contracts.  A role's class is never
inferred from a primitive id, adapter operation, or colour value.

State-text roles must declare finite `contrastTreatment: required` or
`deemphasized` in their Theme role binding.  This controls only their fixed
floor; it does not permit a numeric author override.  The resolved fill and
opacity are composited over the resolved Scheme `surface` before comparison.
A violating role produces `E_SCHEME_STATE_TEXT_CONTRAST` with the exact role
path, so a Theme binding cannot reach Layout with an unreadable state value.

## Explicitly absent decoration

Decoration Theme roles extend `backgroundTreatment` with `none`.  `none` is a
declared omission, not transparent fill or zero opacity:

- Layout receives a typed background disposition and creates no decoration
  placement for `none`.
- Scene carries a finite `decorationDispositions` record for every declared
  absent decoration role on each surface.  This makes omission inspectable
  even though it has no drawable primitive.
- `fill` and `outline` remain enabled dispositions and must satisfy the
  completed-Scene 1.10:1 floor when they emit a background decoration.

The Scene schema/model and serializer gain this explicit evidence.  No adapter
is asked to interpret `none`, derive a fallback colour, or hide a primitive.

## Shared completed-paint analysis

`scene.paint_analysis` is a renderer-neutral pure module.  Given a flat hex
paint, opacity, and an opaque canvas paint it returns the composited colour and
WCAG contrast ratio.  It accepts no font, raster, Layout, or adapter input.

For this issue's finite classes, the authoritative ground is the completed
surface canvas: current background decorations and state text are specified on
that surface rather than on an arbitrary overlapping host.  A future semantic
role that paints over another variable paint must introduce an explicit host
ground contract; it may not reuse this floor with a guessed overlap order.

`scene.perceptibility` continues to emit its policy-free
`I_SCENE_PAINT_CONTRAST` observations from the shared kernel.  A separate
`scene.contrast_policy` maps completed `purpose`/`visualRole` facts through the
registry classification and emits deterministic `E_SCENE_DECORATION_CONTRAST`
and state-text report findings.  Draft feedback transports the same completed
finding as a warning; immutable corpus checking fails only on policy errors.

## Report and migration

`tools/presentation_contrast.py` reads committed public Scene documents,
collects every classified primitive and explicit absence, and writes a stable
per-purpose report.  For each applicable purpose it records primitive count,
slide count, minimum/median contrast, floor, and disposition.  `--check`
compares the checked report and returns every below-floor finding; it does not
create a numeric baseline or suppress a known violation.

All light and dark Theme declarations migrate in the same implementation slice
as the regenerated public Scene/SVG evidence.  The corpus includes at least
one visibly emitted example for alternating rows, axis bands, closed days,
group bands, and group-header bands.  The exact state-text values are migrated
with their finite treatment declarations.  A generated Scene cannot advance
with a stale report, inventory, or materializer output.

## Boundaries and non-goals

- Color/Scheme closure owns declared state-text admissibility; Layout owns
  placement; Scene transports completed paint and absence facts; adapters only
  serialize supplied primitives.
- The Scene policy evaluator observes and reports.  It never repaints, moves,
  drops, or substitutes a primitive.
- The 1.10:1 decoration floor is not a generic accessibility-text rule, and
  the 3:1 de-emphasis choice is not a general colour override mechanism.
- Gradients, shadows, images, and varying host backdrops are outside this
  first finite policy.  A classified role using one requires a later explicit
  ground-analysis design rather than a heuristic sample.
