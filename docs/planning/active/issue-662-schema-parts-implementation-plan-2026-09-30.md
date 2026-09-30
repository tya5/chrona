# Implementation Plan — Shared Schema Parts (#662)

Design: [design](../../design/issue-662-schema-parts-design-2026-09-30.md), amended by the [architecture review](../../reviews/current/issue-662-schema-parts-architecture-review-2026-09-30.md)
(A1-A9 are part of the design). Baseline and claim checks: [design plan](issue-662-schema-parts-design-plan-2026-09-30.md). This plan is the authority for mechanics.

**Status:** design pack published; the owner decisions listed at the end of the review gate S1c onward (S0, S1a and S5 do not depend on them). No product code is changed by this pack.

## Literal acceptance mapped to slices

| # | Row (short) | Slices | Evidence at release |
| ---: | --- | --- | --- |
| 1 | parts exist; no inline copies | S1c, S2, S3 | parts in the inventory; a test that reads the inventory and fails on a copy of a shared pattern in any `live` entry other than the parts (scope: design D8) |
| 2 | each B resolved; path guard | S1d, S2, S3, S4 | the B register (below) with a test per item; guard probe matrix |
| 3 | validation-equivalence gate | S0 (tool), every slice (run) | gate output recorded per slice in its PR; deliberate tightenings listed in `expected-deltas` with a test each |
| 4 | #591 classification, kinds named | design D3 register; S1e, S1d, S4a | the register rows T1-T3, W1, N1-N5, checked by their tests |
| 5 | archive; inventory gates pass | S5a-S5c | evidence table (design D6), inventory, annotation, reference, packaging and wheel-size gates green |

## The B register (item, resolution, slice, test)

| B | Resolution | Slice | Test |
| --- | --- | --- | --- |
| 1 endpoint | `end` accepted, `finish` alias, normalised to `finish` | S4a | `end` and `finish` give byte-identical Scene; policy accepted list |
| 2 authoring-workspace | shared `annotationPurpose/Side/Alignment`; named subsets for visibility modes; anchor left to a successor issue | S2c, S4b | subset-of-superset test; L1 equality; successor issue filed |
| 3 formats | `valueFormat` with two declared subsets | S2d | subset test; L1 equality |
| 4 paths | `safeRelativePath` (strict), `fileName`, loose `relativeAddress` frozen as is; authoring-command guard | S1c, S1d | probe matrix |
| 5 identifiers | `identifier` defined; existing ids unchanged; id-site inventory test | S1c, S4c | every live `id` site references `identifier` or is on a documented allowlist |
| 6 content identity | one `sha256Identity` | S1c | probes incl. trailing newline; L1 |
| 7 license | `license` shared by the asset schemas; color-scheme stays free text with the reason recorded | S3, S4d | `project-pending` still valid for color-scheme |
| 8 dates | one `isoDate` (design D2) | S1c, S1e | probe per kind |

## Rules for every slice

- One coherent PR per slice ("I662-N ..." titles, `Refs #662`, no closing keywords in title or any commit). Docs-only PRs skip pytest; code PRs run the three Ubuntu shards.
- Before starting a slice that edits `view-v0.28`, `theme-v0.13/14`, `project-v0.7` or `layout-profile-v0.9`, list open PRs touching the file (`gh pr list -R tya5/chrona --search "path:schemas/<file>"`);
  keep the edit line-local; run `git merge-tree` against each such PR; rebase immediately before merge.
- Local checks for schema slices: `tests/unit/tools`, `python -m tools.schema_inventory`, `tools.schema_annotations`, `tools.validate_schema_references`, `tools/check_import_direction.py`,
  `tests/integration/test_packaged_resources.py`, the S0 gate against `origin/main`, and for slices touching presentation code `python -m tools.derived_evidence --check` and
  `python -m tools.regenerate_public_examples --check`. Any derived-evidence change in a slice not meant to change output is a stop-and-report condition. Full pytest is left to PR CI.
