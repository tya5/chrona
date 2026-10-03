# Issue #1013: a label on a translucent chip or panel is judged on its composited ground (work record)

Living record for [#1013](https://github.com/tya5/chrona/issues/1013) (P1 on the [#454](https://github.com/tya5/chrona/issues/454) board, read only): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history. The owner-level choices are also recorded as a comment on #1013 (options, choice, why, how to reverse).

**Public base:** `ecdacefa` on `main`. **Status:** design plan, design, architecture review and implementation plan published together in one docs PR, before code. One code slice (C1013-1) follows.

## 1. Published baseline

#1013 (found by #980) has a body and no later comment, and no acceptance table: *a free label (or mark) whose ground is a translucent Rect (a label chip or region frame with opacity below 1) is a blocking `E_SCENE_CONTRAST_GROUND_UNSUPPORTED`, because the policy refuses any translucent host; no committed Theme has one; direction: composite the host over the ground beneath it (the cone path already composites translucent ink) so the label is judged on the colour it truly lies on.* Read on `ecdacefa` from [`contrast_policy.py`](../../../src/chrona/presentation/scene/contrast_policy.py), [`paint_analysis.py`](../../../src/chrona/presentation/scene/paint_analysis.py) (`blend_over`), Specifications 46 section 8, 50, 08 (C4 note box) and 07, and the [#980](issue-980-free-label-contrast-2026-10-03.md), [#995](issue-995-contrast-severity-2026-10-03.md) and [#890](issue-890-as-of-light-cone-2026-10-03.md) records:

1. **One refusal.** `_ground_under` picks the topmost earlier covering Rect or Symbol with a fill (the as-of cone is skipped, it is a tint, #890); if that host's `paint.opacity` is not 1 it returns "unsupported" (`E_SCENE_CONTRAST_GROUND_UNSUPPORTED`, an error for text and marks, a warning for a decoration, #995). A translucent host is therefore never read, even when what lies beneath it is a plain canvas.
2. **The pieces to compose already exist.** `blend_over` (opaque colour of an ink at an opacity over an opaque ground), `sample_linear_gradient`, `_host_ink` (a canvas texture or a catalogue pattern host is ground in two colours, worse decides), `_cone_overlay`/`_under_cone` (cones painted between a host and the primitive tint the ground; worst of the block ends; a straddling label also lies on the untinted host).
3. **The corpus never hits it.** The committed contrast report has 0 errors and 0 warnings, so no public Scene has a label, mark or decoration on a translucent host.
4. **A different, deliberate refusal.** Note prose is judged only against its own same-source, opaque, flat note box and "cannot fall through to another host" (Specification 08, C4, #950): `_note_box_ground` is not `_ground_under`.
5. Statements that this changes: Specification 46 section 8 (two places: "a mark or text on a translucent host remains `E_SCENE_CONTRAST_GROUND_UNSUPPORTED`" and "a translucent chip or host cannot be read"), Specification 50 (period band paragraph: "a translucent host beneath a mark or text still cannot be judged"), Specification 07 (region frame: "a translucent fill is an unsupported ground and fails closed"), and the ledgers `docs/diagnostics/presentation-contrast.md`, `skills/chrona/references/diagnostics.md` and `docs/diagnostics/inventory.md` (generated code locations and the code's meaning).

Unverified: how a translucent chip looks when rendered (read as an image in C1013-1 from a synthetic Theme override).

## 2. Literal acceptance (copied from the issue)

#1013 has no acceptance table. Its literal asks, with the assignment constraints:

1. Composite the host over the ground beneath it so a free label (or mark) is judged on the colour it truly lies on, instead of failing closed.
2. (Assignment) The ground resolution is the one the gate has: `blend_over`, the cone-composited ground, pattern substrate and ink; the beneath ground is a band, pattern, texture, cone, region frame or the canvas.
3. (Assignment) Synthetic tests only: a translucent chip over a light and a dark canvas, over a band tint, over a pattern (worst-of-grounds as for patterns and cones); no committed Theme is needed.
4. (Assignment) Fail-closed stays for what is genuinely unresolvable, documented exactly (section 5.4).
5. (Assignment) #995 classes kept: text legibility blocks, decoration warns; no gate weakened.
6. (Assignment) Specifications 46 and 50 and the diagnostic ledgers updated; mutation-checked; one rendered image of a synthetic case read if one is rendered.
7. (Assignment) The reviewer's `examples/halcyon-1/*target-b*` YAML and #991's files are not touched; a new finding on them is reported on #987.

## 3. Dependencies and neighbours

- Reused unchanged: #884/#980 (ground text), #890 (cone as ground), #587 (two-colour grounds), #995 (severity classes), #950/C4 (note box).
- #991 (target-B knobs, another agent): layout, legend, chip and hatch code and the `halcyon-1` evidence are not touched. A translucent chip drawn by #991's knobs is judged by this change; any finding on the reviewer's slides goes to #987.
- Files: `contrast_policy.py` (the only code), the tests, Specifications 46, 50, 07, the diagnostic ledgers. No Layout, Scene, schema, Theme or adapter change.

## 4. Design plan

| Id | Use case | Source |
| --- | --- | --- |
| U1 | A label on a translucent label chip, a translucent region frame or a translucent panel is judged on the colour it lies on, light or dark canvas. | #1013 |
| U2 | The same over a band tint, a canvas texture, a catalogue pattern, an opaque or opaque-gradient host, and under the as-of cone. | #1013 |
| U3 | A mark on a translucent host (same code path) is judged likewise. | #1013 body |
| U4 | What cannot be read stays blocking `E_SCENE_CONTRAST_GROUND_UNSUPPORTED`, and a decoration keeps its warning. | assignment |

Open decisions (decided in section 5, recorded on #1013): **D1** which classes composite; **D2** what set of grounds a translucent host yields; **D3** cones around a translucent host; **D4** how the finding names the composite; **D5** what stays unresolvable.

Responsibility boundary: the completed-Scene policy is the only judge and stays Scene-only (reads the serialized Scene); Theme, Layout, adapters and the registry are untouched. Data model: no Scene member, schema or Theme change; one new `groundKind` value family in a finding (an open string field today). Migration: none; the corpus has no translucent host, so no public Scene or report changes. Design review questions: does any floor, class or code weaken? Can a composite look better than the truth (a missed worst ground)? Does the recursion terminate? Does a decoration or the note box change?

Acceptance evidence: synthetic tests (section 7), mutation checks, corpus report unchanged (0 errors, 0 warnings), one rendered synthetic image read, specification and ledger text.

## 5. Design

### 5.1 The rule (D2)

A host with `paint.opacity` a in [0, 1) and a readable fill is composited, not refused. The ground of a label is resolved by one recursive function over the Scene's paint order, with the candidate rule of today (topmost earlier covering Rect or Symbol with a fill, cone skipped):

- **No host:** the canvas fill (a translucent canvas stays unresolvable, 5.4).
- **Opaque host:** unchanged (flat fill, or the gradient sample at the label's sample point; a canvas texture or catalogue pattern host adds its ink as a second ground).
- **Translucent host H (opacity a):** resolve the grounds *beneath H* by the same function (the topmost covering host earlier than H at the label's sample point, with the cones painted between that host and H applied). Each colour of H (its fill or gradient sample, and its stroke ink when H is a texture or catalogue pattern host) becomes `blend_over(colour, a, beneath)` for **every** beneath ground. The label is judged on every composite and the worst ratio decides, as for patterns and cones. Stacked translucent hosts recurse; paint-order keys strictly decrease, so it terminates.

Worst-of-grounds is exact for a label inside one uniform region; the sample point decides the host and the gradient sample, as for an opaque host. Over a pattern or texture the chip is composited against substrate **and** ink, so the label is judged on the darker of the two composites too.

### 5.2 Classes (D1)

Marks and text (`legibility`: `mark`, `state-text`, `ground-text`) composite. A decoration does not: it keeps its documented `W_SCENE_DECORATION_GROUND_UNSUPPORTED` warning on a translucent host, with its dominant-substrate model and no ink or cone grounds (#995, Specification 46 section 8). **Options:** (a) legibility only (chosen), (b) every class, (c) text only. (b) widens the decoration model (a translucent band over a translucent band, which Layout already orders, #893) and would change warnings nobody asked about; (c) leaves a mark on a translucent chip blocking for no reason (the #1013 body says "or mark"). **Reverse:** drop the class condition (one line) to composite decorations too.

### 5.3 Cones (D3)

Cones painted after the beneath host and before H tint the beneath ground (block ends decide, straddle rule, as today), then H is composited over that. Cones painted after H tint the composite, as they tint an opaque host. A cone stays a tint, never a host.

### 5.4 What stays unresolvable (D5), exactly

Each remains `E_SCENE_CONTRAST_GROUND_UNSUPPORTED` (error for text and marks, warning for a decoration) or, where it is today, `E_SCENE_CONTRAST_PAINT`:

1. A translucent host whose opacity is not a finite number in [0, 1], whose fill is not `#RRGGBB`, whose gradient cannot be sampled, or whose beneath ground is itself one of these (recursively).
2. A **translucent canvas** (`canvasPaint.opacity` not 1): nothing is known under it. Unchanged (`E_SCENE_CONTRAST_PAINT`).
3. **Note prose** on a translucent, gradient, patterned or missing note box (Specification 08 C4): that contract pairs the prose with its own opaque flat box and forbids fall-through. Unchanged, not part of this change.
4. A decoration on a translucent host (5.2).
5. A label whose sample point is unknown (no bounds) keeps the canvas, as today.

### 5.5 Naming the composite (D4)

The finding keeps one row per channel with the worst ratio. For a composite ground: `groundId` the translucent host, `groundColor` the composited colour, `groundKind` `translucent-over-<kind of the beneath ground>` (`translucent-over-canvas`, `translucent-over-flat`, `translucent-over-pattern-host-ink`, `translucent-over-translucent-over-flat`, ...); when a cone tints it, `cone-blend` with the cone as `groundId`, as today. No new finding field.

### 5.6 Failure behaviour and extension points

A malformed paint is the existing error; nothing is silently skipped and nothing falls through to another host. Extensions not designed here: compositing for decorations (5.2 reverse) and a translucent canvas over a declared page colour.

## 6. Architecture review

- **Layers.** Only the Scene policy changes; it still reads the serialized Scene alone. Registry, Layout, Theme and adapters are untouched.
- **No gate weakened.** No floor, class, code or severity changes. A case that failed closed (a translucent host) now fails only when the composite is below the floor, so a passing result requires the true worst ground to clear 4.5 or 3.0. Every case that was already judged goes through the same opaque code. The resolver returns every beneath ground (texture ink, pattern ink, cone ends), never a subset. Mutation checks (section 7) prove it.
- **No second rule.** One resolver serves flat, pattern, text and mark; the note box and the decoration model are explicitly outside (5.4).
- **Adjacent designs.** #890 (the cone is a tint over the host: reused for the beneath ground and the composite), #587 (two colours), #995 (classes), #950/C4 (note box fail-closed), #893 (translucent pairs have a Layout-defined paint order, so stacked hosts are ordered). Specification 56 section 3.2 and the schema gate do not apply (no schema or View, Theme or Layout Profile change); stated for completeness.
- **Do not edit data to pass.** No Theme, Scene, report, manifest or `halcyon-1` file is touched; the corpus has no translucent host, so evidence is byte-identical.
- **Compatibility.** A Theme that paints a translucent chip or frame under a label no longer fails closed; it is judged. A downstream project that failed with `E_SCENE_CONTRAST_GROUND_UNSUPPORTED` on such a label now passes, or fails with the ordinary `E_SCENE_STATE_TEXT_CONTRAST` (ratio and composited ground reported). Intended.

## 7. Implementation plan

| Slice | Files | Tests (synthetic, no `examples/`) | Generated | Publication |
| --- | --- | --- | --- | --- |
| **C1013-1** | `src/chrona/presentation/scene/contrast_policy.py` (one resolver replaces `_ground_under`'s refusal; the flat and pattern callers consume its grounds), Specifications 46, 50, 07, `docs/diagnostics/presentation-contrast.md` note, `skills/chrona/references/diagnostics.md`, new `tests/unit/chrona/presentation/scene/test_translucent_ground_contrast.py`; the existing translucent-host assertions in `test_free_label_contrast.py`, `test_contrast_severity.py` and `tests/integration/test_contrast_severity_render.py` move to the new rule (each remaining unresolvable case keeps a fail-closed test) | (a) chip over light and over dark canvas, pass and fail, composite colour exact (`blend_over`); (b) over a band tint, an opaque gradient, a region frame; (c) over a canvas texture and a catalogue pattern: worst of substrate and ink decides; (d) stacked translucent hosts; (e) cone before and after the chip, straddling; (f) a translucent patterned chip; (g) a mark on a translucent host; (h) decoration still warns, note box, translucent canvas and unreadable paints still fail closed; (i) text stays `legibility`/error, `decoration_severity` cannot soften it; (j) one render of a Theme override with a translucent label chip | the bot only (corpus unchanged) | one code PR, `Refs #1013` |
| **Evidence** | none | corpus report 0 errors, 0 warnings; the synthetic render image read | none | in the PR |
| **Acceptance** | `docs/reviews/current/issue-1013-...` | literal rows | none | one docs PR, then the exact-main three-OS run |

**Mutation checks (C1013-1).** The composite replaced by the host colour alone; the beneath ground ignored (canvas used); only the first beneath ground kept (texture or pattern ink dropped); the cone before the chip dropped; the cone after the chip dropped; the opacity ignored (host treated as opaque); the class condition widened to decorations (the decoration-warns test fails) and narrowed to text only (the mark test fails); the floor lowered; the unreadable-paint refusal removed. Each must fail at least one test.

**Order and risk.** If implementation shows the corpus changes, or a rule beyond section 5 is needed, the slice stops and the cause is recorded here before code resumes.

## 8. Progress and evidence

Per slice: the PR, the corpus report summary, the image read, the mutation results. (Empty until C1013-1.)
