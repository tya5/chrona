# Design — Serialized Scene Perceptibility Gate (#446)

**Design plan:** `issue-446-scene-perceptibility-design-plan-2026-09-26.md`.
**Status:** Proposed for architecture review.

## P0 audit and scope

The audit runs only over committed serialized public Scenes, at Layout's
micro-point tolerance.  After #443 and #455 correction evidence it reports:

| Family | P0-defect result | Classified residual |
| --- | --- | --- |
| opaque later-paint text occlusion | zero | none |
| text intersection over 4 square points | zero | none |
| `ellipsize-with-source` text outside its slot | zero | none |
| slot escape under `visible-overflow` | no unpermitted escape | 24 declared outcomes, chiefly title font-box leading/descender geometry |
| paint perceptibility | threshold not selected | #431 policy input, not a P0 exemption |

The 24 declared outcomes are not a numeric baseline.  Each is classified from
its own completed slot overflow declaration.  A changed primitive, slot, or
policy is evaluated afresh.

The gate is an observer of public Scene facts.  It neither substitutes for
Layout containment/collision validity nor changes a Scene, renderer, View,
Theme, or generated artifact.

## Finding contract

`chrona.presentation.scene.perceptibility` provides a pure evaluator over a
deserialized `chrona/scene/v0.6` document and returns ordered immutable
findings:

```text
ScenePerceptibilityFinding(
  version, code, severity, scene_path, primitive_ids,
  slot_id?, measured_facts, disposition?
)
```

`version` is `v1`; `code` belongs to a finite vocabulary; `scene_path` and
primitive ids establish stable identity; `measured_facts` contains only
serialized coordinates, paint, ordering, slot policy, and calculated area or
contrast.  Findings sort by `(scene_path, code, primitive_ids)` independently
of JSON object ordering.  No primitive-ID allowlist, count baseline, or
untyped reason string is part of the contract.

The evaluator accepts mappings/JSON primitives only.  It imports neither font
metrics, Layout composition, a renderer, nor a rasterizer.  The public tool
loads committed files and invokes this same evaluator.  The draft path first
serializes its completed Scene-equivalent mapping, invokes the evaluator, and
adds ordered warnings to its command result; it does not mutate immutable
evidence bytes or rerun Layout.

## Checks

### 1. Later opaque paint occlusion

For each positive-area `Text` primitive, inspect later visual primitives in
the stable serialized `(paintOrder, primitive input index)` relation.  A
candidate occluder is a positive-area `Rect` with a nonempty fill and fully
opaque resolved paint.  It reports `E_SCENE_TEXT_OCCLUDED` if its intersection
covers at least 50% of the text box.

An exact typed relation is the sole intentional exception: a text primitive
whose `hostPlacementId` names that candidate is classified as
`I_SCENE_HOSTED_TEXT_OVERLAP`, not silently ignored.  The host must be present
in the same surface and the host relation remains independently schema/model
validated.  Path strokes, transparent fills, zero-area shapes, unresolvable
paint, and geometry below the Layout tolerance are not opaque occluders.

### 2. Slot containment and declared disposition

For a positive-area text primitive with a known slot, compare its bounds with
the slot at micro-point tolerance.

- `fit` and `ellipsized` text outside the slot report
  `E_SCENE_TEXT_SLOT_ESCAPE`.
- `suppressed` text is excluded.
- a slot declaring `visible-overflow` produces the informational,
  individually-addressed `I_SCENE_DECLARED_VISIBLE_OVERFLOW` finding with the
  slot policy and excess facts.  It is not a gate failure and requires no
  count baseline.
- a `clip-optional` slot has no visible escaped text; otherwise it reports an
  error.  An ellipsis declaration is not permission to escape.

The check observes actual Scene geometry.  It does not infer source width,
line breaking, or a new canvas policy.

### 3. Text intersection

Compare distinct positive-area `Text` primitives in the same surface.  An
intersection greater than four square points reports
`E_SCENE_TEXT_INTERSECTION`, including both primitive ids, slot ids,
collision provenance if serialized, and area.  Exact same-primitive entries,
sub-threshold measurement residue, and typed host text-versus-host primitive
relations are outside this text-text comparison.  Declared `visible-overflow`
does not suppress a text-text intersection: it remains an observable warning
for drafts and a failing unpermitted corpus result unless a future policy
specifically gives it a typed counterpart.

### 4. Composited paint observation

The evaluator includes a pure sRGB hex/RGB alpha-composition kernel.  It
reports `I_SCENE_PAINT_CONTRAST` for a primitive whose resolved paint can be
composited over the serialized canvas ground, carrying the resulting ratio and
paint facts.  It does not assign a pass/fail threshold, semantic role class,
or required/optional status.  #431 owns those decisions and can consume this
one kernel rather than creating a renderer-specific implementation.

## Tool, draft, and CI ownership

`tools/check_scene_perceptibility.py` discovers every committed
`examples/**/generated/*.scene.json`, parses strictly, produces one stable
machine-readable and human-readable report, and fails only on `E_` findings.
It runs once as a named conformance gate after generated evidence integrity;
it does not start pytest, rasterization, or a second materializer population.
Malformed/missing Scene evidence remains an ordinary conformance failure.

Draft rendering uses the evaluator after Scene serialization and maps `E_`
findings to ordered `W_SCENE_*` diagnostics for author visibility; its normal
artifact stays available under the #449 valid-closure rule.  Informational
findings remain available to reports but do not duplicate warnings.

## Invariants and non-goals

1. The checked corpus has no `E_` findings before the gate becomes required.
2. Typed hosts are validated model facts, never geometric or numeric
allowlists.
3. Evaluator output is deterministic for byte-identical Scene input.
4. The evaluator neither reads fonts/raster state nor resolves placement,
paint policy, text measurement, or adapter semantics.
5. Role thresholds, palette migration, README visual selection, and a generic
layout collision repair remain outside #446.

## Required evidence

- pure evaluator fixtures for each code, ordering tie, tolerance boundary,
  typed host classification, every disposition, and malformed document;
- public corpus tool output with no `E_` findings and individually reported
  declared visible-overflow observations;
- draft warning evidence using the same evaluator and unchanged artifact bytes;
- one conformance integration test proves the tool is invoked once without
  suppressing pytest or matrix jobs; #451 owns aggregate process reporting;
- #431 consumes the compositing kernel only after its own threshold design.
