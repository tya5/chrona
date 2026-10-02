# Design — Shared Schema Parts (#662)

**Plan:** [design plan](../archive/planning/issue-662-schema-parts-design-plan-2026-09-30.md); **review:** [architecture review](../archive/reviews/issue-662-schema-parts-architecture-review-2026-09-30.md), whose amendments (A1-A9) are part of this design;
**mechanics:** [implementation plan](../archive/planning/issue-662-schema-parts-implementation-plan-2026-09-30.md). Evolution rule: [Spec 56 §3.2](../specification/56-schema-authoring-and-diagnostics.md).

Each decision below states the recommendation and its consequence. Those marked **owner** change a public contract or reinterpret Spec 56 and need the owner's word
before code; the rest are internal to the approved contract. Nothing here edits a schema; the parts, loader and gate are implementation slices.

## Principles

1. **A refactor must be provable.** Replacing an inline definition by a `$ref` must leave every schema's fully dereferenced form unchanged (design D1, plan S0). A change to an accepted value is a
   *tightening* or a *widening*, listed in the register (D3), never a side effect of moving text.
2. **Share a concept, not a coincidence.** Two definitions are unified only where they name the same concept and today accept the same values. Where committed data or a layer boundary shows they
   differ on purpose, the difference is kept as a named subset or a sibling (D3, D5, graphics).
3. **A part is frozen once published.** Existing `$defs` in a part never change meaning; a change is a new part version. This is what keeps historical and transitioning schemas, and other live
   consumers, from being retro-changed by one edit.

## D1. How shared parts are referenced, loaded and packaged (owner: reinterprets loader ownership)

**Ids.** `urn:chrona:common-v0.1`, `urn:chrona:vocabulary-v0.1`, `urn:chrona:graphics-v0.1`, matching the two existing parts (`urn:chrona:presentation-resource-v0.1`,
`urn:chrona:revision-store-resource-ref-v0.1`). The other `$id` styles in the tree (`chrona/x-vN`, `timeline/project-...`, `https://chrona.dev/schemas/...`) are not extended: a relative `$ref` to a
filename would resolve against those non-URL bases into the wrong id. Files: `schemas/common-v0.1.schema.yaml`, `vocabulary-v0.1.schema.yaml`, `graphics-v0.1.schema.yaml`. Each declares
`$schema` (required: `referencing.Resource.from_contents` raises `CannotDetermineSpecification` without it; measured), `$id`, `title`, `description` and `$defs` only, and asserts nothing at its root.
References are `urn:chrona:common-v0.1#/$defs/isoDate` and so on.

**Part lifecycle.** Each part is a `live` inventory entry (kinds `schema-part-common`, `-vocabulary`, `-graphics`; the two existing parts keep theirs). Adding a `$defs` entry to a part version is
allowed. Changing or removing one is not; it is a new URN (`common-v0.2`), and each consumer moves when it next bumps. The inventory entry records a canonical digest per definition
(`frozenDefs`), and `tools/schema_inventory.py` fails when an existing digest changes. Consequence: the #591 guard compares only bumps, so it would not see a part edit; the digest lock is the missing check (review F12).
Historical and transitioning schemas never reference the new parts; only live entries do (D8).

**Registry and validator factory (recommended).** `chrona.resources` gains one cached `schema_registry()` (a `referencing.Registry` of every part in an explicit `SCHEMA_PARTS` tuple, loaded through
`schema_document`) and one `schema_validator(name)` returning `Draft202012Validator(schema_document(name), registry=schema_registry(), format_checker=<date only>)`. Every current construction site
moves to it: 17 in `src/` (contracts `_registry()` and its four validator sites, core validation, profiles, importer, layout profile, theme inheritance, review detail, scene serialization, authoring command,
preset library, example registry, operational resources), the 6 conformance scripts and `tools/schema_annotations.py`. `jsonschema.RefResolver` (deprecated) in `operational/resources.py` and its 9-name store are removed.
A guard test parses `src/`, `tools/` and `conformance/` and fails on `Draft202012Validator(` outside the factory. Why: a URN reference resolves lazily, so a missing registration raises
`Unresolvable` only when an input reaches that `$ref`; today three different mechanisms coexist (a registry, a deprecated resolver, nothing). A static gate additionally resolves every `$ref` of every live schema
against the registry (`E_SCHEMA_REF_UNRESOLVED`) so absence is caught without an input.
`validate_project(..., schema_path=...)` accepts a caller-supplied schema; it goes through the factory too, with the file's own `$id` added to the registry view.