- The gate output (three layers, below) is pasted into the PR and into a progress row here. A slice whose gate output differs from its stated deltas stops; the design is amended first.
- Dependency graph: S0 -> S1a -> S1b -> S1c -> {S1d, S1e, S2, S3}; S1f after I573-1; S4a after S2; S5a-c after S0 and independent of the parts (serialise inventory edits); S6 last.

## S0. Validation-equivalence gate (no schema or product change)

**Files.** `tools/schema_equivalence.py`; `tests/unit/tools/test_schema_equivalence.py`; `conformance/schema-equivalence/expected-invalid-v0.1.yaml`;
`conformance/schema-equivalence/baseline-results-v0.1.json` (temporary: removed at S7); `conformance/run_conformance.py` registers a `schema-equivalence` check.
The tool imports nothing from the loader it will later check: it reads `schemas/` directly, builds its own `referencing.Registry` from every schema `$id`, and derives the document-to-schema mapping
itself from each schema's `version` constant (root `properties.version.const` or the enveloping `allOf` branch, plus an explicit override table for `summary-profile` and scene). Independence is the point:
a loader bug must not be able to hide itself.

**Three layers.**
- **L1 structural.** For every schema file, a canonical fingerprint of its *dereferenced* form (external URN and local `$ref` inlined, annotations and unused `$defs` removed). `--base-rev <git rev>` compares
  head to a base revision. Equal fingerprints prove an unchanged accepted set for pure refactors with no document needed. A difference is allowed only when it is a pure insertion of optional properties
  (the `_additive_only_change` rule of `tools/schema_inventory.py`, reused) or matches a line in `expected-deltas` (`{schema, pointer, before, after, reason, test}`); anything else fails with the pointer.
- **L2 corpus verdicts.** Every tracked `*.yaml`, `*.yml`, `*.json` (from `git ls-files`, excluding `schemas/`, `.github/`, `docs/archive/`) whose `version` maps to a schema is validated and recorded as
  `{path, schema, valid, first error: pointer and rule}`. The baseline file holds the verdicts at the S0 base commit; the check fails when a baseline document's verdict or first error changes without an
  `expected-deltas` line. Documents absent from the baseline are checked only for "valid unless listed in `expected-invalid`". The prototype found 211 mapped documents (view v0.27 x24, v0.28 x12; theme v0.11 x23;
  render-context v0.16 x29; layout-profile v0.9 x26; Project x23; ...), 4 invalid (listed with reasons, to be confirmed in S0), and about 100 documents of unmapped versions (scene v0.6 x29 must be mapped in S0).
- **L3 diagnostics.** For each baseline-invalid document and for a probe matrix, the production ingress function (`parse_contract`, `parse_authoring_command`, `validate_project`, `parse_document`, scene
  loader) is called and the `(code, pointer, rule, message)` recorded; message changes need an `expected-deltas` line. The probe matrix is the set of strings the design names (impossible dates, Unicode digits,
  trailing newline, traversal, NUL, backslash, ids with spaces and non-ASCII, the six `finish`/`end` cases) for each kind that has a site, so rejections are evidenced although the committed corpus is almost all valid.
- Inline documents built in Python tests are outside the gate; pytest covers them and must stay green.

**Tests.** Sensitivity (each must fail the gate): edit one pattern in a copied schema; make a valid document invalid; change a message; remove an inventory entry. Pass cases: an added optional property; a
listed delta applied exactly; a pure `$ref` replacement of an identical inline definition (L1 equal). A test that every live kind has at least one document or one probe. Runtime budget recorded; L2 plus L3 must stay
under the conformance step budget (prototype: single pass over 211 documents took seconds).

**Proof of no unintended change.** The slice changes no schema; its own proof is the sensitivity tests. It is run at the S0 base commit to write the baseline, whose diff review lists the 4 invalid documents.

**#573.** None. Additive optional properties (I573-1's `memberNames`) pass L1 and change no baseline verdict, so #573 is not blocked and needs no re-record.

