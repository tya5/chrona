# Issues #977 and #970: merge-time friction (work record)

Living record for [#977](https://github.com/tya5/chrona/issues/977) (hard-coded slide and label counts in tests) and [#970](https://github.com/tya5/chrona/issues/970) (S0 expected-delta entries outlive their PR). Both are one class: a number or an entry that every parallel PR must hand-edit, so each rebase conflicts. One record, edited in place; Git keeps history. Order: #977, then #970.

**Public base:** `5bd31ee8` on `main`. **Status:** design and implementation plan (sections 3 to 5) published (PR #986, `9162d39d`); S2 (#977) merged as PR #992 (`28ed8e10`); S3 (#970) implemented

## 1. Published baseline

Read on `5bd31ee8` (both issues had no comment before the claims).

1. **Where the counts are.** A search of `tests/` and `tools/` for literal slide, scene, label and path totals finds exactly these:
   - [`test_public_geometry_regressions.py`](../../../tests/acceptance/output/test_public_geometry_regressions.py): `len(SCENES) == 42` (twice), `len(SVGS) == 42`, `axis_count == 379` (twice), `hosted == 17`.
   - [`test_derived_evidence.py`](../../../tests/unit/tools/test_derived_evidence.py): `len(derived_paths()) == 93`; its docstring in [`derived_evidence.py`](../../../tools/derived_evidence.py) says "currently 58 + 9 paths" (already wrong).
   - [`test_presentation_coverage.py`](../../../tests/unit/tools/test_presentation_coverage.py): `len(discover(root)) == 42`.
   - [`test_local_authoring.py`](../../../tests/unit/chrona/usecases/test_local_authoring.py): `len(closures) == 20`, with a growing comment of slide names.
   - [`test_label_chips.py`](../../../tests/integration/test_label_chips.py): two hand-listed sets of HALCYON-1 slide names (not totals, but the same conflict: PRs for #585 edited both twice).
   Not slide totals, so left alone: `tools/corpus_coverage` row `| halcyon-1 | 29 | 29 | 24 | 29 |` (Project object magnitudes), `test_view_v01_schema` (`len(entries) == 7`, a fixture), and the schema `enum` golden in `tests/fixtures/cli_characterization/golden.json` (it moves with a Theme enum, the lane of #889).
2. **How often they moved.** PR #966 changed the scene and SVG totals from 41 to 42 and the label total from 366 to 379 and edited both name sets; the controller-z slide PR (a474d425) changed 36 to 37, `hosted` from 13 to 14 and the path and coverage totals. Every PR carrying a slide edits the same lines, and #585 re-based them four times.
3. **What the evidence is.** A PR never authors generated evidence: CI regenerates it in a snapshot from the manifests (`tools/derived_evidence.py`), and the three-OS and shard tests read that snapshot. A manifest slide always has an SVG; the Scene is optional by the code but every slide declares one. For every slide the Scene's `axis-label` primitive count equals the SVG's `data-purpose="axis-label"` element count.
4. **S0 gate (#970).** `conformance/schema-equivalence/expected-deltas-v0.1.yaml` has 476 one-line entries: L1 113 (66 value deltas, 42 `after: removed`, 5 `after: added`), L2 60, L3 303. L1 compares the working tree with `--base-rev` (a manual PR step, AGENTS.md step 3; conformance runs only L2 and L3). An L1 entry is read only while its schema differs from the base: it applies if the base value equals `before`, counts as landed if it equals `after`, and otherwise `compare_l1` fails the run with "does not apply". An entry for a schema that did not change is only an `unused` note. Nothing ever removes an entry. L2 and L3 entries compare the tree with `baseline-results-v0.1.json`, which is not re-recorded per PR, so they stay meaningful and are not part of this issue.
5. **Observed.** The #584 `annotationKinds` and Theme `values` entries sit in the file and report "does not apply" against a base that also contains #585-2 (`writingMode` joined the same enum).

Unverified until built: that every merged L1 entry can be proven landed from Git history (to be proved entry by entry in section 5, S3).

## 2. Literal acceptance (from the issues)

**#977**
1. Derive the expected totals (public-slide, scene, axis-label, geometry counts) from the committed manifest or generated evidence, so adding a slide does not edit a test.
2. Keep a check that every slide is accounted for.
3. Keep a check that no slide changes silently: relations plus a reviewed per-slide allow-list for intentional changes.
4. Design-first and small. (Owner rule, restated by the lead: corpus output is not an oracle; stop hand-edited magic numbers without weakening detection of unintended change.)

**#970**
1. Decide the lifecycle of an expected-delta entry (options a, b, c in the issue).
2. Recommendation to implement: entries carry the PR or merge revision and are removed by the next PR that touches the file, plus a gate mode that fails when an entry is stale for more than one merge.
3. Design-first and small. Added by the lead: prune the currently stale entries, proving each stale against the base it was recorded for; S0 semantics intact, no real delta check weakened.

## 3. Design

### 3.1 #977: totals are derived, the per-slide record is a ledger

- **No literal total in any test.** Totals come from the manifests: scene and SVG sets equal the declared outputs, the derived-path total is counted from the raw manifest YAML plus `REPORTS`, the coverage and local-authoring counts equal the slides or contexts the manifests declare.
- **Relations replace the label totals.** For each slide, Scene `axis-label` count equals SVG `axis-label` element count (the adapter drops none); the slides whose `dvt` member label follows its host bar are the ones the Scene has both for. These hold with no number.
- **A reviewed ledger replaces "no change".** `tests/acceptance/output/public-slide-ledger.yaml` has one line per manifest slide, keyed `<example>/<slide-id>`, sorted: `{axisLabels: N}` plus `dvtHosted: true` and `chips: [...]` only where they apply (absent means false and none). The test fails for a slide with no row (not accounted for, message prints the observed values to paste), a row with no slide, an unknown field, and any difference between the observed value and the row. An intentional change edits that slide's row in the PR that causes it, with the reason in the PR; an unintended change fails. A row is a change detector, not a quality target, and says so in its header. Rows are one line each in sorted order, so two PRs adding different slides merge cleanly.
- **Core rule tested on synthetic input.** The comparison is a pure function in `tests/support/public_evidence.py`; its tests build observed and ledger values by hand (missing, stale, mismatch, unknown field, default) and carry mutation checks. The corpus test only feeds it the real slides.
- **Out of scope.** Scene content, quality bars (contrast, overlap, ellipsis checks stay as they are, minus their counts), and the schema enum golden.

### 3.2 #970: entries are retired by Git, not by hand

- **An entry is merged when the base revision's file contains it.** Identity is (layer, subject, pointer, before, after). Its landing commit is the oldest commit of the unbroken run, in the first-parent history of the file up to the base, that holds the entry; that commit's first parent is the base the entry was recorded for. This is the "PR or merge revision": derived from Git, so no author edits it and none can forget it. An optional `pr: <number>` field is accepted for readers and ignored by the logic.
- **Stale means merged and not applying now.** A merged L1 entry that does not apply to the base (value neither `before` nor still needed) was only ever for its own PR. `compare_l1` then reports it as stale instead of failing "does not apply"; an entry that still applies (its `before` holds) keeps working. An in-flight entry (absent from the base file) is judged exactly as today. The residual check (patched base equals head, or additive) is untouched, so no real delta is excused by a stale entry.
- **Age and the gate mode.** A stale entry's age is the number of first-parent commits that touch `schemas/` after its landing commit, up to the base. In a `--base-rev` run an age of 0 or 1 is a note (the next schema PR may prune it); an age above 1 is a failure that names the entry, its landing commit and `--prune-stale`. Counting schema commits, not all commits, keeps a docs or bot commit from ageing it.
- **Pruning with proof.** `python -m tools.schema_equivalence --base-rev origin/main --prune-stale` removes the stale entries from the file. It removes one only after proving it against its recorded base: at the landing commit's first parent `before` holds at the pointer (or the schema is present for `removed`, absent for `added`), at the landing commit `after` holds, and at the base `before` no longer does. An entry that fails the proof is kept and listed. It rewrites only the removed one-line entries.
- **Not changed.** L2 and L3 entries (they compare with the recorded baseline, not a base revision), the conformance check (L2 and L3), the `unused` note for in-flight entries, and every comparison rule of L1.

### 3.3 Architecture review

Both slices are test and tool code; no layer, schema, Scene or public contract changes. #977 changes no product behavior and reads only manifests and generated files, as the existing corpus tests do. #970 changes the gate's reporting and file hygiene, not what it accepts: a stale entry could only ever fail a run, never excuse a change. The gate stays independent of the production loader (`test_the_gate_reads_no_production_loader`), and Git is used through the existing `_git` helper. Specification 56 (validation equivalence) and AGENTS.md step 3 gain one sentence each for the lifecycle. Conflict surface: #889 edits the Theme and Layout schemas and count tests (it rebases onto these PRs); #585 and #890 are untouched, except that pruning removes L1 lines at the end of the expected-deltas file, where #585 appends, which is a trivial rebase.

## 4. Owner-level judgement calls

Recorded here and as a comment on each issue (options, choice, why, how to reverse).

- **J1 (#977): ledger rows for every slide, or only exceptions.** Chosen: every slide, because the issue asks for both "every slide accounted for" and "no change silently", and a missing row is the accounting check. Reverse: delete the ledger and its test; the relations alone remain.
- **J2 (#977): chips in the ledger.** Chosen: yes, replacing the two name sets in `test_label_chips.py`, because they conflict the same way. Reverse: restore the sets.
- **J3 (#970): carry the revision as a field, or derive it.** Chosen: derive from Git, `pr` optional, because a field is written before the merge commit exists and would need a second edit. Reverse: require `pr` and match it against the commit subject.
- **J4 (#970): where the stale gate runs.** Chosen: the `--base-rev` run only, because conformance has no base and a stale limit there would fail unrelated PRs. Reverse: add `--base-rev origin/main` to the conformance check.
- **J5 (#970): age unit.** Chosen: schema-touching merges, limit 1. Reverse: change `STALE_MERGE_LIMIT` or the path filter.

## 5. Implementation plan

| Slice | Content | Files | Gate |
| --- | --- | --- | --- |
| S1 | This record, both issues | this file | docs PR, conformance |
| S2 (#977) | `tests/support/public_evidence.py` (declared slides, observation, `compare_ledger`), the ledger file, `test_public_slide_ledger.py` (corpus plus synthetic mutation tests), literals removed from the five tests above, stale docstring fixed | the files named in section 1 and the new ones | focused tests, mutation checks, `git diff --stat origin/main` shows only these |
| S3 (#970) | `Delta` merge and age fields, landing-commit lookup, stale classification and age gate in `run_gate`/`compare_l1`, `--prune-stale` with proof, tests on a synthetic Git repository, the prune of the currently stale L1 entries (each proof recorded in the PR), spec 56 and AGENTS.md sentences | `tools/schema_equivalence.py`, `tests/unit/tools/test_schema_equivalence.py`, the deltas file, spec 56, `AGENTS.md` | S0 gate with `--base-rev origin/main` (expect PASS and no stale), focused tests, mutation checks |
| S4 | One literal acceptance review for both issues; exact-main three-OS run on the review commit; close each issue only if every row is met or narrowed with a successor | `docs/reviews/current/` | the exact-main run |

Each slice is one PR with `Refs #n` only. S2 lands first; #889 rebases onto it if it lands first.

## 6. Progress and evidence

### S2 (#977, implemented)

No test states a slide, scene, label or path total any more. [`tests/support/public_evidence.py`](../../../tests/support/public_evidence.py) reads the declared slides from the manifests and holds the pure comparison; [`public-slide-ledger.yaml`](../../../tests/acceptance/output/public-slide-ledger.yaml) has one sorted line per slide (`axisLabels`, `dvtHosted`, `chips`); [`test_public_slide_ledger.py`](../../../tests/acceptance/output/test_public_slide_ledger.py) checks the real corpus and the rule on hand-built input. The geometry test asserts that the generated files equal the declared outputs; the derived-path total is counted from the raw manifests plus `REPORTS`; the coverage and local-authoring tests compare with the declared slides and contexts; the two name sets in `test_label_chips.py` became the ledger's `chips`. The ledger was first generated at `5bd31ee8` and its chip rows were checked against the old hand-written sets (identical). Two slides landed while the PR was in flight (`controller-z/as-of-cone` from #979 and `controller-z/region-frames` from #984, which also edited the old totals 42 to 44): rebasing conflicted on exactly the old literals, and the ledger test named both missing rows with the line to paste, so each cost one added line.

Mutation checks (all killed): a changed, removed, extra, unsorted, chip-less and host-less ledger row; the rule ignoring a missing row, a stale row, `dvtHosted`, `chips`, `axisLabels`, an unknown field or a missing `axisLabels`; a chip-order-sensitive comparison; the observation reading the wrong Scene or SVG purpose, never finding a host, or the wrong chip prefix; the relation always passing; a Scene with one axis label deleted; an undeclared generated SVG; `discover` skipping a slide; `derived_paths` dropping a report or the Scenes.

### S3 (#970, implemented)

[`tools/schema_equivalence.py`](../../../tools/schema_equivalence.py): `Delta` gains `pr`, `merged`, `landing`, `age`, `applied`; `entry_landings` reads the first-parent history of the file up to the base and gives each entry its landing commit and age; `mark_merged` flags the L1 entries the base file holds; `compare_l1` reports a merged entry that no longer applies as stale, not "does not apply" (the residual check is untouched); `stale_findings` fails an age above `STALE_MERGE_LIMIT` (1) and notes an age within it; `prune_stale` / `--prune-stale` removes stale entries after the proof of section 3.2 and reports each. Tests: [`test_schema_expected_delta_lifecycle.py`](../../../tests/unit/tools/test_schema_expected_delta_lifecycle.py) on a synthetic repository (landing, refresh, re-add, side-branch merge, L3 never merged, age gate, base-rev runs, each proof branch, markers, byte-for-byte file rewrite, optional `pr`).

The prune, against `origin/main` at `9162d39d`: all 104 L1 entries then in the file (the 9 that #984 had already hand-removed are not counted) were proven stale and removed, 0 kept: 101 by "before held at the landing commit's first parent, after holds at the landing commit, before no longer holds at the base" and 3 repair entries (View `periods`, Theme `annotationKinds` in `theme-v0.11` and `theme-v0.13`, whose `before` was never true at their landing parent because the result had landed earlier) by "after already held at the base they were recorded for". 363 L2 and L3 lines remain. `python -m tools.schema_equivalence --base-rev origin/main` passes with no stale entry.

Mutation checks: 30 mutants of the limit and its comparison, the age filter (`schemas/`, first-parent), the landing and run-break rules, stale selection (applied, layer), merged marking by layer, the does-not-apply excuse (always, never), the applied flag, every proof branch and the marker predicates, the file rewrite (keeps every line, drops every L1 line), the entry key (without `before`, without pointer), `pr` validation, the unused note, the marking step and the `--base-rev` requirement. Four survived the first pass and are killed by tests added for them (side-branch merge, oldest-commit landing, L3 in the base file, a removal marker present at its landing commit); one is equivalent (the rewrite also parses non-entry lines and keeps them).
