# Implementation Plan — Serialized Scene Perceptibility Gate (#446)

**Design:** `issue-446-scene-perceptibility-design-2026-09-26.md`.
**Architecture review:**
`issue-446-scene-perceptibility-architecture-review-2026-09-26.md`.
**Start condition:** the P0 acceptance review and CI for the corrected
#443/#455 corpus record zero unpermitted findings.  This plan is published
before that condition; source implementation is not.

## I446-1 — Pure finding model and evaluator

**Files:** a focused scene-perceptibility module under
`src/chrona/presentation/scene/`, unit fixtures/tests beside Scene model and
serialization tests.

1. Define the versioned immutable finding value, finite codes/severities,
   canonical ordering, strict Scene mapping ingress, and shared report form.
2. Implement opaque-Rect text occlusion, tolerance-aware slot disposition,
   text intersection, and composited-paint observation exclusively from the
   mapping fields described in design.
3. Validate typed host classification against same-surface primitive identity;
   do not accept arbitrary relation strings, geometry guesses, count baselines,
   or renderer objects.

**Acceptance:** deterministic unit fixtures cover every code, 50% occlusion
threshold, tie ordering, tolerance edge, malformed/missing facts, host
classification, each slot disposition, and no imports from Layout/font/
renderer modules.

## I446-2 — Corpus tool and conformance gate

**Files:** `tools/check_scene_perceptibility.py`, conformance workflow/input
configuration, focused tool/conformance tests, generated diagnostic inventory
if literal identifiers change.

1. Discover only committed public generated Scenes and feed each through I446-1.
2. Emit stable human-readable and machine-readable report entries.  Fail only
   on `E_`; retain `I_` entries without aggregate baseline suppression.
3. Add exactly one named conformance invocation after generated-evidence
   integrity.  Do not call rasterization, materialization, pytest, or matrix
   orchestration from the tool.

**Acceptance:** corpus report contains zero errors and individually listed
declared visible-overflow outcomes; a synthetic bad Scene causes a named
failure; an existing conformance test proves one invocation and continues
independent tests on failure.

## I446-3 — Draft warning projection

**Files:** post-Scene draft render result/diagnostic transport, CLI/result
tests, no immutable corpus artifacts unless normal source output changes.

1. Invoke the shared evaluator on the exact completed Scene representation
   after Scene construction.
2. Map error findings to ordered `W_SCENE_*` draft diagnostics retaining code,
   Scene identity, primitive ids, and measured facts in the result payload.
3. Preserve successful artifact serialization and leave informational findings
   reportable but non-duplicative.

**Acceptance:** a draft-only synthetic occlusion/escape produces stable
warning facts while SVG/Scene bytes remain the same as the completed artifact;
invalid source/resource diagnostics retain their existing behavior.

## I446-4 — Release review

**Files:** P0/#446 acceptance review and affected public evidence.

1. Run evaluator/tool over regenerated public corpus after all source changes.
2. Run focused unit/tool/render/materializer/conformance tests and structural
checks; batch materializer regeneration once; inspect generated report and a
representative Scene/SVG diff.
3. Publish source/evidence atomically.  Use the existing three-OS CI and
newest-Python materializer job for full suite/release evidence; query only at
expected completion, not repeatedly.

**Release acceptance:** no committed Scene has an `E_` perceptibility finding;
typed host relationships are the sole intentional classification; CI contains
the gate once and no renderer/adapter gains a quality-policy branch.

## Stop conditions

Return to design if a check needs font/raster data, a new Scene layout fact, an
untyped exemption, a renderer-specific interpretation, threshold/role policy
owned by #431, or CI aggregation behavior owned by #451.