## S1. Loader, common part, authoring-command guard

**S1a. Loader and factory (no schema change).**
Files: `src/chrona/resources/__init__.py` (`SCHEMA_PARTS`, `schema_registry`, `schema_validator` (validator cached by name, no format checker yet), `bundled_schema`, `dereferenced_schema`);
migrate the 17 `src/` construction sites (contracts `_registry()` and four validators, core validation incl. the `schema_path` override, extension profiles (two), icon importer, layout profile, theme inheritance
(two), review detail, scene serialization, authoring command parser, preset library, example registry, operational resources) and remove `RefResolver` and `_schema_store`; `tools/schema_annotations.py` and the six
conformance scripts use the factory; `tools/schema_inventory.py` gains the static `$ref` resolvability gate (`E_SCHEMA_REF_UNRESOLVED`); `tools/wheel_smoke.py` builds the registry from the installed wheel;
`tests/integration/test_packaged_resources.py`.
Tests: `tests/unit/chrona/test_schema_loader.py` (registry contents, missing part raises at the gate not at a document, bundled form validates with a bare validator, dereferenced form has no part `$ref`);
an AST guard failing on `Draft202012Validator(` outside the factory in `src/`, `tools/`, `conformance/`; the static gate on a synthetic unresolved reference.
Proof: S0 L1, L2 and L3 all equal to base (zero deltas); pytest green; `derived_evidence --check` no diff; micro-benchmark recorded (design D1).
#573: none.

**S1b. `format` diagnostic.** Files: `src/chrona/schema_diagnostics.py` (`rule="format"`, rank, message without the value), Spec 56 §3 rule list. Tests in `tests/unit/chrona/test_schema_diagnostics.py`. Proof: S0 L3 equal
(no schema asserts a format yet because the factory has no checker). #573: none.

**S1c. `common-v0.1` and adoption in non-layout live schemas.**
Files: `schemas/common-v0.1.schema.yaml` (`sha256Identity`, `isoDate`, `safeRelativePath`, `relativeAddress`, `relativeAddressDotTolerant`, `fileName`, `identifier`, `slug`, `portableName`, `gitRevision`,
`revisionToken`, `fractionalTrack`, `license`); `schemas/schema-inventory-v0.1.yaml` (three part entries, `frozenDefs` digests; the existing parts get entries only if absent); `tools/schema_inventory.py`
(frozen-digest check, `consumers` check for live entries); adoption edits in actual-intake-batch, actual-set, authoring-command-result, authoring-workspace, automation-result, command-request,
presentation-materialization-receipt, presentation-preset, preset-library, profile, project, render-context, scene, theme-v0.14, view-v0.28 (dates, `fr`), icon-catalog-v0.4 and theme-asset-source (`portableName`).
`presentation-resource`, `revision-store-resource-ref` and `layout-profile` are not edited here.
Two commits in one PR: (1) defs byte-exact to today's regexes (`$` kept), pure refactor; (2) defs take the decided anchors (T3) if the owner accepts it. Tests: `tests/unit/tools/test_schema_parts.py`
(frozen digests, the live-entry copy test of design D8, parity of `common` with `presentation-resource` and `revision-store-resource-ref` except the anchor), Python-twin parity for the three `portableName` copies, and
one probe per def and per adopting kind.
Proof: commit 1 must show L1 equal, L2 equal, L3 equal on every file; commit 2 shows only the T3 deltas, each listed with its test. #573: none (layout-profile excluded).

**S1d. authoring-command guard (T1).** Files: `schemas/authoring-command-v0.1.schema.yaml` (in place, three fields), `tests/unit/chrona/operational/test_authoring_commands.py` and
`tests/unit/chrona/usecases/test_authoring_materialization.py` (probe matrix through `parse_authoring_command` and `apply_authoring_command`: today's verdict recorded first, then the guarded verdict; the matrix
includes a workspace named `my plan.yaml` and `計画.yaml`, which must still work). Proof: L1 deltas exactly `/properties/target/properties/path`, `.../preset/properties/path`, `.../directory`; L2 no document; L3 lists the moved errors.
Requires the T1 owner decision. #573: none.