**Tools that read schemas standalone.** Two read-only functions in `chrona.resources`: `bundled_schema(name)` (the schema plus each referenced part embedded under `$defs` by its `$id`, the JSON Schema
2020-12 compound-document form, so a bare validator with no registry validates it) and `dereferenced_schema(name)` (external `urn:chrona:` references replaced by their target subtree, local references in
that subtree resolved, for analysis, never for validation). Readers migrate as follows: `tools/schema_annotations.py` validates examples through the factory (a bare validator raises `Unresolvable` on a
node whose example contains an external `$ref`); `presentation_coverage`, `corpus_coverage`, `vocabulary_inventory` and `check_view_dispatch_reachability` walk literals without following `$ref`, so they read
`dereferenced_schema`; `vocabulary_inventory`'s policy pointers are re-resolved against the dereferenced tree. Their declared-value output is compared before and after (plan S2) and must be equal except for
documented path changes. Consequence: without this step a moved enum silently drops out of the coverage denominator (review F2).

**Packaging.** No `pyproject.toml` change: the wheel `force-include` of `schemas` is recursive, so the parts ride along; `schema_resource()` already prefers the packaged copy. `test_packaged_resources.py` adds the
three parts to its byte-identity list; `tools/wheel_smoke.py` builds the registry from the installed wheel and validates one document that reaches each part. Archived files go outside `schemas/` (D6) so the
recursive include does not keep shipping them.

**Rejected.** Build-time inlining (a generated duplicate is the drift being removed, and `test_schema_resources_resolve_to_the_source_authority` assumes the file is the authority); a filename-relative `$ref`;
loading every `schemas/*.schema.yaml` into the registry by glob (as the conformance scripts do today): a part is available only by explicit listing, so a stray or archived file cannot become a `$ref` target.

**Performance (measured).** With a reused validator an external URN `$ref` costs +8% over a local one on a small definition (101 us vs 110 us per call); constructing a validator per call costs +50%
(114 us vs 172 us). All current sites construct per call. The factory caches the validator per schema name; the 4,015-entry Material catalog test (10 s budget) is re-run in S3.

## D2. `isoDate` and the calendar (owner: tightening)

Today, for every `^\d{4}-\d{2}-\d{2}$` site, these strings are accepted by schema validation: `2026-13-45`, `2026-02-30`, `2026-00-00`, `0000-01-01`, `2026-02-29` (2026 is not a leap year), `２０２６-09-30`
(Python `\d` matches Unicode digits; JSON Schema patterns are ECMA-262, where `\d` is ASCII), and `2026-09-30\n` (Python `$` matches before a final newline). Unquoted YAML dates that are impossible never reach a
schema: PyYAML raises `ValueError` while loading. Downstream, Project rejects an impossible date with `E_SCHEMA "Expected ISO Date, got ..."` from `as_date` (measured for `2026-13-45`, `2026-02-30`, Unicode digits);
presentation code calls `date.fromisoformat` unguarded at six sites (`v05_content.py` x4, `projection.py` x2), whose surfacing is unverified.

