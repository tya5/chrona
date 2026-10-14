# Issue 1134: contrast policy, optional reasoned per-pair exception

Status: design and implementation plan for one PR (`Refs #1134`). Successor of #1126 (section 5.6 of
`issue-1126-contrast-opt-in-2026-10-04.md` reserved this shape). Normative text lives in
Specification 07 (Contrast policy), Specification 46 section 8 and Specification 56 section 3.2; this file does not
repeat it.

## 1. Baseline

Public base `ad857a52`. `contrastPolicy` (Theme v0.15) sets five classes to `none | warning | error`. A class at
`error` fails the render with the first blocking finding. There is no way to keep a class strict and accept one named
pair. Owner decision of 2026-10-04: nothing needs this today, so this is optional and additive.

## 2. Literal acceptance (rows of the #1126 body, as carried by #1134)

1. A text pair at 3.72 with an exception at 3.5 is a warning; the same pair with an exception at 4.0 is an error.
2. A mark pair at 1.0 with an exception at 1.0 is a warning.
3. Missing `minimum` or `reason` fails at its pointer.
4. An unmatched exception is reported.
5. Absent exceptions give byte-identical output.

(The "Target B declares both pairs" row of the #1126 body was superseded by the opt-in default and is not carried.)

## 3. Design

- **Shape.** Optional member `contrastPolicy.exceptions`: a non-empty array of
  `{role | purpose, over, minimum, reason}`. Exactly one of `role` (the finding's visual role) or `purpose`;
  `over` is the visual role of the ground the pair was measured against, `canvas` for the canvas, or `any`;
  `minimum` a finite number greater than 0; `reason` a non-empty string. Unknown keys are refused.
- **Effect.** Only a floor finding that is an `error` under its class (`E_SCENE_MARK_CONTRAST`,
  `E_SCENE_STATE_TEXT_CONTRAST`, `E_SCENE_DECORATION_CONTRAST`) with a measured ratio. The first matching entry in
  declaration order applies. Ratio at or above `minimum`: the finding becomes the warning
  `W_SCENE_CONTRAST_ACCEPTED` (it stands for the blocking code it replaced; facts: ratio, floor, `minimum`, `reason`,
  ground). Below `minimum`: still the original error. A class at `warning` or `none` has no error to accept, so its
  entries are unused.
- **Unused entry.** An entry that replaced or matched no error finding in the Scene is reported as the warning
  `W_SCENE_CONTRAST_EXCEPTION_UNUSED` with disposition `exceptions[<i>]` (same consumer rule as #1117). An entry that
  matched a pair below its `minimum` is used: the error already names the pair.
- **Layers.** The Theme declares and `resolve_theme` validates (`E_THEME_CONTRAST_POLICY`, pointer
  `/body/contrastPolicy/exceptions/<i>/<field>`); the Scene evaluator takes the entries as an argument and reads
  only the Scene; the render maps findings to warnings. The corpus tool (provenance registry) passes none.
- **Compatibility.** An optional property added in place (Spec 56 section 3.2), no version bump. Absent member:
  the evaluator receives no entries, every code path and the Theme identity are unchanged. No Scene schema change.
- **Not done.** `minimum` below the class floor is not required to be useful and `minimum` above the floor is allowed
  (it can never apply); no per-Scene scoping.

## 4. Implementation plan (one slice)

Files: `src/chrona/presentation/scene/contrast_policy.py` (evaluator), `src/chrona/presentation/color_scheme.py`
(validation), `src/chrona/usecases/render_review.py` (pass entries, map warnings), `diagnostic_messages.py`,
`schemas/theme-v0.15.schema.yaml`, expected-deltas if the gate asks, Specs 07, 46 and 56, `skills/chrona/references/diagnostics.md`.
Tests (synthetic): `tests/unit/chrona/presentation/scene/test_contrast_exception.py`,
`tests/unit/chrona/presentation/test_contrast_exception_theme.py`, one render test. Evidence: schema equivalence gate,
conformance, `tools/regenerate_public_examples.py --check --jobs 4`. Bot-generated files are not committed.