**S1e. Calendar check (T2), if D2 = B.** Files: factory enables `FormatChecker(["date"])`; `isoDate` adopted at every date site of the six kinds (some were adopted in S1c under A); Spec 56 §3.2 sentence (design F7 c);
tests: impossible-date, Unicode-digit and newline probe per kind; scene `format: date` now asserted, with a test over the committed scenes. If D2 = A, this slice is only the ASCII/newline pattern already in S1c and
the decision is recorded in Spec 56. Proof: L1 deltas exactly the `format` insertions and pattern anchors; L2 equal; L3 lists the changed messages. #573: none.

**S1f. layout-profile adoption.** Files: `schemas/layout-profile-v0.9.schema.yaml` (`sha256Identity`, `relativeAddress`, `revisionToken`, `fractionalTrack`; its `id` def stays). Scheduled after I573-1 merges: rebase on the merged
schema, re-run the gate against `origin/main` so `memberNames` appears as a permitted addition. Proof: L1 equal apart from the T3 anchor deltas and the additive `memberNames` that main already carries. **Depends on #573.**

## S2. `vocabulary-v0.1` (after S1c)

Files: `schemas/vocabulary-v0.1.schema.yaml` and inventory entry with digests; adopting schemas per sub-slice; tools that read literals (`tools/presentation_coverage.py`, `tools/corpus_coverage.py`,
`tools/vocabulary_inventory.py`, `tools/check_view_dispatch_reachability.py` retargeted from `view-v0.20` to the live View and the vocabulary) read `dereferenced_schema`; code-twin parity tests.
Sub-slices, each its own PR: S2a `visualProfile` (render-context v0.16, presentation-preset, preset-library v0.2; twins in `cli.py` and `scene/visual_capabilities.py`); S2b `monthLabelForm` (view x2, axis-name-tables; twins in
`layout/axis.py`, `model/axis_names.py`); S2c `annotationPurpose/Side/Alignment` and the visibility-mode subsets (view, authoring-workspace); S2d `valueFormat` with `tableColumnScalarFormat` and `summaryMetricFormat`
(view, summary-profile); S2e `dateEndpoint` (project) and `anchorEndpoint` without the alias yet.
Proof per sub-slice: L1 equal on every schema (a shared enum is byte-equal to the inline one once dereferenced); the declared-value output of the four readers (recorded with `--emit` before, compared after) is equal, or its
only differences are documented path changes; subset-of-superset tests. #573: none (layout-profile has no vocabulary item). View edits follow the concurrency rule above.

## S3. `graphics-v0.1` (after S1c)

Files: `schemas/graphics-v0.1.schema.yaml` (`viewportSize`, `tileSize`, `tileAngle`, `densityBasisPoints`, `circlePrimitive`, `rectanglePrimitive`, `paintMode`, `lineCap`, `lineJoin`, `strokePaintRules`); adoption in
`icon-catalog-v0.4` and `theme-asset-source-v0.1`, including `license` from `common`; inventory entry. Not adopted: pattern shell, primitive unions, and Scene v0.7 (a sibling).
Tests: parity test tying Scene's circle, rect and path-command shapes to the catalog geometry (valid catalog values are valid Scene values; kind sets equal); the 4,015-entry Material catalog test and an entry
micro-benchmark before and after (budget: no more than 1.25x); `_icon_catalog_envelope`'s `name` regex twin. Proof: L1 equal (license adoption: none, structures are equal); L2 equal including the three catalogs and
the theme-asset-source fixtures. #573: none.

## S4. B resolutions that change behaviour or need a successor