| Option | What it does | Consequence |
| --- | --- | --- |
| A. Shape only, stated | keep the pattern, make it ASCII and newline-proof: `^[0-9]{4}-[0-9]{2}-[0-9]{2}(?![\s\S])`; document that calendar validity is a semantic-phase rule | rejects only Unicode digits and the trailing newline; every impossible date still passes the schema |
| **B. Shape plus `format: date` (recommended)** | A's pattern plus `format: date`, asserted by a `FormatChecker(["date"])` in the factory | rejects impossible dates at the schema stage with a pointer; needs a `format` rule in `schema_diagnostics._explain` (it currently falls to jsonschema's message, which echoes the value, against Spec 56 §3) and the rule list in Spec 56 §3 amended; scene v0.7's existing `format: date`, inert today, becomes asserted |
| C. Calendar regex | a leap-year-exact regex | works with no format checker but is about 300 characters, and the `pattern` diagnostic prints the regex to the author; rejected |

Keeping the pattern with the format is deliberate: `jsonschema`'s `date` checker has differed across supported versions (`>=4.18`) in what it accepts beyond `YYYY-MM-DD`.
Newly rejected by B: strings of the right shape that are not calendar dates, in these kinds: actual-intake-batch, actual-set, authoring-command, authoring-workspace, project and view (window and annotation `date`),
and scene (`date` def). Corpus evidence (prototype, 211 committed documents): 0 documents newly rejected. **Classification:** Spec 56 §3.2 reserves a bump for a change that "makes an existing resource
invalid". No resource that renders today becomes invalid (every value B rejects is already rejected later), but the rejection moves earlier and changes its message and code. Recommendation: a declared exception,
recorded in Spec 56 §3.2 as "an error moved earlier without changing which working inputs are accepted is in place", with a test per kind. If the owner does not accept that reading, use A now and record B as a
batched change for each kind's next incompatible bump; the issue permits "a stated decision not to check".

**Stated decision (2026-10-01, delegated by the lead because the owner could not answer in time; revisitable): no calendar check in the schema.** `isoDate` stays pattern-only and byte-exact
to today's `^\d{4}-\d{2}-\d{2}$` (the anchor and Unicode-digit behaviour are T3, below). The factory stays without a format checker, so `format: date` is asserted nowhere (scene v0.7's `format: date` stays inert).
Project keeps its runtime `as_date` check (`E_SCHEMA "Expected ISO Date, ..."`), and the presentation `date.fromisoformat` sites stay as they are. This is the "stated decision not to check" that the issue's row
allows. Reason: making the schema reject an impossible date (option B) tightens the accepted set of seven kinds and moves a code, a stage and a message, which is a #591 compatibility question the owner has not ruled
on; option A is a smaller tightening of the same kind (Unicode digits, trailing newline) and waits on the same ruling. Consequence: the S1e slice is docs only (one Spec 56 §3.2 sentence recording this decision,
no code); the `format` diagnostic rule (S1b) stays implemented and dormant. **Revisit on an owner ruling:** the work to adopt B later is the factory checker plus the `isoDate` pattern change plus the probes listed
in T2; nothing built so far has to be undone.

## D3. Tightening and widening register (owner)

