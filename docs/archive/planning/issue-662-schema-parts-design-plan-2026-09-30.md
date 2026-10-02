# Design Plan — Shared Schema Parts (#662)

Baseline for [issue #662](https://github.com/tya5/chrona/issues/662), on main `400f323d` (2026-09-30).
Design: [design](../../design/issue-662-schema-parts-design-2026-09-30.md). Review: [architecture review](../reviews/issue-662-schema-parts-architecture-review-2026-09-30.md).
Mechanics: [implementation plan](issue-662-schema-parts-implementation-plan-2026-09-30.md).
Rule for schema evolution: [Spec 56 §3.2](../../specification/56-schema-authoring-and-diagnostics.md) (#591, closed).

This pack is documents only: no schema, tool or product code changes. Every number below was measured on main with throwaway scripts
(not committed); slice S0 of the implementation plan turns the corpus measurements into a committed gate.

## Published, inferred, unverified

Published (read on main): the issue body; the 29 live entries and 44 non-live entries of `schemas/schema-inventory-v0.1.yaml`; the schema files;
`src/chrona/resources/__init__.py`; every `Draft202012Validator(` construction site (26 in `src/`, `tools/`, `conformance/`; 17 more in `tests/`);
`tools/schema_inventory.py`, `tools/schema_annotations.py`, `tools/validate_schema_references.py`, `tools/presentation_coverage.py`,
`tools/corpus_coverage.py`, `tools/vocabulary_inventory.py`, `tools/check_view_dispatch_reachability.py`; the #591 archive record; the #573 plan.

Inferred: that no consumer outside the repository depends on a historical schema file (the repository is the only published consumer).

Unverified, and stated where it matters in the design: whether guided-annotation overrides ever produce a valid View (a harness run raised
`RepresenterError` before validation; see review F11); how the CLI surfaces an unguarded `date.fromisoformat` `ValueError` in the presentation
layer; whether revision-store adapters normalise `address` before joining it to a path.

## Literal acceptance (issue rows, verbatim)

1. Parts A1 to A3 exist, and every copy in A references them. Grep finds no inline copy of the sha256, date, safe-path or identifier patterns outside the common schema.
2. Each item in B is resolved: unified, or kept as a declared, documented subset. The `authoring-command` path gains the traversal guard.
3. **Validation-equivalence gate:** every committed YAML (`examples/`, presets, fixtures, tests) validates with the same result before and after, except for inputs that B deliberately tightens. Those are listed, and a test covers each one.
4. Where B changes an accepted value set, the change follows #591 (additive in place, otherwise a declared incompatible bump), and the affected kinds are named.
5. Unused historical schema files are archived, and the schema inventory and its gates still pass.

Reading notes (the review develops these): row 1's grep cannot be literally true while 44 non-live schema files keep their inline copies, so it must be scoped
to live entries (owner decision D8). Row 5's "unused" needs a definition; the design gives one (design D6).

## Claims in the issue checked against main

| Claim | Status | Evidence |
| --- | --- | --- |
| 28 schema kinds latest on main | **stale by one** | 29 live entries, 29 distinct kinds; 28 only if the wheel catalog `builtin-axis-name-tables` is not counted |
| scene 94 / layout-profile 25 / project 20 defs; "`$defs` used well" | verified, but View has 3 `$defs` and Theme 0 | the two largest resource schemas are almost entirely inline, so View has almost nothing to reference (D5) |
| Only two parts are shared, both by URN | verified | `urn:chrona:presentation-resource-v0.1` (used by View x17, icon-catalog x2, summary-profile) and `urn:chrona:revision-store-resource-ref-v0.1` (command-request, automation-result, snapshot-ref) |
| `^sha256:...$` in 18 schemas | verified | 18 live files, 28 pattern nodes; 12 files inline it, 7 hold it in a local `$defs`, 1 (icon-catalog) both |
| ISO-date pattern in 6 schemas; "inline in five, `$defs/date` in two" | 6 verified, **5 is 4** | inline in actual-intake-batch, actual-set, authoring-command, view; `$defs/date` in authoring-workspace, project. Scene v0.7 has `format: date` (a different, never-asserted form) |
| safe relative path regex in 6 schemas | verified | authoring-workspace, presentation-preset, presentation-resource, preset-library, project, theme-v0.14 |
| Envelope `{version, kind, id, body}` in 11 | verified | 11 inline envelopes; 3 more schemas (view, icon-catalog, summary-profile) reference the shared one |
| B1 View anchor `start \| finish \| at \| body` (view-v0.28 line 382); Project `at \| start \| end` | verified | also `finish` is used in 3 example Views, 2 fixtures and one conformance file; `end` is used by Project and by dependency ports |
| B2 authoring-workspace annotation modes `none \| presentation \| all` vs View `none \| semantic \| presentation \| all` | verified, but **a deliberate subset, not drift** | the guided override vocabulary is closed by design; `relations` is likewise `none \| semantic` vs View `none \| semantic \| critical \| all` |
| B2 placement `side` behind View (`auto`, `inside` missing) | **wrong** | View's annotation `placement.side` is exactly `above \| below \| start \| end`, identical to authoring-workspace. `auto`/`inside` belong to a different concept, the label `side` (`visibility.labels.side`, line 143) |
| B3 `tableColumns[].format` vs summary-profile `format` | verified | View has `text, dateRange, date, signedDays` plus an object form `{kind: presence}`; summary-profile has `text, date, count, signedDays` |
| B4 six strict path schemas; layout-profile and revision-store loose | verified, **undercounted** | four variants exist: strict (6), loose (layout-profile, revision-store), a third loose form in render-context v0.16 (`..` only, has `$`), and icon-catalog v0.4's strict-plus-scheme form (accepts the same set as strict) |
| B4 `authoring-command` `path` has `minLength: 1` only | verified, and wider | `target.path`, `payload.directory` and `payload.preset.path` all have `minLength: 1` only |
| The authoring-command path is a security fix | **overstated** | `target.path` only reaches `workspace_path.name` equality; `directory` is re-checked by `_relative` at two layers; `preset.path` is re-validated by the workspace schema and `_child`. See review F8 for what is and is not audited |
| B5 `id` is `minLength: 1` only in six schemas | **wrong** | 18 of 29 live schemas. `^[a-z][a-z0-9-]*$` in example-registry and preset-library, and layout-profile's letter-first form, verified |
| B6 sha256 written three ways | verified, and more | inline pattern (12 files), `$defs/identity` (preset-library, scene), `$defs/sha256` (render-context), plus `$defs` in four more |
| B7 color-scheme license is a free string | verified | and committed data depends on it: 6 schemes say `project-pending`, 10 say `MIT` |
| B8 all date patterns accept `2026-13-45` | verified | also `2026-02-30`, `2026-00-00`, `0000-01-01`, non-leap Feb 29, Unicode digits and a trailing newline; unquoted YAML dates that are impossible fail earlier, at YAML load |
| A: scene shares the circle and rect shapes | **partly wrong** | scene's shapes carry no 0..256 bounds (`positive`/`number`), so they are a bounds-relaxed sibling, not a copy; only icon-catalog and theme-asset-source are exact copies |
| A: revision `{token}` and `{fr}` "in view, layout-profile, revision-store" | partly | `{token}` is in layout-profile and revision-store only; `{fr}` is in layout-profile and view |
| C: 78 files, 1.4 MB | **stale by one** | 77 tracked files (73 schemas, README, inventory, `semiconductor.example.yaml`, `__init__.py`), 1.38 MB |
| C: 17 View, 10 Theme, 7 Scene | verified | |
| C: "View up to v0.26 is referenced by no source or test, only by the schema inventory" | **wrong** | v0.26 is an accepted version in `_SCHEMAS` and 4 tests mention its version; v0.15/19/20/22/23/24 are named by `test_packaged_resources.py`; v0.20 is read by `tools/check_view_dispatch_reachability.py`; v0.14 is pinned by the vocabulary policy. Only v0.12, 13, 16, 17, 18, 21, 25 have no executable reference by file name (docs mention some) |
| README/inventory are the archive authority | **stale README** | `schemas/README.md` lists View v0.14, Layout v0.4, Render Context v0.13 as live; the inventory says v0.28, v0.9, v0.16 |

## Dependencies and state

- #591: closed; Spec 56 §3.2 is in force. The inventory guard only compares new predecessor/successor bumps, so an in-place refactor is unguarded (review F12).
- #573: open. The plan and review merged (PR #659); no code PR is open; slice I573-1 will add `reviewSurface.memberNames` to `layout-profile-v0.9` in place.
  Every #662 slice that edits `layout-profile-v0.9` is scheduled after I573-1 lands (implementation plan S1d).
- #575, #574: no schema overlap. #582-#588 add optional fields to Project/View/Theme in place, so View-touching #662 slices must be small and rebased immediately before merge.
- Open PRs on main: #661 (measurement, draft), #424 (README). Neither touches `schemas/`.

## Use cases the design must serve

1. An author adds a visual profile once and every schema that lists profiles accepts it.
2. A schema author writes `$ref` to a shared definition and cannot forget to register it: a missing registration fails a gate, not one rare input at runtime.
3. A tool that lists a kind's finite vocabulary (coverage, declared-value policy, dispatch reachability) still sees every value after the value moves to a part.
4. A reviewer of any slice can see, mechanically, that accepted values did not change except where declared.
5. The installed wheel validates a document that references a part.
6. A contributor finds one current schema per kind, with historical files archived rather than mixed in.

## Open decisions (each has a recommendation and consequence in the design)

D1 reference, registry and packaging. D2 `isoDate` calendar check. D3 tightenings and their #591 classification. D4 endpoint `finish` versus `end`.
D5 authoring-workspace and View. D6 which historical files to archive. D7 the resource envelope. D8 scope of the "no inline copy" grep.

## Responsibility boundaries

- Schemas own accepted structure. Consumers (View/Layout/Core/operational) own defaults and semantics; a part never carries behaviour.
- `chrona.resources` owns schema loading and the registry; no other module builds a validator.
- Tools that read schemas standalone use the same loader (`bundled_schema` / `dereferenced_schema`), never a private `yaml.safe_load` of a schema that contains `$ref`.
- Conformance owns the equivalence gate, independent of the loader it checks.

## Data and resource model (summary)

Three new schema-only parts, `urn:chrona:common-v0.1`, `urn:chrona:vocabulary-v0.1`, `urn:chrona:graphics-v0.1`, files `schemas/*-v0.1.schema.yaml`, registered in the inventory as
live entries. A part holds only `$defs`; its definitions are frozen once published (design D1). No new resource kind, no authored-document change unless a declared tightening says so.

## Migration effects

Authored documents: none, except the declared tightenings (design D3), each named with its kinds. Runtime: one loader, one validator factory, a `format: date`
checker for `date` only. Wheel: the existing `force-include` ships the parts; archiving moves 38 files out of the wheel (about 0.8 MB uncompressed).
Docs: `schemas/README.md` refreshed; Spec 56 gains three sentences (design D1, D2, review F12).

## Design review questions (answered in the review)

Does a refactor that preserves accepted values need a version bump? Which existing consumers silently stop seeing values? Can a part edit retro-change historical schemas?
Are the B items really the same concept, or deliberately different? Which "unused" files are actually pinned by tools?

## Acceptance evidence needed at release

Per row: row 1, a scoped grep test plus the `$ref` resolvability gate; row 2, the B register in the design with a test per resolved item and the guard tests; row 3, the S0 gate
run before and after every slice, with the deliberate-tightening list and one test each; row 4, the tightening register (design D3) naming kinds and classification;
row 5, the archive evidence table (design D6) and green inventory, annotation, reference and packaging gates.

## Order of slices

S0 equivalence gate; S1 loader, common part, authoring-command guard (layout-profile edits wait for #573); S2 vocabulary; S3 graphics; S4 B resolutions that change behaviour
or need a successor; S5 archive in three tiers; S6 living docs. Detail in the [implementation plan](issue-662-schema-parts-implementation-plan-2026-09-30.md).
