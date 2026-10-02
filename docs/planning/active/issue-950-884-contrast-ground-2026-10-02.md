# Issues #950 and #884: judge ink on the surface it lies on (work record)

Living record for [#950](https://github.com/tya5/chrona/issues/950) (annotation note ink is compared with the canvas at Theme resolution) and [#884](https://github.com/tya5/chrona/issues/884) (the `groupHeader` text has no contrast class). One record because both are the same defect class: a contrast check that names the wrong ground. Baseline, design plan, design, architecture review, implementation plan and progress; edited in place, Git keeps history.

**Public base:** `d2222b8d` on `main`. **Status:** design plan, design, architecture review and implementation plan published together (this record); no code yet. Slices: C950 (Theme-resolution ground for note ink), C884 (ground-text class and pattern-ink ground in the Scene gate), then evidence and the two acceptance reviews.

## 1. Published baseline

Both issues are P1 correctness items of the board [#454](https://github.com/tya5/chrona/issues/454) (read only). Neither had a comment before the claims (bodies read 2026-10-02). Read on `d2222b8d` from code and specifications, not from images:

1. **Theme resolution judges every state-text role against the canvas.** `color_scheme._state_text_contrast` loops `contrast_bindings(STATE_TEXT)` and compares each role's resolved fill (with its opacity) with the Scheme `surface`, floor 4.5 (`required`) or 3.0 (`deemphasized`), diagnostic `E_SCHEME_STATE_TEXT_CONTRAST` at `/body/roles/<role>/fill`. Only the annotation kind header roles are excepted (`_KIND_TEXT_ROLES`): `_annotation_kind_text_contrast` judges them against the bar colours or the box fills (#584).
2. **The Scene gate already judges note prose on its box.** `contrast_policy._note_box_ground` pairs an `annotation-note-text` primitive with the earlier, same-source, opaque `annotation-note-box` that covers its sample point, and refuses a missing, translucent, gradient or patterned box (`E_SCENE_CONTRAST_GROUND_UNSUPPORTED`). At Theme resolution `_annotation_note_ground` already requires the note box to resolve to one opaque flat colour whenever the note text role is declared. So a declared note text always has a flat box fill, and only the static ink check is aimed at the canvas.
3. **Note text lies only on the note box.** Each annotation kind has its own text role and box role (`annotation-callout-text` on `annotation-callout-box`, and so on); only `annotation-note-text` is classified (state text, `required` only). The callout, highlight and arrow boxes never carry note prose.
4. **Group header text is not classified.** `semantic_registry` binds `groupHeader` (purpose `group-header`, Theme role `groupHeader`, which is a typography role with no paint) with no `ContrastClass`. The Scene builder emits the text as `emit_semantic_text("group-header:<id>", "groupHeader", "text")`, so its visual role is the shared `text` role (painted by the Theme `text` role), and `contrast_binding("text")` is `None` by design: classifying the role `text` would classify every title, cell and label.
5. **The ground the gate would read exists.** `groupHeaderBand` and `groupBand` are classified decoration Rects painted below the header text; #583 tints replace their completed fill, so the Scene already carries the tinted band as a flat fill under the text (Specification 50 section 3.4 says the gate reads it). A Theme may give a band a catalogue pattern: the Rect then carries an opaque substrate `fill`, an ink `stroke` and a completed `pattern`.
6. **A patterned host is judged on its substrate only.** `_ground_under` returns the host's `fill`. `_texture_ink` adds a second ground for a `canvas-texture` host only; `_pattern_findings` judges a patterned primitive's own substrate and ink against its host, but nothing judges a plain text or mark lying on a patterned Rect against the pattern's ink.
7. **Roles and Themes.** `E_SCHEME_STATE_TEXT_CONTRAST` is raised at five places in `color_scheme.py`; one test names it (`tests/integration/test_named_periods.py`). No committed Theme resolves a dark note ink over a dark canvas, because it cannot.

Inferred, to be confirmed by the slice that touches it: that no committed Theme or corpus Scene starts to fail when the note ink is judged on the box (every committed Theme with a note role resolved with ink contrasting the canvas; the box fills are `surfaceRaised` or accent colours), and that no committed Scene has a classified text or mark over a patterned Rect with too little ink contrast.

Unverified: the rendered look of a dark canvas with light note boxes, and of header text over a pattern (both are read as images in the evidence slice).

## 2. Literal acceptance

**#950** (three rows, copied):

1. A Theme with a light note box and dark note ink over a dark canvas resolves, and the Scene gate judges the prose on the box.
2. A note ink that fails against its box still fails at Theme resolution, naming the role and the box.
3. Every committed Theme resolves as before.

**#884** (the body has no checklist; its literal requirements):

1. Give the role a text contrast class (as table cells have).
2. Add a synthetic test where a tint equals the header ink.

**Lane evidence required by the assignment:** a dark-canvas Theme with light notes renders and passes the gates (synthetic); the corpus contrast report stays at 0 errors; rendered images are read; no gate is weakened.

## 3. Dependencies and neighbours

- #584 (closed with this as a disclosed limit) and #583 (closed) are the sources; #459 (surface-aware contrast) and #466 (note placement, required note text) own the policy the fixes extend. #848, #453 and #883 are not touched.
- Other agents work on #585, #491 and #588. This work edits no Theme or View schema, no Scene schema, no example, no preset and no Layout module, so none of the shared schema files is touched. Files: `src/chrona/presentation/color_scheme.py`, `model/semantic_registry.py`, `scene/contrast_policy.py`, their tests, Specifications 07 and 46, and this record.

## 4. Design plan

### Use cases

| Id | Use case | Source |
| --- | --- | --- |
| U1 | A dark-first Theme draws paper-light notes: `annotation-note-box.fill` is a light intent and `annotation-note-text.fill` a dark one, over a dark canvas. It resolves; the Scene gate judges the prose on the box. | #950; Title Card, Off-World, Marquee |
| U2 | The same Theme with a note ink too close to the box colour fails at Theme resolution, naming the role and the box, not the canvas. | #950 acceptance 2 |
| U3 | A light-canvas Theme (every committed Theme) resolves exactly as before. | #950 acceptance 3 |
| U4 | A tinted group header band whose tint equals the header ink is a Scene gate error on the header text; a legible tint is not. | #884 |
| U5 | A group header band with a catalogue pattern is judged on its substrate and on its ink; neither can hide the other. | #884, the pattern's ink and substrate |
| U6 | A mark or label lying on any catalogue-pattern Rect is judged on the pattern's ink as well as its substrate, as for a canvas texture. | root cause, general |

### Open decisions

- **D1** which ground the Theme-resolution check uses for `annotation-note-text`.
- **D2** which box roles count (the issue's parenthetical says all four annotation box roles).
- **D3** how the header text is classified without a Theme migration.
- **D4** the floor and treatment of header text.
- **D5** whether the pattern-ink ground is local to the header or general.

### Design review questions

Does the static check stay a subset of what the Scene gate would later find, never stricter on a different ground? Is any Theme or Scene contract changed (schema, version, diagnostic code)? Does a classified role keep exactly one ground rule across Theme resolution and Scene?

### Acceptance evidence

Unit and integration tests per section 6; mutation checks on each new rule; the corpus contrast report and the S0 gate output; rendered SVG/PNG of the dark-canvas note slide and of a tinted and a patterned header, read in full.

## 5. Design

### 5.1 #950: the ground of note ink at Theme resolution (D1, D2)

`_state_text_contrast` takes the ground of `annotation-note-text` from the resolved `annotation-note-box` fill, the ground the Scene gate takes (`_note_box_ground`), and from the canvas `surface` only when the note box declares no readable colour fill. Everything else is unchanged: the floor (`required`, 4.5), the ink opacity, the pointer `/body/roles/annotation-note-text/fill`, and the diagnostic `E_SCHEME_STATE_TEXT_CONTRAST`. The failure detail names the role and the box (`annotation-note-text:annotation-note-box:<ratio>`) when the box was the ground, and stays `<role>:<ratio>` when the canvas was.

**D1 choice.** Judge on the box, fall back to the canvas. The alternative of judging on both was rejected: a note lies on its box, and a ratio against a canvas the prose never touches rejects valid Themes, which is the defect. The canvas fallback is for a box with no readable colour; in practice `_annotation_note_ground` then rejects the Theme anyway (`E_SCHEME_ANNOTATION_NOTE_GROUND`), so the fallback only fixes the order of two errors.

**D2 choice.** Only `annotation-note-box`. The issue's parenthetical (all four box roles that declare one, as the kind header check does) is true of the kind header, which Layout may draw on any kind of box, but not of note prose: the Scene gate pairs it with the note box only, and the other three boxes have their own unclassified text roles. Judging note ink against a callout or arrow box would reject a Theme whose dark callout box never carries note prose, the same defect moved to another role. Reversal: add the other three fills to the ground list in `_note_ink_grounds`; it is one line and a diagnostic detail.

No new diagnostic, schema or Scene field. Behaviour change: a Theme that declared a dark ink over a dark canvas and a light box was rejected and now resolves; a Theme whose note ink passed the canvas but fails its box was accepted and is now rejected (`E_SCHEME_STATE_TEXT_CONTRAST`). The second case would have failed the Scene gate on the first note drawn, so it is an earlier report of an existing failure, not a new one.

### 5.2 #884: a ground-text contrast class (D3, D4)

The header text keeps the visual role `text` and so its Theme ink; its identity is its purpose, `group-header`. The registry gains the class `ContrastClass.GROUND_TEXT` ("ink of the shared `text` role that lies on a decoration ground"), assigned to the `groupHeader` binding. A ground-text binding is resolved by purpose, never by role: `contrast_binding(role)` ignores it (so the role `text` stays unclassified, and every other text with that role is unaffected), and a new `contrast_binding_for(role, purpose)` returns the role's binding when it has one, else the ground-text binding of a text primitive's purpose. The Scene gate calls the new function.

**D3 choice.** A purpose-keyed class, not a new Scene role and not a Theme `contrastTreatment`. A new Scene role (`group-header`, as the registry already spells it) would change the `visualRole` of every committed group header in every Scene and need a paint alias to the `text` role; a `groupHeader` state-text treatment would make every committed Theme (33 Theme files across examples and bundles) declare it, which is a mass Theme migration for a fixed rule. Reversal: give a Theme the choice later by adding `groupHeader`'s treatment as an optional Theme property (Specification 56 section 3.2, in place); the gate would read it from the primitive as for state text.

**D4 choice.** The treatment is `required` (4.5:1), fixed by the class, not authorable. A group header names the group and is read, like the variance cells that are also fixed or required; a Theme that wants it quieter chooses an ink with 4.5:1 on its bands. The finding is the existing state-text finding (`E_SCENE_STATE_TEXT_CONTRAST`, disposition `required`, floor 4.5, paint channel `fill`, ground id and colour), so the report and the diagnostic inventory gain a row, not a code.

The ground is the one the gate already reads: the topmost earlier opaque flat or gradient-sampled Rect covering the text's sample point, which is the tinted `group-header-band` (or the group band when the header lies on it), else the canvas, plus the canvas texture ink. The Scene is not changed: the primitive carries no new field, so no committed Scene or Scene schema changes and the byte-identity of public Scenes is evidence of that.

### 5.3 #884: the pattern's ink is a ground (D5)

When the host under a classified text or mark is a Rect with a completed catalogue pattern (Scene `v0.7`, `pattern` with `densityBasisPoints` or primitives, and a hex `stroke`), the gate also judges the ink on the pattern's ink colour; the finding records `ground_kind` `pattern-substrate` for the fill ground and `pattern-ink` for the stroke ground, and the worse ratio decides, as for a canvas texture (`texture-substrate`, `texture-ink`). A decoration is still judged against the substrate only (a tint is not judged against thin ink lines). The code is the existing `_texture_ink` generalized to `_host_ink`.

**D5 choice.** General, not header-only. The defect is that a patterned ground has two colours, and the header text is only the first role to notice; a header-only rule would leave marks and variance text over a patterned group band as open as before. Cost: a classified text or mark over a patterned Rect may now fail where it passed; the corpus report is the check (section 8), and a Theme that fails is fixed in its YAML, never by relaxing the rule. Reversal: restrict `_host_ink` to the `GROUND_TEXT` class.

### 5.4 Failure behaviour and extension points

Unreadable or non-opaque grounds keep their existing `E_SCENE_CONTRAST_GROUND_UNSUPPORTED`; nothing is inferred. The class is open: a future text with a shared role and a decoration ground (group detail text over a band, for example) is one registry line.

## 6. Architecture review

- **Layers.** Theme resolution reads only Theme and Scheme values; the Scene gate reads only the completed Scene. Neither reads Layout, and Layout and adapters are untouched. The static check becomes the earlier, narrower report of the failure the gate would find on the same pair, which is the property each of the two checks is for.
- **One ground rule per role.** Note prose: box at both layers. Header text: band (tint, pattern substrate, pattern ink) at the Scene; the Theme `text` ink has no static box to read (the band is a Theme role the View tints), so the Scene is the only checkpoint, as for marks.
- **Compatibility.** No schema, Scene, View, Theme, CLI or diagnostic-code change. A Theme or View that rendered before renders the same unless it was already failing a gate it did not run; Scenes of the corpus are byte-identical (no-change evidence only). The two behaviour changes are stated in sections 5.1 and 5.3.
- **Adjacent designs.** #584 `_annotation_kind_text_contrast` (the same fix for the header; unchanged), #583 tint ("a tint equal to the header ink" is its documented successor), #587 canvas texture (the ink ground is generalized, not duplicated), #459/#466 (the gate and the required note text). The S0 gate does not apply to a code-only change; it is run and recorded in each PR anyway.
- **Do not weaken a gate.** Every change adds a ground or moves a static ground to the ground the gate uses; no floor, no case and no diagnostic is relaxed. The mutation checks (section 7) show each new rule fails when removed.

## 7. Implementation plan

| Slice | Files | Tests | Generated | Publication |
| --- | --- | --- | --- | --- |
| **C950** | `src/chrona/presentation/color_scheme.py` (`_note_ink_ground` used by `_state_text_contrast`); Specification 07 and 46 (note ink ground) | `tests/unit/chrona/presentation/test_color_scheme.py`: dark ink on a light box over a dark canvas resolves; ink too close to the box fails naming role and box; light canvas unchanged; unreadable box falls back to the canvas; opacity counts. `tests/integration/test_annotation_note_ground.py`: a synthetic dark-canvas Theme with light notes renders end to end, the gate judges prose on the box (ground id `annotation-note-box`), and a too-close ink fails at resolution | none expected; public Scenes byte-identical | one code PR, `Refs #950` |
| **C884** | `model/semantic_registry.py` (`GROUND_TEXT`, `contrast_binding_for`), `scene/contrast_policy.py` (purpose lookup, `_host_ink`), registry test; Specification 46 section 8 and Specification 50 section 3.4 | `tests/unit/chrona/presentation/scene/test_contrast_policy.py`: a header text whose ink equals its tint is an error, a legible one is info at 4.5; a patterned band is judged on substrate and ink; a plain `text` of another purpose is not gated; v0.6 is unchanged. `tests/integration/test_group_header_contrast.py`: a synthetic Project through a real render with a tint equal to the ink, a legible tint, and a patterned band | the contrast report gains `group-header` rows (derived, by the bot) | one code PR, `Refs #884` |
| **Evidence** | none (synthetic and report) | the dark-canvas note render and the tinted and patterned header render, read as images; the corpus contrast report 0 errors; S0 output | none | in the PRs and the acceptance reviews |
| **Acceptance** | `docs/reviews/current/issue-950-...` and `issue-884-...` | literal rows, each with direct evidence | none | one docs PR, then the exact-main three-OS run |

**Mutation checks (per slice).** C950: ground left as the canvas; box ground taken from another box role; opacity dropped; the failure detail without the box; the fallback inverted. C884: the class not assigned; purpose lookup returning any `text`; floor 3.0 instead of 4.5; pattern ink ignored; ink judged but the better ratio kept (instead of the worse); decoration given the ink ground.

**Order and risk.** C950 and C884 touch different code and are independent; C950 goes first (it unblocks the dark targets). If a committed Scene fails the new pattern-ink ground, the slice pauses, the cause is recorded here and the Theme or the rule is corrected before code resumes.

## 8. Progress and evidence

Not started. This section records, per slice, the PR, the S0 output, the corpus contrast report summary and the images read.
