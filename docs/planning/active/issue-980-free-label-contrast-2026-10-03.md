# Issue #980: free labels get a contrast class (work record)

Living record for [#980](https://github.com/tya5/chrona/issues/980) (P1 on the [#454](https://github.com/tya5/chrona/issues/454) board, read only): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history. The owner-level choices are also recorded as a comment on #980 (options, choice, why, how to reverse).

**Public base:** `fb191bdd` on `main`. **Status:** design plan, design, architecture review and implementation plan published together (this PR). No product code yet.

## 1. Published baseline

#980 has the body (written during #890) and one owner comment (other text in the shared `text` role over tinted group bands is still not gated; include it). Read on `fb191bdd` from code, specifications, and the [#884](../../reviews/current/issue-884-group-header-contrast-acceptance-review-2026-10-03.md), [#890](issue-890-as-of-light-cone-2026-10-03.md) and [#995](issue-995-contrast-severity-2026-10-03.md) records:

1. **The class mechanism exists.** `semantic_registry.ContrastClass.GROUND_TEXT` is "ink of the shared `text` role that lies on a ground the Theme chose", resolved by `contrast_binding_for(role, purpose)` for a Text primitive: `contrast_binding(role)` first, else the first `GROUND_TEXT` binding whose `purpose` matches, only when the role is `text`. Today one binding carries it (`groupHeader`, purpose `group-header`). `contrast_policy._primitive_findings` gives it the floor 4.5, disposition `required`, channel `fill`, code `E_SCENE_STATE_TEXT_CONTRAST`, severity class `legibility` (blocking, #995).
2. **The ground is already complete for text.** `_ground_under` takes the topmost earlier covering Rect or Symbol with a fill (a label chip is a Rect one paint order below its label, so a chip is the ground of its own label), samples an opaque gradient, refuses a translucent host (`E_SCENE_CONTRAST_GROUND_UNSUPPORTED`, an error for text), adds the ink of a canvas texture or a catalogue pattern host (two grounds, worse decides), and `_cone_overlay` composites the as-of cone over the host. Nothing in that path is specific to group headers.
3. **Every other Text primitive is ungated.** The committed Scenes carry 34 distinct (purpose, role) pairs of Text; 9 are classified. Ungated: `as-of-label`, `member-label` (outside, role `text`, and inside, roles `member-label-inside-*`), `axis-label` (role `text`, `axis-label2`, `axis-label3`), `table-cell` and `table-column-label` (role `text`), `title-text`, `subtitle-text`, `group-detail`, `milestone-digest-entry`, `relation-label`, `legend-label`, `project-note`, `summary-header`, `summary-metric`, `summary-figure-caption` and `-value`, `note-index`, and the annotation callout, highlight and arrow prose. Theme resolution checks state text on the canvas and the inside labels on their bar (`E_SCHEME_INSIDE_LABEL_CONTRAST`) only.
4. **Prototype read (scratch, not committed).** Classifying all of those purposes `GROUND_TEXT` and running the corpus report gives **no finding on any `text`-role label** (lowest ratio 5.26, the as-of label) and **three new errors, all in `examples/controller-z`**: `note-index` text in the `accent` ink on its ground, 3.28 against 4.5 (`annotations`), and the second axis tier's label (`axis-label2`, ink `surface`) on the `accent` quarter band, 3.67 (`axis-tiers`, `axis-cell-corners`). The reviewer's `halcyon-1/21-target-b` slide has no finding. The same gate over the packaged presets rendered on the starter and on the halcyon project (`chrona render --preset`, scratch) finds `axis-label2` 3.67 on `executive-light` and `elevated-light` (the same `#3986E6` band) and `axis-label3` 1.0 on `technical-print` (ink equal to the hatch ink of the band under it). The `note-index` ink `accent` has 3.2 to 3.7 against the surface in `executive-light`, `elevated-light` and `editorial`.

Inferred: that the three corpus findings are the whole corpus effect (the prototype ran every committed Scene); confirmed by the slice that changes the registry.

Unverified: how the corrected slides look (read as images in C980-1); whether a Theme with a translucent label chip exists outside the corpus (it would now be `E_SCENE_CONTRAST_GROUND_UNSUPPORTED`, the rule for any text on a translucent host).

## 2. Literal acceptance (copied from the issue)

#980 has no acceptance table. Its literal asks, with the owner comment:

1. Add the purposes whose text can lie on a decoration ground (as-of label, member label, period label where unclassified) to the `ground-text` class, one registry line at a time.
2. Run the corpus contrast report and fix any Theme that then fails in its YAML (never relax the 4.5 floor).
3. Axis labels (named in the body).
4. Other text in the shared `text` role over tinted group bands (owner comment).

Assignment constraints: free labels are checked at the required floor against the ground actually beneath them (canvas, band tint, pattern substrate and ink, cone-composited ground, region-frame fill) with the ground resolution the gate has; text stays blocking (#995); a chip or label that carries its own box is judged on that box; no gate weakened; each corpus finding is reviewed and fixed by the general rule or the slide's YAML, never by editing corpus data to pass; synthetic tests (dark canvas with a failing and a passing label, over a pattern, over a cone) read no `examples/` input; mutation-checked; rendered images read for every changed slide; the reviewer's `21-target-b` YAML is not edited.

## 3. Dependencies and neighbours

- Reused unchanged: #884 (ground text), #950 (note ink), #890 (cone ground), #587 (texture and pattern grounds), #995 (severity classes), #428 (chips).
- #991 (target-B knobs, another agent): its layout, legend, chip and hatch code and `halcyon-1` evidence are not touched. #987 (target B): any new finding on the reviewer's slide is reported there, not fixed here (there is none today).
- Files: `semantic_registry.py`, tests, Specifications 46 section 8 and 50, `examples/controller-z` Theme YAML (C980-1), the packaged preset Theme YAML (C980-2). `contrast_policy.py` is unchanged.

## 4. Design plan

### Use cases

| Id | Use case | Source |
| --- | --- | --- |
| U1 | A dark Theme whose as-of label, axis label or outside member label is too close to the canvas, a band, a pattern or the cone fails the corpus gate. | #980 |
| U2 | A label that sits in its own chip is judged on the chip, not on the canvas under it. | assignment |
| U3 | Table cells, group details and the other free text over a tinted band are gated like the group header. | owner comment |
| U4 | A new label purpose cannot silently re-open the hole. | architecture |
| U5 | A public slide whose label now fails is fixed in its YAML by the general rule, or recorded and filed. | assignment |

### Open decisions (decided in section 5, recorded on #980)

- **D1** scope: which purposes.
- **D2** the floor and severity.
- **D3** how a role of its own (second axis tier, inside label, annotation prose) is resolved.
- **D4** chips, translucent hosts, cone, pattern.
- **D5** the corpus findings: fix or record.
- **D6** the packaged presets.

### Responsibility boundaries

The registry says what a role is (one `GROUND_TEXT` argument per binding); the completed-Scene policy resolves the ground and the ratio (unchanged); Theme and preset YAML choose inks and grounds; Layout, Scene construction and adapters are untouched.

### Data and resource model, migration

No schema, Scene, Theme-member or code-path change: a registry classification, one lookup rule, tests, specification text, and Theme YAML where a real slide fails. Public Scenes change only where a Theme value changes (C980-1: three Themes in `examples/controller-z`; C980-2: packaged presets, which render differently by design).

### Design review questions

Does any floor or class weaken? Does the policy stay Scene-only? Can a new label purpose re-open the hole? Does a corpus finding get fixed by editing data to pass, or by a legitimate YAML value choice?

### Acceptance evidence

Synthetic tests; mutation checks; corpus contrast report (0 errors); images of every changed slide read; the preset sweep before and after.

### Order of design slices

C980-1 (class, tests, spec, corpus fixes), C980-2 (presets), acceptance.

## 5. Design

### 5.1 Scope (D1)

Every Text primitive whose role has no contrast class of its own is ground text. In registry terms: the bindings of kind `label` that are not already classified by role get `ContrastClass.GROUND_TEXT`: `asOfLabel`, `axisBand`, `axisLabel`, `axisLabel2`, `axisLabel3`, `groupDetail`, `titleText`, `subtitleText`, `tableColumnLabel`, `tableCell`, `memberLabel`, `memberLabelInside{Planned,Actual,Snapshot,Scenario}`, `milestoneDigestEntry`, `relationLabel`, `legendLabel`, `projectNote`, `noteIndex`, `annotation{Callout,Highlight,Arrow}Text`, `summaryHeader`, `summaryMetric`, `summaryFigureValue`, `summaryFigureCaption`. Not included: `labelVisual` (an Icon, not Text) and the variance cells (classified by role already). The assignment names the as-of label, the member label and the axis label; the owner comment widens it to the other `text` labels; the rest are the same hole on a role of its own. **Options:** (a) the three named purposes, (b) every `text`-role purpose, (c) every unclassified Text (chosen). (a) leaves group details and table text on a tinted band ungated, which the owner comment rules out; (b) leaves a second axis tier, an inside label and annotation prose ungated for no reason of principle (the prototype shows two real failures there). **Reverse:** drop the argument from a registry line.

**U4 guard.** A registry test fails when a `label` binding has no contrast class and is not on a short, named exemption list (`labelVisual`, `finishDelta`, `varianceAhead`, `varianceBehind`: classified through the role they paint). A new label purpose is therefore a conscious registry choice.

### 5.2 Floor and severity (D2)

The `GROUND_TEXT` rule of #884 unchanged: floor 4.5, disposition `required`, channel `fill`, code `E_SCENE_STATE_TEXT_CONTRAST`, severity class `legibility`, blocking in the corpus gate, no Theme knob (#995: text legibility never softens). **Options:** (a) 4.5 for all (chosen), (b) 3.0 for large text, (c) an authored treatment per role. (b) and (c) need size knowledge or a Theme member the gate does not have and would let a Theme opt out of the floor for a free label, which the issue forbids ("never relax the 4.5 floor"). **Reverse:** a registry-class split (a `deemphasized` free-label class) as a later, separate decision.

### 5.3 Resolution of a role of its own (D3)

`contrast_binding_for(scene_role, purpose)` returns the by-role binding when there is one; else, for a Text primitive, the first `GROUND_TEXT` binding with that purpose whose `scene_role` is the primitive's role **or** the primitive's role is the shared `text`. Before: only the second branch. So a label painted in `axis-label2` or `member-label-inside-planned` resolves by (role, purpose) and the shared `text` ink by purpose, as for the group header. `contrast_binding(role)` (by role, used by the Scene model and builder) keeps excluding `GROUND_TEXT`, so no Scene-construction behaviour changes. A non-Text primitive never resolves to ground text.

### 5.4 Grounds (D4)

No new ground rule; the table states what the existing one gives a free label, each with a synthetic test:

| Beneath the label | Ground used |
| --- | --- |
| nothing | the canvas fill |
| a band, a row tint, a region frame, a chip (opaque Rect or Symbol) | that fill, the topmost earlier covering one; a chip is therefore the ground of its own label |
| an opaque gradient | the clamped stop interpolation at the label's sample point |
| a canvas texture or a catalogue pattern host | substrate and ink, the worse ratio decides |
| the as-of cone over any of the above | the host blended with the cone ink at the gradient strength where the label lies (worst of the two block ends); a label straddling the cone's edge also lies on the unblended host |
| a translucent host | `E_SCENE_CONTRAST_GROUND_UNSUPPORTED`, an error (the #995 rule for text, unchanged) |

### 5.5 Corpus findings (D5)

Each finding is reviewed against the general rule and fixed in the slide's own Theme YAML, never in generated output or by relaxing a floor:

- **`axis-label2` on the quarter band (`axis-tiers`, `axis-cell-corners`, 3.67).** The Themes bind the band to `accent` and its label to `surface`. The scheme already names the legible ink on `accent`: `insideLabelPlanned` (`#000000`, 5.73 against `#3986E6`; the planned bar is the same fill). **Chosen:** `axis-label2.fill: insideLabelPlanned` in the two Themes. **Options:** a darker band (`text`, a look change of the band), `text` ink (4.44, still below the floor). **Reverse:** restore `surface` (the gate then fails again, so the reverse is a gate decision).
- **`note-index` (`annotations`, 3.28).** The index digit is the note's marker; the note box stroke and leader are `warning`. **Chosen:** `note-index.fill: warning` in the Theme the slide uses (`examples/controller-z/themes/executive-light.yaml`; about 5.4 against the raised surface it lies on, confirmed by the gate in the slice), tying the index to its note. **Options:** `text` (16, loses the tie), `textMuted`. **Reverse:** restore `accent`.

A finding whose fix would need a data edit or a floor change is not fixed here: it is recorded in this section and a short issue is filed (none expected).

### 5.6 Packaged presets (D6)

The gate runs over the corpus only; a packaged preset that renders a failing label is shipped, as the preset sweep in section 1 shows. They are the same general rule, so C980-2 applies it by YAML: `axis-label2.fill: insideLabelPlanned` in `executive-light` and `elevated-light` (same `accent` band), `note-index.fill` to an ink that passes on the surface in the presets where `accent` does not (`executive-light`, `elevated-light`, `editorial`), and `technical-print`'s `axis-label3` against its band's hatch ink (the exact value chosen with the rendered image; the hatch ink or the label ink changes, not the floor). **Options:** fix now (chosen: the presets are what an author gets by default and the change is YAML), or file a successor. **Constraint:** a preset change moves its pinned digests and characterization records; those are re-recorded in the same PR and listed. **Reverse:** revert the PR; no code depends on the values.

### 5.7 Failure behaviour and extension points

A malformed paint, an unreadable ground and a translucent host are the existing errors. A future deemphasized free-label class is a registry class plus a floor entry; it is not designed here. Warning severity for free labels does not exist: text is `legibility`.

## 6. Architecture review

- **Layers.** Registry declares; the Scene policy is the only judge and is untouched; Theme and preset YAML choose values; Layout and adapters are not involved. The policy still reads only the serialized Scene.
- **No gate weakened.** No floor, class, code or ground rule changes; classifications only grow. Mutation checks (section 7) prove each classification and the by-role resolution matter.
- **One rule per class.** Free labels use the #884 path, not a second one; the guard test keeps the registry the single place that says which roles are text.
- **Adjacent designs.** #950 (note ink, by role, unchanged), #890 (cone as ground, reused for text exactly as for ground text), #587 (two-colour grounds), #995 (text blocks, decoration warns), #431 and #459 (the policy). The section 8 and 50 statements "no other text in the role `text` is classified" become stale and are rewritten.
- **Do not edit data to pass.** The three Theme edits are value choices by the general rule (an ink the scheme names for that ground); no Scene, report, manifest or the reviewer's `21-target-b` YAML is edited; evidence is regenerated by the bot.
- **Compatibility.** No schema, Scene or Theme member change. Specification 56 section 3.2 and the S0 gate do not apply; stated here so the review is complete.

## 7. Implementation plan

| Slice | Files | Tests (synthetic, no `examples/`) | Generated | Publication |
| --- | --- | --- | --- | --- |
| **C980-1** | `src/chrona/presentation/model/semantic_registry.py` (`GROUND_TEXT` on the bindings of 5.1, `contrast_binding_for` rule of 5.3, comments), `docs/specification/46-completed-scene-paint.md` section 8 and `50-constraint-driven-gantt-surface-quality.md` (the class and the statement), `examples/controller-z/themes/{axis-tiers,axis-cell-corners,executive-light}.yaml` (5.5), `tests/unit/chrona/presentation/model/test_semantic_registry_contrast.py` (class list, guard), new `tests/unit/chrona/presentation/scene/test_free_label_contrast.py` | (a) dark canvas with a label too close fails (as-of label, axis label, outside member label, table cell, a second axis tier, an inside label), the same labels in a legible ink pass at the required floor; (b) over a tinted band, over a pattern (substrate and ink), over a canvas texture; (c) over the as-of cone, wholly inside and straddling the edge; (d) in an opaque chip (judged on the chip, not the canvas), in a translucent chip (`E_SCENE_CONTRAST_GROUND_UNSUPPORTED`); (e) a region-frame fill; (f) a non-Text primitive and a decoration role never ground text; (g) `contrast_binding_for` resolution by purpose and by (role, purpose); (h) registry guard: every `label` binding classified or named exempt; (i) the floor is 4.5 whatever the Theme says (a `contrastTreatment` on a free label does not change it) | the corpus contrast report and the Scenes of the three Themes (bot) | one code PR, `Refs #980` |
| **C980-2** | `src/chrona/resources/presets/bundles/{executive-light,elevated-light,editorial,technical-print}/theme.yaml` (5.6), the pinned preset digests and CLI characterization records that move | a test that renders the starter and a note-bearing view under each packaged preset and asserts no `legibility` error (a synthetic project in `tmp_path`, no `examples/` input) | none beyond the bot | one code PR, `Refs #980` |
| **Evidence** | none | corpus report 0 errors before and after; images of `axis-tiers`, `axis-cell-corners`, `annotations` before and after, and one preset image per changed preset, read | none | in the PRs |
| **Acceptance** | `docs/reviews/current/issue-980-...` | literal rows | none | one docs PR, then the exact-main three-OS run |

**Mutation checks (C980-1).** Registry: a classification removed from each of `asOfLabel`, `memberLabel`, `axisLabel`, `tableCell`; the by-role branch of `contrast_binding_for` removed (axis tier 2 and inside labels pass ungated); the by-purpose branch removed (every `text`-role label passes ungated); `GROUND_TEXT` widened to non-Text; the floor lowered for the class; the guard test's exemption list widened. Policy-visible: the cone overlay skipped for ground text; pattern ink dropped; chip order ignored. Each must fail at least one test.

**Order and risk.** If the corpus shows a finding beyond the three read here, or a Theme fix would need a data edit, the slice stops and the cause is recorded in section 5 before code resumes.

## 8. Progress and evidence

Per slice: the PR, the corpus report summary, the images read, the preset sweep. (Empty until C980-1.)