- **S4a endpoint alias (W1).** Files: `schemas/view-v0.28.schema.yaml` (`anchorEndpoint` gains `end`), `src/chrona/presentation/layout/annotations.py` (line 97 set, line 105 branch),
  `surface_annotations.py` (line 663 branch), normalisation of `end` to `finish` at contract construction, `conformance/declared-vocabulary-policy-v0.1.yaml` (accepted list), Spec 06 annotation paragraph, one Spec 56 §3.2
  sentence. Tests: two Views identical except `finish`/`end` render byte-identical Scene; `end` on a point mark and on a span; existing three example Views and two fixtures unchanged. Proof: L1 delta exactly the added enum value;
  L2 equal; derived evidence no diff; the Scene id text (`surface_annotations.py:627`) unchanged for `finish`. #573: none.
- **S4b** file the successor issue for the guided-annotation path (review F11) and for the loose address family (F8); no code.
- **S4c** id-site inventory test (design D3, N1). **S4d** record the color-scheme license decision (Spec 34 sentence and a test that `project-pending` and `MIT` remain valid).

## S5. Archive historical schema files (independent of the parts; serialise inventory edits)

Each sub-slice: `git mv` to `docs/archive/schemas/` (with a short README naming the issue and that git is the record), remove the inventory entries in the same commit, repair relative links in `docs/` (AGENTS.md
archive rule), run the S0 gate with an `archived` delta type, `tools.schema_inventory`, annotations, references, `tests/unit/tools`, `tests/integration/test_packaged_resources.py`, `tools/check_wheel_size.py` on a
built wheel (expected reduction about 0.8 MB uncompressed in total), conformance.
- **S5a tier 1 (21 files, 433 KB):** actual-set v0.2; layout-profile v0.7, v0.8; profile v0.2; render-context v0.13, v0.14; scene v0.1-v0.5; theme v0.5-v0.7; view v0.12, 13, 16, 17, 18, 21, 25. Also convert or remove
  `docs/examples/operational-workflows/actual-set-v0.2.yaml` (unsupported version) and fix the docs that name these files.
- **S5b tier 2 (11 files, 261 KB):** layout-profile v0.4, v0.5; preset-library v0.1; render-context v0.12; theme v0.9, v0.10; view v0.15, 19, 22, 23, 24; drop them from the list in `test_packaged_resources.py`.
- **S5c tier 3 (6 files, 127 KB):** first retarget `tools/wheel_smoke.py` (live layout schema), `tools/check_view_dispatch_reachability.py` (live View plus vocabulary; after S2), the vocabulary policy pointers
  (theme v0.8, render-context v0.15, view v0.14 to the live schemas; re-check `accepted`; a widened declared vocabulary is a finding, not something to silence), and the stale `conformance/validation.json` entry; then archive
  layout-profile v0.3, view v0.20, render-context v0.15, theme v0.8, view v0.14, project v0.6.
- Kept: view v0.26, v0.27; theme v0.11, v0.12; icon-catalog v0.3; scene v0.6, until their own migration issues move their committed documents.
Proof: for every archived file, the evidence table row in design D6 still holds at the PR head (a script re-derives file-name references, registry acceptance and committed-document counts); L1 shows only `archived`
deltas; no `E_SCHEMA_INVENTORY_COVERAGE`. #573: none. Any file that gains a reference after the design date stays.

## S6. Living documents

Spec 56 §3.2 (refactor, widening, moved error: as far as not landed with S1e/S4a), `schemas/README.md` refreshed or generated from the inventory, inventory `consumers` accuracy for live entries, `docs/` link repair.
The remaining owner-decision outcomes (D7 deferral, D8 scope) are recorded in the acceptance review. No code.

## S7. Acceptance review (separate publication, after S0-S6)

`docs/reviews/current/issue-662-...-acceptance-review-...md` with the literal-acceptance marker and a row for every criterion, exact-main CI cited, the temporary baseline removed. Closing the issue is a
separate act after that; the design pack and this plan are archived afterwards per AGENTS.md.

## Progress

| Slice | State |
| --- | --- |
| Design pack (this PR) | published; owner decisions pending |
| S0-S7 | not started |