**Status of the rows (2026-10-01, owner-delegated to the lead):** T1 is **adopted** (slice S1d: the acceptance row requires the traversal guard). T2 is **not adopted** (stated decision, D2). T3 is **not adopted**:
the existing sites keep `$`, and the frozen parts keep whatever anchor they carry; the new defs `fileName` and `identifier` are already newline-proof. Both T2 and T3 are kept in the table as the revisit
record, for the same reason (tightening accepted values is a #591 incompatibility question with no owner ruling yet). `ACCEPTED_TODAY` in `tests/unit/tools/test_schema_parts.py` pins the strings that a later adoption
would flip. N1-N5 and W1 are unchanged.


Classification uses Spec 56 §3.2: in place when no working resource changes; an incompatible bump otherwise. `T` rows tighten, `W` widens, `N` is unified with no value change.
"Corpus" is the prototype run over the committed documents; the S0 gate makes it permanent.

| # | Change | Kinds affected | Corpus | Recommended classification | Test |
| --- | --- | --- | --- | --- | --- |
| T1 | authoring-command guards: `target.path` gets `fileName` (non-empty, not `.` or `..`, no `/`, `\`, control chars), `payload.preset.path` and `payload.directory` get `safeRelativePath`; ids stay `minLength 1` | authoring-command v0.1 | no committed command file | in place: every value rejected is already rejected downstream (`E_AUTHORING_BASE_REVISION`, `E_AUTHORING_MATERIALIZE_PATH`, workspace schema); only the code and stage change. **Measured at S1d (2026-10-01):** this holds for `payload.preset.path` and `payload.directory` (every newly refused value was already refused by the workspace contract or the materializer) and for separators, `.` and `..` in `target.path`; it does not hold for a backslash or control character in the workspace file name, which `apply_authoring_command` accepted when the file carried exactly that name on a POSIX file system. That narrowing is deliberate and recorded in the register test; `preset.yaml\n`-style trailing newlines stay accepted by the strict path because T3 is not adopted. `fileName` deliberately does not use the strict charset, because `target.path` must equal a real workspace file name that may contain spaces or non-ASCII | a probe matrix (traversal, absolute, backslash, NUL, newline, `.`/`..`, spaces, non-ASCII) through `parse_authoring_command` and `apply_authoring_command`, recording today's verdict and the new one |
| T2 | `isoDate` calendar (D2, option B) | actual-intake-batch, actual-set, authoring-command, authoring-workspace, project, view, scene | 0 of 211 | declared exception (or option A) | one impossible-date probe per kind, plus Unicode-digit and newline probes |
| T3 | anchor hardening: `$` becomes `(?![\s\S])` in the shared `sha256Identity`, `safeRelativePath`, `isoDate`, `slug`, `portableName` (Python's `$` accepts one trailing newline; verified for sha256 and the strict path) | live kinds that inline sha256 or the strict path, except the two frozen existing parts: actual-intake-batch, actual-set, authoring-command(-result), authoring-workspace, automation-result, command-request, icon-catalog v0.4, layout-profile, materialization-receipt, preset-library, presentation-preset, profile-package, project, render-context, scene, theme v0.14. View, icon-catalog's envelope and summary-profile are **not** affected: they inherit `presentation-resource`, which stays frozen (D7) | 0 | in place, same exception as T2; or keep `$` byte-exact (a documented caveat) if the owner declines | probes with a trailing newline for each def; a parity test that `presentation-resource`'s copies equal `common`'s except the anchor |
| N1 | identifier: define `identifier` (non-empty, no control characters, spaces and Unicode allowed) but **do not unify existing ids** | none now | see below | none; adopted by each kind at its next bump (batched, §3.2) | a test that no live `id` site newly rejects any committed value |
| N2 | value formats: one `valueFormat` vocabulary with declared subsets | view, summary-profile | 0 | in place, no value change | subset-of-superset test; each context's accepted set unchanged (S0 L1) |
| N3 | visual profiles, month forms, annotation purpose and placement: shared enums | render-context v0.16, presentation-preset, preset-library v0.2; view v0.28, axis-name-tables; view, authoring-workspace | 0 | in place, no value change | S0 L1 equality; code-twin parity (below) |
| N4 | license `{spdx, notice}` shared by the two asset schemas; **color-scheme stays free text** | icon-catalog v0.4, theme-asset-source; color-scheme unchanged | 6 schemes say `project-pending` | in place, no value change | probe: `project-pending` still accepted by color-scheme |
| W1 | View anchor `endpoint` accepts `end` (D4) | view v0.28 | n/a | in place widening; existing resources stay valid | `end` and `finish` produce byte-identical Scene |
| N5 | the loose address family (layout-profile, revision-store, and render-context's variant) keeps today's regex in a named def; render-context keeps its own named def | layout-profile v0.9, revision-store-resource-ref (so command-request, automation-result, snapshot-ref), render-context v0.16 | 0 | none. Tightening the shared revision-store part changes four kinds at once; do it at the next bump of each | probes recording that NUL, backslash and embedded-newline addresses are still accepted, with the reason |

**Why identifiers are not unified (N1).** A scan of every `id`/`*Id` site with only `minLength: 1` (18 of the 29 live schemas) against candidate patterns: rejecting whitespace (`^[^\s\x00-\x1f\x7f]+$`) newly
rejects 10 committed documents, and the layout-profile letter-first form (`^[A-Za-z][A-Za-z0-9._-]*$`) rejects 14, all View `tableColumns[].id` values such as `Work package / gate`, `作業ストリーム`, `Δ`, `#`
(these ids are display headers) and the actual-set v0.2 observation id `supplier:FW-42`. Rejecting only control characters newly rejects nothing, which is why `identifier` is defined that way, but adopting it in
place would still be a tightening of every kind that carries an id, including the presentation-resource envelope shared by View, icon-catalog and summary-profile. The remaining named families are kept as they are:
`slug` (`^[a-z][a-z0-9-]*$`, example-registry and preset-library), `portableName` (`^[A-Za-z0-9][A-Za-z0-9_-]*$`, three schemas and three Python copies), and layout-profile's `id` stays a local def with its `maxLength`.

**Code twins.** Constants that duplicate a schema value get a parity test (schema value equals the Python value), not a runtime read of the schema: three copies of the `portableName` regex
(`resources.py`, `importer.py`, `normalizer.py`), the month forms (`layout/axis.py`, `model/axis_names.py`), and the visual profiles (`cli.py`, `scene/visual_capabilities.py`).

## D4. Endpoint vocabulary: `finish` versus `end` (owner)

View annotation anchors say `start | finish | at | body`; Project `endpointRef` says `at | start | end`; dependency ports in Layout accept `finish` and `end`; Actual observations say `start`/`finish`. Committed
data uses `finish` in View anchors (3 example Views, 2 fixtures, `conformance/presentation-g2-g4-design-v0.1.yaml`) and the vocabulary policy pins `[start, finish, at, body]`.

- **Recommended: accept both, `end` documented as canonical, `finish` a declared alias.** Widen the View enum to add `end` in place (W1). Normalise `end` to `finish` at contract construction, because the endpoint text
  is embedded in a Scene primitive id (`surface_annotations.py:627`), so an un-normalised `end` would give the same picture different ids. `annotations.py:97,105` and `surface_annotations.py:663` accept both;
  the policy's accepted list gains `end`. No committed YAML changes. `vocabulary` defines `dateEndpoint` (`at, start, end`, Project) and `anchorEndpoint` (`start, end, finish, at, body`, View) with a subset test.
  Consequence: the alias stays until a future incompatible View bump batches its removal; new examples use `end`. The widening is not an optional-property addition, so §3.2's mechanical guard does not
  apply, but §3.2's own test (existing resources stay valid and behave the same) holds; Spec 56 §3.2 gets one sentence saying so.
- Rename to `end` only: breaks 3 example Views, 2 fixtures, one conformance file and the policy, and needs View v0.29. Rejected as disproportionate for a naming alignment.
- Leave both: keeps the drift; rejected because it is the finding.

## D5. authoring-workspace and View (owner for the anchor)

Verified: the annotation `purpose` (4 values) and `placement` (`side` above/below/start/end, `alignment` start/center/end) are identical in the two schemas; `visibility.annotations` and `relations` are
**deliberate subsets** (guided overrides are a closed vocabulary that "cannot alter" semantics, per the schema text). View has 3 `$defs`, so there is nothing to reference until definitions are extracted.

- **Do not reference View's versioned schema from authoring-workspace.** `urn:chrona:view-v0.28#/$defs/...` would couple authoring-workspace v0.1 to a View version; each View bump would repoint it, the
  collision #591 removed. Both schemas instead reference `vocabulary`: `annotationPurpose`, `annotationSide`, `annotationAlignment` (exactly shared) and `annotationVisibilityMode` with the named subset
  `guidedAnnotationVisibilityMode` (`none, presentation, all`), and `relationVisibilityMode` with `guidedRelationVisibilityMode` (`none, semantic`). Subsets are separate enums in `vocabulary` plus a
  subset-of-superset test, not an `allOf` intersection: an intersection produces two enum errors and worse Spec 56 diagnostics. No accepted value changes (N3).
- **The anchor is a different matter.** A guided annotation's `anchor` is `{kind, id}`; View's requires `facet` and `endpoint`, and `_apply_view_overrides` appends the guided annotation to the View body
  as authored. Either guided annotations cannot yield a valid View today, or a step not found in this review supplies the fields. A harness run of a guided annotation raised `RepresenterError` before
  validation (review F11), so the question is open. Recommendation: do not change the anchor shape in #662; open a successor issue to diagnose the guided-annotation path. If it is confirmed broken, aligning
  the guided anchor to View's (facet and endpoint required) is a tightening of authoring-workspace v0.1, to be classified then. Consequence: B2's "authoring-workspace behind View" is closed for the enums and
  left open, honestly, for the anchor.

## D6. Which historical schema files may be archived (evidence, not guesses)

The `transitioning` inventory entries name `consumers` and `removalSlice`, but no tool checks either (the consumer field lists `resources.py` for every one, including files that file never mentions). Evidence used here:
(1) file-name references in `src/`, `tests/`, `tools/`, `conformance/`, `.github/`, `pyproject.toml`; (2) accepted versions in the runtime registries (`_SCHEMAS`, `theme_inheritance`, `scene/serialization`);
(3) committed documents that declare the version (`examples/`, `src/chrona/resources`, fixtures, `conformance/`, `docs/examples/`); (4) inventory and migration tooling: `presentation_coverage._validate_resource_versions`
reads every live and transitioning entry's version to decide which resource versions slides may declare, and `validate_version_evolution` reads only pairs newer than the baselines (View 0.28, Layout 0.9, Project 0.7);
there is no migration tool that reads an old schema. Data is the 44 non-live files.

| Tier | Files | Evidence | Precondition |
| --- | --- | --- | --- |
| Keep (6) | view v0.26, v0.27; theme v0.11, v0.12; icon-catalog v0.3; scene v0.6 | accepted at runtime and/or committed documents at that version (view v0.27: 24; theme v0.11: 23; icon-catalog v0.3: 4; scene v0.6: 29 generated scenes, read by `presentation_coverage`) | removed only with their own migration issue |
| 1 (21) | actual-set v0.2; layout-profile v0.7, v0.8; profile v0.2; render-context v0.13, v0.14; scene v0.1-v0.5; theme v0.5-v0.7; view v0.12, 13, 16, 17, 18, 21, 25 (433 KB) | no executable file-name reference; version not accepted by any registry; no committed document (actual-set v0.2 has one docs example, see below) | edit docs that name them; drop their inventory entries |
| 2 (11) | layout-profile v0.4, v0.5; preset-library v0.1; render-context v0.12; theme v0.9, v0.10; view v0.15, 19, 22, 23, 24 (261 KB) | only `tests/integration/test_packaged_resources.py` lists them (a wheel-shipping expectation) | edit that list |
| 3 (6) | layout-profile v0.3 (`tools/wheel_smoke.py` asserts it ships); view v0.20 (`check_view_dispatch_reachability.py` reads it: a stale pin, the live View is v0.28); render-context v0.15, theme v0.8, view v0.14 (pinned by `conformance/declared-vocabulary-policy-v0.1.yaml`); project v0.6 (a stale `conformance/validation.json` entry under a non-existent `docs/schemas/` path) (127 KB) | each is named only by a tool or policy that should point at a live schema | retarget the tool/policy to the live schema first (the policy's pointers must be re-resolved and `accepted` re-checked) |

`docs/examples/operational-workflows/actual-set-v0.2.yaml` declares a version no runtime accepts (it is unsupported input); the slice converts or removes that example with the schema. Destination for archived
files: `docs/archive/schemas/` with a short README, `git mv`, outside `schemas/` so the wheel stops shipping them (wheel budget 5,000,000 bytes compressed; the recursive include otherwise keeps them);
inventory entries removed in the same commit (`E_SCHEMA_INVENTORY_COVERAGE` demands file and entry agree); relative links repaired per AGENTS.md. The first three archive slices are independent of any part.

## D7. The resource envelope (owner)

Eleven live schemas inline `{version, kind, id, body}`; the shared envelope `presentation-resource` is already referenced by View, icon-catalog and summary-profile. Its only real constraints are `id` and
`kind` non-empty, and moving eleven schemas to `allOf: [{$ref: envelope}, {...}]` changes each one's diagnostic shape (Spec 56 §3 reduces `allOf` branches) for a four-line saving. Recommendation: **descope**
the envelope from #662 and record it in the acceptance review as deferred with a successor, unless the owner wants it; if kept, it is the last optional slice, gated by diagnostics equivalence on the
committed invalid documents. **Decided 2026-10-01 (owner, #715): no shared envelope**; the eleven inline envelopes stay ([#715 record](../archive/planning/issue-715-schema-parts-leftovers-plan-2026-10-01.md), D3). `presentation-resource` itself is **not touched** in #662 (seventeen View schemas, two icon-catalog schemas and summary-profile resolve it; a change would retro-change them).

## D8. What "no inline copy outside the common schema" means (owner)

The 44 non-live schema files keep their inline copies until archived or migrated, and the Keep tier stays. The literal grep therefore cannot pass repository-wide. Recommendation: the acceptance row is defined
as "no inline copy of the shared patterns in any `live` inventory entry other than the parts", enforced by a test that reads the inventory; historical entries are frozen, never re-pointed (re-pointing a
transitioning schema would change what an accepted historical version accepts). The two existing parts (`presentation-resource`, `revision-store-resource-ref`) are frozen and keep their own copies of sha256 and the paths;
a parity test proves they equal `common`'s definitions, except the T3 anchor. **Decided 2026-10-01 (owner, #715): this scope stands, with no `-v0.2` part for the frozen parts; the remaining inline copies leave with their `transitioning` removal slices** ([#715 record](../archive/planning/issue-715-schema-parts-leftovers-plan-2026-10-01.md), D1). Making them reference `common` would need new part versions and a re-pointing of View v0.28, icon-catalog and summary-profile at the next bump. The gate also fails a `live` schema that copies a pattern a part already defines.

## Learnings from S1c (recorded 2026-10-01)

- **A `$ref` union branch changes the message.** `schema_diagnostics._union_forms` reads a branch's own `required` and `properties` to name the permitted forms. A branch that is only a `$ref` exposes none of
  them, so the message for a bad View table-column `width` would change from `expected one permitted form: properties fr; properties minmax` to `... properties minmax`. The S0 L3 probes do not reach table widths, so
  the gate alone would not have caught it; the author compared the reducer output base against head. Consequence: `fractionalTrack` stays **inline at the two View `width` branches** that spell `fr`, it is defined
  but not used by View, and the D8 copy test records this as a deferral. Adopting it there needs `_union_forms` to follow `$ref` with a parity test on the message first (planned in S2, before any vocabulary def is
  used as a union branch).
- **A nullable site cannot sit beside a typed def.** `authoring-command-result`'s `resultRevision` is `type: [string, 'null']`; folding it into `$ref: sha256Identity` (typed `string`) would need an `anyOf`/`allOf`
  and change L1, so it is left inline and recorded as a deferral. Likewise `authoring-command` itself was not edited in S1c (S1d owns it, and the S0 sensitivity tests use its `baseRevision` pattern as their edit target).
- **Defs carry `type: string`.** An adopted site drops its own `type: string`; a site with a sibling of the same keyword would fold into an `allOf` and change L1.
- **The digest lock makes T3 a deliberate act.** Changing an existing def of `common-v0.1` fails the frozen-digest gate by design, so a later T3 adoption needs a new part version (`common-v0.2`) or a
  deliberate digest update stated in the same PR; this is one more reason it waits for the owner.

## Graphics part

`graphics-v0.1` holds what `icon-catalog-v0.4` and `theme-asset-source-v0.1` genuinely share: the integer `viewport` size (1..4096), the tile size (1..256), tile angle, `densityBasisPoints`, the `circle` and
`rect` pattern primitives (with their bounds), `paintMode`, `lineCap`, `lineJoin`, and the stroke/fill conditional rules (`strokePaintRules`, used by the glyph path, the catalog path, the pattern path and
the icon path: five occurrences across the two schemas). It does **not** hold the pattern shell or the primitive union, because the two schemas resolve `patternPrimitive` to different unions (source: circle,
rect, line, arc; catalog: circle, rect, lowered path); a shared shell would need a parameterised `$ref`. `license` comes from `common`. Scene v0.7 is a **sibling, not a copy**: its circle, rect and command
shapes are unbounded on purpose (Scene carries Layout-completed geometry, `number`/`positive`), so referencing the bounded catalog shapes would tighten Scene. A parity test asserts that every catalog primitive and command
is valid Scene geometry and that the kind sets are equal.

**Recorded at S3 (2026-10-01).** The part has eleven definitions: `viewport`, `tile`, `tileAngle`, `densityBasisPoints`, `circlePrimitive`, `rectanglePrimitive`, `paintMode`, `lineCap`, `lineJoin`, and the stroke
rule split in two, `strokePaintRequiresStrokeFields` and `fillPaintForbidsStrokeFields` (a single `allOf` definition cannot replace a site's own `allOf` without nesting it, and a `$ref` beside `properties` folds into an
`allOf` pair; both change the dereferenced form, so each of the two `if/then` rules is its own definition and a site lists both). The pattern shell stays local for the reason above. `viewport`, `tile`, the primitives and the
enums are whole-object or whole-enum definitions, so a site is `{description, $ref}` and keeps its dereferenced form; the asset schemas' `license` is `common#license`. Scene's circle and rectangle are a **looser sibling and
are not forced onto the strict definitions**: their coordinates and sizes are `number`/`positive`, with no 0..256 or radius 128 bound, because Scene carries Layout-completed geometry (a region beyond the authored tile); a
reference would have newly rejected valid Scenes. For the same reason Scene's `iconViewport` and tile sizes stay local. Scene v0.7 **does** reference the definitions that hold no bound it leaves open: the angle, the
density, the three enums and the two stroke rules (each was a byte-equal copy; L1 equal). `theme-v0.13`'s diagonal-hatch `angle` is the same pattern angle and references `tileAngle`. A test proves every valid catalog
primitive is valid Scene geometry, that the kind sets are equal, and that Scene still accepts a circle the strict definition refuses. One coincidental match is recorded as a different concept: layout-profile's grid cell
index and span (`integer`, 1..10000), which equals `densityBasisPoints` structurally.

## Living documents

Spec 56 §3.2 gains: an in-place refactor that leaves every schema's dereferenced form unchanged is allowed; adding a value to an existing enum is an in-place widening when consumers handle it (D4); an error
moved earlier without changing which working inputs are accepted may be in place with a declared list (D2, D3). Spec 56 §3 gains the `format` rule. `schemas/README.md` (lists View v0.14, Layout v0.4,
Render Context v0.13 as live) is refreshed or replaced by a generated table. The inventory's `consumers` field is checked against the referencing files for `live` entries (plan S6).

## Failure behaviour

An unresolvable `$ref` is a gate failure (`E_SCHEMA_REF_UNRESOLVED`), never a runtime fallback. A part whose frozen digest changed is a gate failure. A `format: date` violation is reported as
`SchemaViolation(rule="format", expected=("YYYY-MM-DD calendar date",))` without echoing the value.

## Boundaries

Schemas, `chrona.resources`, the schema tools, conformance, the wheel test list, docs. No Theme, View, Layout, Scene or adapter behaviour changes except the D4 endpoint alias in `presentation/layout/annotations.py`
and `surface_annotations.py` and the D2 `format` rule in `schema_diagnostics.py`.
