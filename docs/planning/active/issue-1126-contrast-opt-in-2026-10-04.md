# Issue #1126: contrast constraints are an opt-in design option (work record)

Living record for [#1126](https://github.com/tya5/chrona/issues/1126) (owner-approved, board [#454](https://github.com/tya5/chrona/issues/454), read only): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history. The owner-level choices are also recorded as a comment on #1126 (options, choice, why, how to reverse).

**Owner directive (2026-10-04, in Japanese on the board; paraphrase):** contrast constraints must not bind design freedom; it is enough that they can be chosen as an opt-in design option. This **supersedes the issue body's "acceptance with a reason against an always-on floor"**: the floors become something a Theme opts into, not something every Theme must argue its way out of.

**Public base:** `a2bfc892` on `main`. **Status:** design plan, design, architecture review and implementation plan published together (this record); no code yet. One code slice (O1126), then the acceptance review.

## 1. Published baseline

Read on `a2bfc892` from code, specifications, #995's record ([severity classes](issue-995-contrast-severity-2026-10-03.md)) and the blocked PRs #1106 (#1074) and #1118 (#1110):

1. **The gate is the completed-Scene policy; it blocks only through the corpus tool.** `contrast_policy.evaluate_scene_contrast` reads the serialized Scene. A mark below 3.0 and a state or ground text below 4.5 (or 3.0) is an `error`; a decoration is a warning with a Theme knob (`contrastPolicy.decoration`, #995). `tools/presentation_contrast.py --check` (conformance, the derived snapshot) fails on any `error`. **A render never fails on a mark or text finding, and today reports none of them.** The only thing that blocks a Theme author's design is therefore the repository's own corpus gate (and, for an author who declares it, `contrastPolicy.decoration: error`).
2. **The two blocked target-B pairs.** White on the amber chip (3.717 against 4.5; the as-of label is `ground-text`) and an actual gate over the same-ink planned gate (1.000 against 3.0). Both are owner choices; PRs #1118 and #1106 make the gate see them and the corpus check would fail.
3. **What else is "contrast" and what is not.** Static Theme-resolution text checks (`E_SCHEME_STATE_TEXT_CONTRAST`, kind, inside label, text on surface: a Theme's own role against its canvas or box), the Scene gate above, and structural gates (`E_THEME_ROLE_REQUIRED`, `E_SCENE_CONTRAST_PAINT`, an invalid treatment, a malformed Scene document). Only the Scene gate's floor misses and its unreadable-ground findings are "contrast constraints" in the owner's sense.
4. **Scenes name their Theme.** A committed Scene's `provenance.resources` lists the Theme's kind, id, revision and content identity, so the corpus tool can tell which Theme made a Scene without any Theme churn. Theme ids are not unique across the corpus (three `executive-light` files), 55 distinct ids across 60 Theme files.
5. **Editing the Themes is not free.** Opting in by adding a member to 60 Theme files changes every Theme content identity, every pinned Context (64) and every Scene's provenance: a corpus-wide migration with no repin tool, and the opposite of "corpus bytes identical".

Inferred, confirmed by the slice: that no public Scene changes bytes (a passing pair emits no warning), and that every committed Scene passes the floors today (the corpus report reads 0 errors).

## 2. Literal acceptance

The issue body's rows are superseded by the owner directive. The criteria of this work, from the directive and the coordinator's assignment:

1. A Theme that declares nothing is not blocked by contrast: its floor misses are typed warnings (CLI, JSON, MCP, corpus report), never an error of the render, of Theme resolution or of the corpus gate.
2. A Theme may opt a class of finding into `error` (or `warning`, or `off`); an opted-in `error` blocks.
3. Bundled presets and the corpus Themes that rely on the floors today stay held to them: their quality guarantee and the "contrast 0 errors" invariant are kept by an explicit opt-in, not by the default.
4. Target B (and any Theme not opted in) renders and passes with warnings; no acceptance and no edit of the target-B YAML is needed, so PRs #1106 and #1118 go green.
5. Only diagnostics severity changes: no rendered output changes, public Scenes are byte-identical.
6. Structural gates are unchanged; an unreadable ground may be an explicit warning instead of a fail-closed error under the default.
7. Spec 46 and 50 state that the floors are opt-in design constraints; skill, diagnostics ledgers and CLI goldens updated; synthetic tests (opt-in `error` blocks, the default warns, an opted-in bundled preset still blocks), mutation-checked.

Not done, and why: the per-pair acceptance with a reason (the issue body). Under the default there is nothing to accept; for a Theme that opts into `error`, the escape is to relax that class. Recorded on #1126 with how to add it later (an optional member).

## 3. Dependencies and neighbours

- #995 (classes, `contrastPolicy.decoration`, the `W_` transport and corpus report) is generalized, not replaced. #884, #950, #980, #1013 (text classes and grounds): unchanged. #1118 and #1106: not touched; they merge after this. #1117 (unread bindings): the policy members are all read. Target-B files are the reviewer's.
- Files: `contrast_policy.py`, `color_scheme.py`, `render_review.py`, `warning_ledger.py`, `diagnostic_messages.py`, `tools/presentation_contrast.py`, a new `conformance/contrast-opt-in.yaml`, `theme-v0.11/0.13.schema.yaml`, Specifications 07, 46, 50, 56 (none: the rule 3.2 is applied), the skill's diagnostics table, CLI goldens, tests.

## 4. Design plan

### Use cases

| Id | Use case | Source |
| --- | --- | --- |
| U1 | Target B at its owner-approved palette renders; the corpus check passes; the two pairs are warnings. | directive |
| U2 | A Theme author who wants the floors writes `contrastPolicy: {mark: error, stateText: error, groundText: error}` and a render with a miss fails. | directive |
| U3 | A bundled preset or a shipped example keeps its guarantee. | assignment |
| U4 | A reader of CLI/JSON/MCP sees a faint mark or text as a typed warning with its ratio and floor. | #995 |
| U5 | An author silences a class (`off`). | directive |

### Open decisions (each decided in section 5 and recorded on #1126)

- **D1** the classes and values. **D2** the default. **D3** how today's guarantees are kept without editing 60 Themes. **D4** floors. **D5** unreadable grounds. **D6** the per-pair acceptance. **D7** reporting and codes.

### Responsibility boundaries

Theme declares the policy and the render enforces it where the Theme is known; the completed-Scene evaluator takes the severities as an argument and never reads a Theme; the corpus tool, which sees Scenes only, applies the repository's opt-in registry by the Scene's Theme identity; Layout and adapters are untouched.

### Data and resource model, migration

One generalized optional Theme member (`contrastPolicy`), one repository registry file, four new `W_` codes (the warning twins of the existing error codes). A Theme that omits the member is "not opted in".

### Design review questions

Does anything change a rendered byte? Is any floor changed (no)? Does the corpus keep failing for a shipped Theme that regresses? Can a Theme author be blocked by contrast without having asked for it (no, except through the repository's own registry for the repository's own Themes)?

### Acceptance evidence

Synthetic tests per section 7; mutation checks; corpus regenerated byte-identical; corpus report with the opt-in registry (0 errors for opted-in Themes, warning counts for the rest); target B in a scratch copy of #1118 and #1106 with its owner palette: passes with warnings; S0 output.

## 5. Design

### 5.1 The policy (D1, D4)

Theme body `contrastPolicy`, each member optional, each `off | warning | error`:

| Member | Findings it governs (code at `error`) |
| --- | --- |
| `mark` | a data mark below 3.0 (`E_SCENE_MARK_CONTRAST`) |
| `stateText` | a state text below its treatment floor (`E_SCENE_STATE_TEXT_CONTRAST` of a state-text role) |
| `groundText` | ink of a ground-text purpose (group header, as-of label) below 4.5 (`E_SCENE_STATE_TEXT_CONTRAST` of a ground-text purpose) |
| `decoration` | a decoration below 1.10 (`E_SCENE_DECORATION_CONTRAST`), and a decoration on an unreadable ground (`E_SCENE_CONTRAST_GROUND_UNSUPPORTED`), as in #995 |
| `unsupportedGround` | a mark or text whose ground cannot be computed (`E_SCENE_CONTRAST_GROUND_UNSUPPORTED`) |

At `warning` the finding keeps everything and becomes a warning with the `W_` twin code; at `off` it becomes an `info` row (the measured ratio stays visible in the evidence, nothing is reported); at `error` it is the blocking finding it is today. **Floors are not Theme values**: the registry floors and the authored `contrastTreatment` stand; a class is switched, not retuned (reversal: an optional `floor` per member later, additive).

Never governed by the policy: `E_SCENE_CONTRAST_PAINT`, `E_SCENE_STATE_TEXT_CONTRAST_TREATMENT`, a malformed Scene (`E_SCENE_CONTRAST_DOCUMENT`) and every Theme-resolution check: they are structural, not contrast constraints.

**D1 choice.** Five classes mirroring the registry (`MARK`, `STATE_TEXT`, `GROUND_TEXT`, `DECORATION`) and the one failure the gate cannot compute (`unsupportedGround`). Options: one switch for all (too coarse: target B needs marks and ground text relaxed while decoration may stay), per role (a class per role is the unread-binding hazard of #1117), per pair acceptances (D6). Reversal: collapse members.

### 5.2 The default (D2)

A Theme that omits `contrastPolicy`, or a member, is **not opted in**: that class is `warning`. This is the one default, applied wherever a Theme is known (the render). Contrast never blocks a Theme author unless the Theme says `error`. The evaluator function itself keeps its explicit argument (and, when called with none, today's behaviour: legibility `error`, decoration `warning`), so every existing synthetic test of the gate's geometry keeps its meaning; the default is applied by the callers.

**D2 choice.** `warning`, per the directive and the coordinator's recommendation. Options: `error` (today; rejected by the owner), `off` (loses the report the owner still wants, #995). Reversal: one constant.

### 5.3 Validation and carry (Spec 56 section 3.2)

`theme-v0.11` and `theme-v0.13` `contrastPolicy` becomes an object of the five members with enum `off, warning, error` (`decoration` gains `off`; the other four are new optional properties). `color_scheme._contrast_policy` validates each (an unknown member or value is `E_THEME_CONTRAST_POLICY` at `/body/contrastPolicy/<member>`, as for #995) and the resolved Theme carries the declared members. An absent member is "not opted in".

### 5.4 Enforcement and reporting (D7)

- **Render.** After the Scene is composed, every render evaluates it with the Theme's severities (default `warning`) and projects each `warning` finding into the warning records beside #995's: codes `W_SCENE_MARK_CONTRAST`, `W_SCENE_STATE_TEXT_CONTRAST`, `W_SCENE_CONTRAST_GROUND_UNSUPPORTED` (new) and `W_SCENE_DECORATION_CONTRAST`, `W_SCENE_DECORATION_GROUND_UNSUPPORTED` (as in #995), each with `findingCode` (the error it stands for), the measured ratio, the floor, the ground and the class. They reach the Scene `diagnostics`, the CLI, MCP and JSON, collapsed by `collapse_warnings`. A class set to `error` fails the render with the finding's blocking code at `/body/contrastPolicy/<member>`, before any adapter output (#995's behaviour, generalized).
- **Corpus tool.** `presentation_contrast.py` reads each Scene's Theme identity from its provenance and applies the **repository's opt-in registry** `conformance/contrast-opt-in.yaml` (the Theme ids the repository holds to the floors): a listed Theme is evaluated with `mark`, `stateText`, `groundText` and `unsupportedGround` at `error` (today's gate, unchanged) and `decoration` at `warning` (as #995); an unlisted Theme with every class at `warning`. The report prints, per Scene set, which Themes are not opted in and their warning counts, so nothing drifts silently. `--check` fails only on errors and the decoration witness.
- **Messages and skill.** `diagnostic_messages` names each new code; the skill table gains rows.

**D3 choice: a registry, not 60 Theme edits.** The repository keeps its guarantee by listing its opted-in Themes in one file (all 55 current Theme ids except `target-b`), generated once from the committed Scenes. Options: add `contrastPolicy: error` to 60 Theme files (changes every Theme and Context identity and every Scene's provenance: a corpus migration with no repin tool, contradicting "bytes identical"); carry the policy in the Scene (bytes of every opted-in Scene change); default the corpus to `error` and let a Theme opt out (that is opt-out, and target B would need an edit); a per-example manifest switch (per-slide). The registry is the repository's own opt-in, visible, and unlisted means "warns", as the directive asks. A Theme that declares `error` itself needs no listing: its render already fails. Reversal: delete the file (the corpus gate then holds nothing), or list a Theme.

Disagreement with the coordinator's recommendation (3), recorded: "bundled presets and example Themes opt in explicitly in their YAML" cannot keep corpus bytes identical (their content identities, the pinned Contexts and every Scene's provenance change). The registry achieves the same guarantee with the same visibility and zero byte change. Bundled presets are additionally pinned by a synthetic test that renders each under `error` for every class with 0 findings.

### 5.5 Unreadable grounds (D5)

`unsupportedGround` governs a mark or text on a ground that cannot be computed. Under the default it is a warning, not a fail-closed error; an opted-in Theme (or the registry) keeps today's error.

### 5.6 No per-pair acceptance (D6)

Dropped. Under the default there is nothing to accept; a Theme that opts into `error` and wants one exception relaxes that class. It would be an optional additive member (a list of reasoned pairs, as the issue body drew) if a Theme ever needs both a strict class and a named exception.

### 5.7 Compatibility

Optional members only (`theme-v0.11` and `theme-v0.13`, in place, S0 gate recorded in the code PR); the enum widening of `decoration` is checked by the S0 gate and recorded. No Scene schema change. No Theme, preset or example changes; public Scenes byte-identical; CLI output changes only where a default render now reports a floor miss it never reported (checked against every characterization case).

## 6. Architecture review

- **Layers.** Theme declares; the render enforces where the Theme is known; the evaluator reads only a Scene and takes severities as an argument; the corpus tool applies a repository registry by the Scene's own provenance; Layout and adapters are untouched.
- **Nothing weakened for the repository.** Every shipped Theme that is gated today is listed, so its floors, grounds and codes are unchanged; the registry check keeps "0 errors" for them. What changes is who is bound: a user's Theme, and any Theme not listed (target B), no longer is.
- **Structural gates untouched.** Paint, treatment and document errors, `E_THEME_ROLE_REQUIRED`, and every Theme-resolution text check stay.
- **Consumer rule.** Every policy member is read by the render and the tool; an unknown member fails at its pointer.
- **Adjacent designs.** #995 (generalized; its decoration behaviour is the `decoration` member), #884/#950/#980/#1013 (the findings governed), #1110/#1074 (unblocked), #1117 (the closure rule).
- **Do not edit data to pass.** No Theme, example or preset is edited; target B stays the reviewer's.

## 7. Implementation plan

| Slice | Files | Tests (synthetic, no `examples/`) | Generated | Publication |
| --- | --- | --- | --- | --- |
| **O1126** | the files of section 3 | Scene unit: each class at `off`/`warning`/`error` for a mark, state text, ground text, unsupported ground and decoration (codes, severity, class); structural findings never softened; the default argument equals today. Theme: members validated at pointers (schema and `resolve_theme`), undeclared leaves the resolved Theme unchanged. Render: default Theme warns and renders (a faint mark, a faint ground text, the as-of-label shape), `error` fails with the blocking code, `off` reports nothing, an opted-in bundled preset renders with 0 findings under all-`error` and a mutated one blocks. Corpus tool: opted-in Theme fails on a floor miss, unlisted warns, report section. CLI characterization re-recorded if severities show | the contrast report and diagnostic inventory (bot) | one code PR, `Refs #1126` |
| **Evidence** | none | corpus regenerated byte-identical; target B in a scratch copy of #1118 and #1106; S0 output | none | in the PR |
| **Acceptance** | `docs/reviews/current/issue-1126-...` | rows 1 to 7 | none | one docs PR, then the exact-main three-OS run |

**Mutation checks.** Default made `error`; default made `off`; `off` treated as `warning`; `warning` treated as `error`; a class mapped to the wrong member; unsupported ground governed by `mark`; structural finding softened; decoration governed by `mark`; render ignoring the Theme; render failing under `warning`; registry ignored; registry inverted; unlisted Theme held strict; Theme carry dropped; validation accepting an unknown value; report section dropped.

**Order and risk.** If a committed Scene changes bytes or a listed Theme gains an error, the slice stops and the cause is recorded here.

## 8. Progress and evidence

Per slice: the PR, the S0 output, the corpus report summary and the target-B scratch result.
