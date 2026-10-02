# Architecture Review — Shared Schema Parts (#662)

Reviews the [design](../../design/issue-662-schema-parts-design-2026-09-30.md) and the issue proposal against AGENTS.md layer boundaries, Spec 56 §3.2 and §3, and the adjacent designs (#591, #573, #574, #575),
on main `400f323d`. Baseline and claim checks: [design plan](../planning/issue-662-schema-parts-design-plan-2026-09-30.md). Mechanics: [implementation plan](../planning/issue-662-schema-parts-implementation-plan-2026-09-30.md).
This is a pre-implementation architecture review, not the literal acceptance review; it carries no acceptance marker.

**Verdict:** the direction (shared URN parts, one loader, equivalence gate first) is sound. Read literally, the issue's proposal would have done four harmful things, each found by measurement and
each changed by an amendment (A1-A9): silently dropped vocabulary from coverage tooling (F2), rejected 10 to 14 committed documents by unifying identifiers (F9), tightened Scene by absorbing its
geometry into the catalog part (F10), and retro-changed seventeen View versions if `presentation-resource` were edited (F3). Not a rubber stamp.

## Checks that pass

- **Layer.** Schemas own accepted structure; consumers own defaults; a part carries no behaviour. `chrona.resources` is already a neutral leaf imported by Core (`core/validation.py`), presentation, operational and
  extensions, and already imports `jsonschema`; placing the registry and factory there adds no import edge (`tools/check_import_direction.py` is part of the slice's checks). The `format` diagnostic lives in
  `schema_diagnostics.py`, which Spec 56 §3 already makes the one reducer for all ingress.
- **Identity.** Resource identity is the `version` string, not schema bytes, so an in-place refactor changes no closure identity. The unsupported-version contract (Spec 56 §3.1) reads the `_SCHEMAS` registry,
  not files, so archiving a file no registry names cannot change a diagnostic.
- **Packaging.** `force-include "schemas"` is recursive; parts ship with no `pyproject.toml` change, and `schema_resource()` already prefers the packaged copy (verified in `resources/__init__.py`).
- **#591.** The design keeps §3.2's rule (additive in place, incompatible by bump) and adds only what the rule is silent about (F12). #573 (layout-profile in place) and #582-#588 (Project/View/Theme in place)
  compose with it because the equivalence gate treats pure optional-property additions as allowed.
- **#574/#575.** No overlap: the parts are wheel-owned schemas, not corpus; the gate discovers documents by `git ls-files`, not fixed directories, so #575's fixture moves cost nothing.

## Findings

**F1 / A1. A `$ref` to a part is resolved lazily, and there are three mechanisms plus twenty-odd sites.** A URN reference is looked up when the validator evaluates that keyword, so a schema that gains a
cross-file `$ref` fails only on inputs that reach it. Today `contracts/resources.py` uses a `referencing.Registry`, `operational/resources.py` a deprecated `RefResolver` with a hand-listed 9-schema store, and the rest a
bare validator; 17 construction sites in `src/`, 9 in `conformance/` and `tools/`, and 17 in tests. Amendment: one `chrona.resources` factory and registry, all sites migrated, a guard test on `Draft202012Validator(`
outside it, and a static gate resolving every `$ref` of every live schema (design D1). Without the static gate the first sign of a missed registration would be a production `Unresolvable` on a rare document.
`tools/schema_annotations.py` validates examples with a bare validator through `descend`, which raises on a node whose example contains an external `$ref`; it migrates too.

**F2 / A2. Tools that read schemas do not follow `$ref`, so moving an enum silently shrinks their output.** `presentation_coverage._vocabulary` and `corpus_coverage._schema_values` collect literals by walking the
tree; `vocabulary_inventory` resolves a JSON pointer inside one file; `check_view_dispatch_reachability` collects `enum` values from a schema. After an enum moves behind `$ref`, none of them sees it: the coverage
denominator shrinks with no failure. The last one already shows the rot: it reads `schemas/view-v0.20.schema.yaml`, not the live v0.28, so it currently checks a version no resource may use. Amendment: these readers
consume `dereferenced_schema` and the slice compares their declared-value output before and after (design D1, plan S2, S5).

**F3 / A3. A part is a shared blast radius, and existing parts already are.** `presentation-resource` is resolved by seventeen View schemas, two icon-catalog schemas and summary-profile; `revision-store-resource-ref`
by command-request, automation-result and snapshot-ref. An in-place edit to either retro-changes historical and live schemas at once, and the #591 guard, which compares only version bumps, would not notice a part edit.
Amendment: frozen definitions with a digest lock in the inventory, new part versions for any change, and `presentation-resource` and `revision-store-resource-ref` untouched in #662 (parity-tested against `common`).
Consequence accepted: two parts keep their own copies of sha256 and paths, so the literal grep (F4) is scoped.

**F4 / A4. Acceptance rows 1 and 3 are not literally satisfiable as worded.** Row 1's grep would still match 44 non-live schema files (and the Keep tier stays); it must be scoped to `live` entries (D8, owner).
Row 3's "before and after" has no definition and no record: the prototype found 4 committed documents that do not validate under a naive version-to-schema mapping
(`conformance/implementation-delivery-roadmap-v0.1.yaml`, `conformance/layout-profile-invalid-offset-v0.2.yaml`, `docs/examples/operational-workflows/accepted-capture-command.yaml`,
`examples/controller-z/profiles/summary.yaml`), and 22 files carry no `version` at all. Amendment: S0 reuses no production loader, derives the mapping independently, lists each expected-invalid document with a
reason, and adds a structural layer (dereferenced-schema equality) that proves equivalence for pure refactors without needing any document. The corpus is weak evidence for rejections (almost every committed document
is valid), which is why the structural layer and a probe matrix exist.

**F5 / A5. Diagnostics are user-visible and the reducer has no `format` rule.** `_explain` handles enum, const, required, additionalProperties, type, bounds and pattern; a `format` violation falls to jsonschema's
own message, `'2026-13-45' is not a 'date'`, which echoes the value, against Spec 56 §3 ("No raw value is echoed"), and `_rule_rank` gives it the lowest rank. The `pattern` message prints the regex, so any changed
regex (T3) changes the message; a calendar regex would print about 300 characters. AGENTS.md: "a user-visible ... validator failure is not automatically an internal detail". Amendment: add a `format` rule and message, amend
the rule list in Spec 56 §3, and record every message change in the gate's expected-delta list with a test.

**F6. `$`-anchored patterns accept a trailing newline, and `\d` matches Unicode digits.** Verified with `jsonschema` 4.26: `sha256:` plus 64 hex plus `\n` passes `^sha256:[0-9a-f]{64}$`; `a.yaml\n` passes the strict path;
`２０２６-09-30` passes the date pattern. JSON Schema patterns are ECMA-262 where neither holds. This is a real, small defect that the unification would otherwise copy into a new shared file. Amendment: T3 (design D3),
`(?![\s\S])` and `[0-9]`, classified with T2.

**F7. Spec 56 §3.2 is silent on three things the work needs.** (a) A pure refactor with no accepted-value change (the guard compares only bumps, and only the three named kinds); (b) widening an enum (D4);
(c) an error that moves earlier without changing which working inputs are accepted (D2, T1). Amendment: three sentences in Spec 56 §3.2, each with the test named in the design. These are owner-level
because they reinterpret a normative rule.

**F8 / A6. B4 is defence in depth, and the guard must not break real workspaces.** Verified in source: `authoring_commands.apply_authoring_command` reads `command["target"]["path"]` only in `!= workspace_path.name`
(and echoes it into a rejected result's `detail`, `run chrona workspace revision {path}`, so a newline or terminal escape in `path` reaches the operator's terminal); `payload.directory` is checked by `_relative` in
`authoring_materialization` and again by `_relative` in `cas_write_authoring_aggregate`; `payload.preset.path` is written into the workspace and re-validated by the authoring-workspace schema's strict pattern and by
`_child`. There is no traversal path. What the guard buys: earlier, uniform rejection and no control characters in echoed text. The trap: the issue's proposed strict pattern would reject a workspace called
`my plan.yaml` or `計画.yaml`, which works today because `path` must equal the file name. Amendment: `fileName` for `target.path`, `safeRelativePath` for the other two, and a probe matrix that records today's verdict first.
**Verified:** the three fields' schema text, the two consumers above, the aggregate writer's per-name `_relative` and single-top-level rule, and that no existing test exercises traversal. **Not audited:** Windows
path semantics (`Path(value).is_absolute` and backslashes), symlink behaviour of the staged directory, whether `chrona workspace` subcommands read `path` elsewhere, and any consumer outside this repository.
The loose address family (`layout-profile`, `revision-store-resource-ref`, `render-context`) accepts NUL, backslashes and embedded newlines, and its lookahead only sees the first line; whether store adapters
normalise before joining was not audited, so N5 keeps it unchanged and flags it for a successor.

**F9 / A7. Identifiers must not be unified.** Measured over every `id`/`*Id` site with only `minLength: 1` (18 of 29 live schemas, not six): rejecting whitespace newly rejects 10 committed documents and the layout-profile
letter-first form rejects 14. The offenders are View `tableColumns[].id` values used as display headers (`Work package / gate`, `作業ストリーム`, `Δ`, `#`) and the actual-set v0.2 observation id `supplier:FW-42`.
The issue's "spaces and control characters are accepted in some places" is correct and, for spaces, intended. Amendment: define `identifier` (no control characters) and keep `slug`, `portableName` and layout-profile's id;
adopt at each kind's next bump (N1).

**F10 / A8. Scene is a sibling of the catalog geometry, not a copy.** Scene's circle, rect and path-command shapes reference `number`/`positive` without the 0..256 bounds and the `maxItems` of the catalog. Sharing would
tighten Scene v0.7 (a bump) or loosen the catalog. Amendment: `graphics` holds only the bounded catalog/source geometry; a parity test ties Scene to it (catalog values are valid Scene values, kind sets equal). The
theme-asset-source and icon-catalog pattern shells also cannot be shared because `patternPrimitive` resolves differently in each (source: circle, rect, line, arc; catalog: circle, rect, lowered path); the structural
duplicate detector over-reports here because it compares `$ref` text, not targets. The dereferenced comparison in S0 does not have that blind spot.

**F11 / A9. authoring-workspace's guided annotation may not yield a valid View.** The guided annotation anchor is `{kind, id}`; View v0.28 requires `facet` and `endpoint`, and `_apply_view_overrides` appends guided
annotations to the View body as authored. Reproduction attempt (test harness from `test_authoring.py`, a guided annotation override): the workspace schema accepted it, then normalisation raised
`yaml.representer.RepresenterError` on the frozen annotation mapping, before any View validation. No test covers guided annotations. This is either a latent defect or a harness artefact; it is not diagnosed here.
Amendment: do not change the anchor in #662; open a successor issue. It is the one part of B2 the design leaves open.

**F12 / A3. The inventory guard does not see refactors or part edits.** `validate_version_evolution` compares bump pairs newer than View 0.28, Layout 0.9, Project 0.7; an in-place `$ref` replacement in `view-v0.28`
is invisible to it, as is a part edit. The equivalence gate (S0) and the frozen-digest lock are the added checks; F7 (a) writes the rule.

**F13. Concurrency.** #573's I573-1 edits `layout-profile-v0.9` in place; #582-#588 add optional fields to Project, View and Theme in place. `view-v0.28.schema.yaml` is a single 700-plus-line file with 3 `$defs`, so
every View-touching #662 slice is a conflict candidate. Amendment: slices that edit `layout-profile-v0.9` wait for I573-1; every View slice is a line-local replacement, checked with `git merge-tree` against open PRs that
touch the file, rebased immediately before merge; the gate allows additive optional properties so it never blocks #573 or #582-#588.

**F14. Living-document drift.** `schemas/README.md` lists View v0.14, Layout v0.4 and Render Context v0.13 as live (live: v0.28, v0.9, v0.16). The inventory's `consumers` field is unchecked: every transitioning
View entry names `resources.py`, which mentions only v0.26-v0.28. Amendment: README refreshed; for `live` entries the inventory tool verifies that each consumer file mentions the schema file name or a part it
resolves (S6).

**F15. Performance (measured, small).** External URN `$ref` +8% per call with a reused validator, +50% when the validator is rebuilt per call, which every current site does. The factory caches; the Material catalog
test (10 s budget, 4,015 entries) and an entry micro-benchmark are re-run in S3.

**F16. Code twins of schema constants.** Three Python copies of the `portableName` regex, two of the month forms (`axis.py`, `axis_names.py`), and three of the visual profiles (`cli.py`, `visual_capabilities.py`,
`resources.py` defaults) exist. Sharing the schema does not reach them. Amendment: parity tests, not a runtime schema read.

## Effect on the literal acceptance rows

| # | Row | After this review |
| ---: | --- | --- |
| 1 | parts exist; grep finds no inline copy | achievable if scoped to live entries and the two frozen parts (D8, owner) |
| 2 | each B resolved; path guard | B1 alias, B2 enums by shared vocabulary with subsets (anchor open, F11), B3 subsets, B4 guard (`fileName`), B5 not unified with reasons, B6 one def, B7 kept free text with reasons, B8 D2 |
| 3 | equivalence gate | needs S0 as defined (F4); deliberate tightenings are exactly the T rows |
| 4 | #591 classification | the register in D3; three sentences in Spec 56 §3.2 (F7) |
| 5 | archive unused; gates pass | 38 files in three tiers with evidence (D6); the Keep tier is not "unused" |

## Owner decisions needed before code

D1 loader ownership and the digest lock; D2 option A or B; D3 T1, T2, T3 classification and N5's deferral; D4 alias and canonical spelling; D5 successor issue for the guided anchor;
D7 descope the envelope; D8 scope of row 1. Everything else in the implementation plan is internal to the approved contracts.
