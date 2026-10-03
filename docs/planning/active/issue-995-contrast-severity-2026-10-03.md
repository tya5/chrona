# Issue #995: contrast severity classes, decoration and ground are warnings (work record)

Living record for [#995](https://github.com/tya5/chrona/issues/995) (owner decision, top of the [#454](https://github.com/tya5/chrona/issues/454) board, read only): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history. The owner-level choices are also recorded as a comment on #995 (options, choice, why, how to reverse).

**Public base:** `16c9de36` on `main`. **Status:** design plan, design, architecture review and implementation plan published together (PR #996, `b2bc837b`). C995-1 (severity classes, report, render warnings) is merged (PR #1001); C995-2 (the Theme knob) is in review; then the acceptance review.

## 1. Published baseline

#995 had no comment before the claim (body read 2026-10-03). Read on `16c9de36` from code, specifications and PR [#993](https://github.com/tya5/chrona/pull/993) (the reviewer's target-B reproduction), not from images:

1. **The gate is the completed-Scene policy, and it blocks through the corpus tool.** `contrast_policy.evaluate_scene_contrast` (Specification 46 section 8) returns one finding per classified primitive; `severity` is `error` below the floor, else `info`. Nothing in the render path calls it: `chrona render` never fails on it. It blocks through `tools/presentation_contrast.py --check` (conformance check `presentation-contrast`, and the derived-evidence snapshot), which exits 1 when any finding has severity `error`. Tests call it on synthetic renders.
2. **Floors by registry class** (`semantic_registry.ContrastClass`): `MARK` 3.0 (planned, actual, snapshot, missing-actual, summary bar, progress fill, deadline mark, network node); `STATE_TEXT` 4.5 or 3.0 by `contrastTreatment` (variance cells, note text, period label, kind header text); `GROUND_TEXT` 4.5 (group header, #884); `DECORATION` 1.10 (`calendar-closed`, `period-band`, `axis-band-decoration` and `2`, `group-band`, `row-band`, `group-header-band`, `group-tab`, `annotation-note-box`, `annotation-kind-bar`, `-accent`, `-stamp`). Canvas texture, region frame, chips, the cone and the legend swatch are unclassified.
3. **Theme resolution holds text checks only.** `color_scheme.py` raises `E_SCHEME_STATE_TEXT_CONTRAST` (note ink on its box, #950; every other state text on the canvas), `E_SCHEME_ANNOTATION_KIND_CONTRAST`, `E_SCHEME_INSIDE_LABEL_CONTRAST` and `E_SCHEME_CONTRAST` (text on surface). There is **no decoration check at Theme resolution**, so there is nothing to downgrade there; those four stay.
4. **Decoration failures are also gate errors when a ground cannot be read.** A decoration over a translucent host is `E_SCENE_CONTRAST_GROUND_UNSUPPORTED` (error); a decoration pattern is judged on its substrate against the host and its ink against both (`_pattern_findings`), each pair failing as `E_SCENE_DECORATION_CONTRAST`. A malformed paint is `E_SCENE_CONTRAST_PAINT`.
5. **Target B reproduces the failure.** Rendering the #993 sources with the weekend stripe at the approved 0.45 (the PR raises it to 0.85) gives 83 `E_SCENE_DECORATION_CONTRAST` errors, all `calendar-closed`, ratio 1.053 against the 1.10 floor; no mark, text or other role fails (checked in a scratch copy, not committed).
6. **Reporting transports exist.** A render's `warning_records` (`usecases/warning_ledger.collect_render_warnings`) feed the Scene `diagnostics` (`W_` identities), the CLI and the MCP/JSON payloads through `draft_render.warning_payloads`, which collapses equal-code, equal-cause rows into one row with `count` and `occurrences` and a `message` from `diagnostic_messages`. The scene perceptibility family already travels this way (`E_SCENE_*` finding to `W_SCENE_*` warning, draft renders only).
7. **Theme schema additions** follow Specification 56 section 3.2 (optional property, in place, `theme-v0.11` and `theme-v0.13`, the two versions `resolve_theme` accepts, an L1 entry in the expected-deltas file for the S0 gate); the resolved Theme body carries declared optional members (`annotationKinds`).

Inferred, confirmed by the slice that touches it: that no committed Scene has a decoration below its floor (the corpus contrast report has 0 errors), so every public Scene stays byte-identical except target B once it uses the approved opacity.

Unverified: how the 83 warnings read in the CLI text output (collapsed to one row by `collapse_warnings`; read in the evidence step).

## 2. Literal acceptance (copied from the issue)

1. Decoration and ground roles below their floor produce warnings in the report and in the Scene diagnostics, and they no longer fail conformance or the derived snapshot. Text and data-mark roles still fail.
2. A synthetic test covers both severities.
3. Spec 50 (and the contrast policy docs) state the split.
4. Afterwards, the reviewer returns target B's weekend opacity to the approved look (0.45, or the mock's value).

Assignment constraints: marks and text keep their floors (#950 and #884 keep rejecting illegible text and marks); decoration and ground-vs-ground findings are warnings with typed diagnostics and a stable code, reported (CLI/JSON, corpus contrast report, MCP) and failing neither render nor Theme resolution; a declared Theme knob makes the class blocking again; synthetic tests (illegible text blocks, decoration-only failure warns, the knob restores blocking) read no `examples/` input; mutation-checked; no per-slide exemption; corpus output is evidence, not an oracle.

## 3. Dependencies and neighbours

- #950, #884 (text and mark grounds, unchanged), #459 and #431 (the policy), #987, #991 and #993 (target B, the other agent's `examples/halcyon-1` files and knobs: not touched), #970 (the S0 tool: used, not edited), #980 (unclassified free labels: unchanged, still out of scope).
- Files: `contrast_policy.py`, `tools/presentation_contrast.py`, `usecases/render_review.py`, `warning_ledger.py`, `diagnostic_messages.py`, `color_scheme.py`, `skills/chrona/references/diagnostics.md`, Specifications 07, 46, 50, tests, and (C995-2) `theme-v0.11/0.13.schema.yaml` plus the expected-deltas file. Shared schema edits are one optional property each; rebased before every push.

## 4. Design plan

### Use cases

| Id | Use case | Source |
| --- | --- | --- |
| U1 | Target B's weekend shading at the approved faint opacity renders; conformance and the derived snapshot stay green; the 83 closed days are reported as warnings. | #995, #993 |
| U2 | Text or a data mark that is illegible (a variance cell, note ink, a group header, a planned bar) still fails the gate. | #950, #884 |
| U3 | An author who wants a faint band to be a hard error (a print Theme, an accessibility profile) declares it and the render fails. | assignment |
| U4 | An agent or CLI user sees the faint decoration as a typed warning with the measured ratio and floor. | assignment |

### Open decisions (each is decided in section 5 and recorded on #995)

- **D1** which findings become warnings (the class, and the unreadable-ground case).
- **D2** the stable codes and the typed fields.
- **D3** where warnings are reported (render path, tool, draft or all revisions).
- **D4** the knob: where it is declared, its values, where it is enforced.
- **D5** what stays blocking, and the stale statements.

### Responsibility boundaries

Registry (`ContrastClass`) says what a role is; the completed-Scene policy turns a ratio into a finding with a severity by class; the render use case turns warning findings into the render's warning records and enforces the Theme's knob; the corpus tool aggregates; Theme declares the knob; Layout and adapters are untouched.

### Data and resource model, migration

One optional Theme body member (`contrastPolicy.decoration`), two new `W_` codes, one new finding field. No Scene schema change (the Scene carries the warnings as `diagnostics` strings, as for every `W_`). A Theme that omits the member behaves as the default. Public Scenes are byte-identical except where a decoration is below its floor (none in the corpus today).

### Design review questions

Does any floor, class or text check weaken? Does Scene stay the only input of the policy (no Theme re-resolution)? Is the knob declared in a layer that can enforce it? Does the corpus tool still fail on a real text or mark error?

### Acceptance evidence

Synthetic tests per section 7; mutation checks; the corpus contrast report (0 errors, warnings counted); target B regenerated in a scratch copy at 0.45 (0 errors, 83 warnings); the S0 gate output in the C995-2 PR.

### Order of design slices

C995-1 first (it unblocks #993's reviewer); C995-2 (knob) second; acceptance last.

## 5. Design

### 5.1 Severity classes (D1, D5)

Two classes, fixed by the registry class of the role, never by slide:

| Class | Registry classes | Below the floor |
| --- | --- | --- |
| `legibility` | `MARK`, `STATE_TEXT`, `GROUND_TEXT` | `error`, blocking (unchanged: floors, grounds and codes) |
| `decoration` | `DECORATION` | `warning` by default; `error` when the Theme declares it (5.4) |

A decoration's *ground-vs-ground* findings (its fill against the host, a pattern's ink against its substrate and host) belong to the decoration class: they warn. A decoration whose host cannot be read (translucent host: today `E_SCENE_CONTRAST_GROUND_UNSUPPORTED`) cannot be judged, which is also a ground-vs-ground finding and also warns. Never downgraded: any finding of a `legibility` role (a mark or text on a translucent host stays `E_SCENE_CONTRAST_GROUND_UNSUPPORTED`; a mark or text on a decoration is judged on that decoration exactly as before), `E_SCENE_CONTRAST_PAINT`, `E_SCENE_STATE_TEXT_CONTRAST_TREATMENT` and `E_SCENE_CONTRAST_DOCUMENT` (malformed input is integrity, not perceptibility), and every Theme-resolution text check.

**D1 choice.** Class by the existing registry classification, as the issue says, including `annotation-note-box` and the kind accent and stamp (all registered `DECORATION`). Options: (a) all `DECORATION` (chosen), (b) only roles the author marks faint, (c) split by "carries information", which needs a new classification and per-role judgement. Chosen because it adds no new vocabulary and the issue asks for it; the text on a note box is still gated at 4.5 on the box. Reversal: reclassify a role as `MARK` in the registry (one line) to make it blocking for everyone.

**Unreadable decoration ground: warn.** Option: keep it an error. Chosen to warn because it is not an illegibility, it is a missing measurement, and the owner's rule is that ground-vs-ground never blocks; the finding still names the host. Reversal: the knob, or one line in `_decoration_severity`.

### 5.2 Codes and typed diagnostics (D2)

A decoration finding keeps its `visualRole`, `purpose`, ratio, floor, ground id, ground kind, paint channel and sample, and gains `severityClass` (`decoration` or `legibility`, set on every classified finding). Codes by severity:

| Situation | Warning (default) | Blocking (knob) |
| --- | --- | --- |
| below floor | `W_SCENE_DECORATION_CONTRAST` | `E_SCENE_DECORATION_CONTRAST` (as today) |
| host unreadable | `W_SCENE_DECORATION_GROUND_UNSUPPORTED` | `E_SCENE_CONTRAST_GROUND_UNSUPPORTED` (as today) |

A passing decoration stays `info` with `E_SCENE_DECORATION_CONTRAST` as its code (unchanged; the committed report keeps its rows). The finding `severity` becomes `warning` (a third value beside `error` and `info`).

### 5.3 Reporting (D3)

- **Render.** After composing the Scene (beside the perceptibility step, every revision), the use case evaluates the serialized Scene with the Theme's decoration severity and projects each `warning` finding into the render's warning records: code, `findingCode` (the blocking code), `scenePath`, `primitiveIds`, and `measuredFacts` (`contrastRatio`, `floor`, plus `groundId`, `groundKind`, `paintChannel` when present). They reach the Scene `diagnostics`, the CLI and the MCP payloads, collapsed by `collapse_warnings` (one row per code with `count` and `occurrences`). Findings with severity `error` are not turned into render failures except the decoration ones the knob makes blocking (5.4): as today, text and mark errors are the corpus gate's, not the render's.
- **Corpus report.** `presentation_contrast.py` counts warnings per row and in total, prints a `Warnings` column and `warnings: N` on the summary line, shows `warning` in the per-primitive table, and still fails only on `error` findings and the witness. The decoration witness counts a warned decoration as enabled.
- **Messages.** `diagnostic_messages` names the cause of each new warning; the skill's diagnostics table gains a row.

**D3 choice.** Every revision, not draft only: unlike the perceptibility family (a drafting aid) the faint decoration is a property of the published design, and the immutable Scene is the evidence. Cost: one Scene evaluation per render (the same order as perceptibility, which already runs on draft). Reversal: gate the call on the draft revision.

### 5.4 The knob (D4)

The Theme declares `contrastPolicy: {decoration: warning | error}` in its body (optional; omitted means `warning`). Chosen over: a per-role property (a class needs one entry per role, and the issue speaks of a class), a Layout Profile member (contrast is paint, owned by the Theme, not geometry), a Scene field (a schema change for a Theme choice, and the Scene policy would then read the author's intent from the artifact it judges), and a CLI flag (an author's choice must live in the resource, not in the command line). The Theme resolver validates it (`E_THEME_CONTRAST_POLICY` at `/body/contrastPolicy/decoration` for an unknown value or member) and carries it in the resolved Theme body. The render use case passes it to the evaluator; with `error`, any decoration finding that would warn keeps its blocking code and the render fails with that code (`E_SCENE_DECORATION_CONTRAST` or `E_SCENE_CONTRAST_GROUND_UNSUPPORTED`, naming the first primitive and the count) before any adapter output. The corpus tool has no Theme and evaluates with the default; a committed Theme that declares `error` cannot reach it with a failing decoration because the render that makes the Scene already failed. `legibility` has no knob: nothing about it may be softened.

Reversal of the default: change the evaluator's default value and the Spec 50 sentence; no Theme migration.

### 5.5 Failure behaviour and extension points

An unknown severity value is a Theme error before Scene construction; the evaluator rejects a value outside `{warning, error}` with a `ValueError`. A future second warning class (a free-label class, #980) is one more registry class and one more member of `contrastPolicy`.

## 6. Architecture review

- **Layers.** Theme declares; Scene is the only input of the policy; the use case applies the Theme's choice to the policy result and reports; Layout and adapters are untouched. The evaluator stays Scene-only: the knob is an argument, not a Theme read.
- **No gate weakened.** The marks and text checks, floors, grounds, codes and the Theme-resolution checks are untouched; mutation checks (section 7) prove each fails when the class split is removed. Legibility of text and marks *on* a warned decoration is still judged on that decoration's colour, so a decoration cannot hide an illegible mark by being faint.
- **One rule per class across the repository.** The registry says which class; the policy is the only place severity is decided; the report and the render read the finding.
- **Compatibility.** No Scene or View schema change; one optional Theme member (Specification 56 section 3.2, S0 gate recorded in the C995-2 PR); two new `W_` codes. Public Scenes byte-identical except a decoration below floor, none today; target B's own sources are the reviewer's.
- **Adjacent designs.** #431, #459, #466, #884 and #950 define the classes and are unchanged in effect; #890 (cone as ground) and #587 (texture ground) untouched; #980 remains open and unrelated.
- **Do not edit data to pass.** No example, preset or Theme is edited to pass this work; the target-B proof is a scratch copy.

## 7. Implementation plan

| Slice | Files | Tests (synthetic, no `examples/`) | Generated | Publication |
| --- | --- | --- | --- | --- |
| **C995-1** | `scene/contrast_policy.py` (`severity_class`, `decoration_severity` argument, warning codes), `tools/presentation_contrast.py` (warnings column and count), `usecases/render_review.py` and `warning_ledger.py` (contrast warnings), `diagnostic_messages.py`, `skills/chrona/references/diagnostics.md`, Specifications 46 section 8, 50 (period band and the decoration sentence), 07, 08, 64 (stale floor statements) | `test_contrast_severity.py` (Scene unit): (a) an illegible state text, ground text and mark still error, (b) a decoration below floor warns and the document has no error, an unreadable decoration host warns, a pattern decoration warns, a mark on a faint decoration is still judged, (c) `decoration_severity="error"` restores the old codes. Integration: a synthetic render with a faint closed-day shade succeeds and carries `W_SCENE_DECORATION_CONTRAST` in `warning_records` and the Scene `diagnostics`; the report aggregates warnings and `--check` passes on a warning-only corpus and fails on a text error. Existing tests that read a decoration `error` are updated to the explicit blocking argument | the contrast report and the diagnostic inventory (derived by the bot) | one code PR, `Refs #995` |
| **C995-2** | `theme-v0.11/0.13.schema.yaml` (`contrastPolicy`), expected-deltas file, `color_scheme.py` (validate and carry), `render_review.py` (enforce), Specification 07 | Theme resolution accepts the member and rejects a bad one; the same synthetic render fails with `E_SCENE_DECORATION_CONTRAST` under `error` and warns under the default and under an explicit `warning`; illegible state text still fails Theme resolution whatever the member; `schema_equivalence` output recorded | none beyond C995-1 | one code PR, `Refs #995` |
| **Evidence** | none | target B regenerated in a scratch copy at 0.45 (0 errors, 83 warnings); corpus report 0 errors; S0 output | none | in the PRs |
| **Acceptance** | `docs/reviews/current/issue-995-...` | literal rows | none | one docs PR, then the exact-main three-OS run |

**Mutation checks.** C995-1: decoration severity forced to error; warning code swapped for the error code; class assignment widened to marks (a mark below floor would warn); class assignment dropped for ground text; unreadable decoration host kept as error; the report counting warnings as errors; the render skipping the projection; the projection dropping measured facts. C995-2: knob ignored; knob inverted; an unknown value accepted; knob read from the wrong key; error path warning only.

**Order and risk.** If a committed Scene starts to fail or a legibility finding changes, the slice stops and the cause is recorded here before code resumes.

## 8. Progress and evidence

Per slice: the PR, the S0 output, the corpus contrast report summary and the target-B scratch result.

**C995-1 (severity classes, report, render warnings; Refs #995).** `contrast_policy` carries `severity_class` (`legibility` or `decoration`, from the registry class) and takes `decoration_severity` (`warning` default, `error`); a decoration floor miss, an unreadable decoration host and the pattern pairs of a decoration are `warning` with the two new `W_` codes, everything else is unchanged. `presentation_contrast.py` counts `Warnings` per row and in total; `--check` still fails only on errors and the witness. `render_review` evaluates the Scene on every render and projects warnings into `warning_records` (`SceneContrastWarning`), hence the Scene `diagnostics`, the CLI and the MCP payloads, collapsed by `collapse_warnings`. Tests: 34 Scene unit tests (`test_contrast_severity.py`: illegible state text, deemphasized text, ground text, marks, progress fill and note text on its box stay errors under both severities; a mark or text on a translucent host, a malformed paint and a missing treatment stay errors; a decoration-only failure leaves the document with no error; each registry decoration role warns by class; pattern pairs; unreadable host; a mark and text on a faint decoration are still judged on it; the blocking argument restores the error codes), 5 render tests, 3 corpus-tool tests (warning-only corpus passes `--check`, an illegible mark or text fails it). Eight existing tests that asserted a decoration `error` now ask for the blocking mode explicitly and also assert the warning. Mutation checks: 22 of 22 killed (one first-pass survivor, a decoration pattern on a translucent host, killed by a new test). Corpus contrast report: 0 errors, 0 warnings, 3340 findings; no public Scene changes. Target B in a scratch copy of the #993 sources with the weekend stripe at 0.45: 0 errors, 83 `W_SCENE_DECORATION_CONTRAST` (ratio 1.053, floor 1.10), marks unaffected.

**C995-2 (the Theme knob; Refs #995).** `theme-v0.11` and `theme-v0.13` gain the optional `body.contrastPolicy: {decoration: warning | error}` (Specification 56 section 3.2, in place). `color_scheme._contrast_policy` validates it (`E_THEME_CONTRAST_POLICY`, reachable only by a caller that bypasses the schema, which already reports `E_THEME_SCHEMA` at the exact pointer) and carries it in the resolved Theme body; `render_review._scene_contrast_warnings` passes it to the evaluator and, for `error`, fails the render with `E_SCENE_DECORATION_CONTRAST` or `E_SCENE_CONTRAST_GROUND_UNSUPPORTED` at `/body/contrastPolicy/decoration`, naming the first decoration and the count, before any adapter output. Tests (synthetic render through a packaged bundle, no `examples/` input): a faint band fails the render under `error`, a legible band renders under `error`, an explicit `warning` equals the default byte for byte, illegible state text still fails Theme resolution under every setting, an unknown value or member is refused by the schema at its pointer, and four unit tests of `resolve_theme` (carried, absent when undeclared, bad value or member refused, a text check never softened). Mutation checks: 11 of 11 killed (the eleventh, a mark on a translucent host blocking the render, was a real defect of the first push: that finding carries the same `E_SCENE_CONTRAST_GROUND_UNSUPPORTED` code as the decoration one, the `mcp-floor` check caught it, and the blocking filter now also requires the decoration class; a render test covers it under every setting). S0 gate `python -m tools.schema_equivalence --base-rev origin/main`: PASS, L1 `additive` for `theme-v0.11` and `theme-v0.13` (no expected-delta entry needed). Corpus unchanged.

**Finding: the packaged default preset warns.** The default `chrona render` of the starter project now prints one collapsed `W_SCENE_DECORATION_CONTRAST` row for the editorial row-band zebra (ratio 1.013 against 1.10). It is a true finding that no corpus slide shows, because the contrast gate only ever read the corpus. Thirteen CLI characterization cases (stderr) were re-recorded for it. The zebra is a preset design value, not changed here (no data is edited to pass a criterion); whether the preset should be strengthened or the warning narrowed is the owner's call and is recorded on #995.
