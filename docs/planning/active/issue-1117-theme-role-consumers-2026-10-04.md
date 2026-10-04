# Issue #1117: every declared Theme role and binding needs a consumer (work record)

Living record for [#1117](https://github.com/tya5/chrona/issues/1117), the successor of [#1110](https://github.com/tya5/chrona/issues/1110) (work record [issue-1110-asof-label-ink-2026-10-04.md](issue-1110-asof-label-ink-2026-10-04.md)). Baseline, literal acceptance, design plan, design, architecture review and implementation plan are published together before code. Edited in place; Git keeps history.

**Public base:** `23bc8a57` on `main`. **Status:** design merged (PR #1128); slices 1 and 2 (the check, its twin, the tool and the removal of the dead lines with the two re-pins) in one PR, because the render-time warning on the unedited corpus fails the characterization and warning tests; registering the tool in conformance waits for the reviewer's target-B change. Scope rule (owner): the reviewer's `examples/halcyon-1/*target-b*` files are the reviewer's to edit; their change is listed here and done by them (PR #1061 or a successor), never by this work.

## 1. Published baseline

Read on `23bc8a57` from code and every tracked Theme (`examples/*/themes`, the eight bundled preset Themes, `tests/fixtures`):

1. **The hole.** `theme_role_property_consumer(role, property)` answers from the registered role contracts. An **unregistered** role name falls back to two open producers: any name with a text or axis measurement property (a View-named axis tier or column role) and any name with a Rect paint property (`fill`, `stroke`, ... : a Detail Profile legend entry role). So `anything.fill` in `colorBindings` validates whether or not anything reads it. #1110 closed this for the name `as-of-label` by registering the role.
2. **The audit.** Three names are declared and never read by any consumer; each appears only as a `colorBindings` line:
   - `table-header.fill: surfaceRaised` in 55 Theme files (headers use `text`, or `tableColumnLabel` since #991),
   - `annotation-text.fill: text` in 54 (annotation text uses `annotation-callout-text` and the other registered per-purpose roles),
   - `range.fill: warning` in 19 (no semantic binding, View `textRole`, axis tier or Detail Profile legend entry names `range`).

   55 distinct Theme files, 128 lines: `examples/controller-z` 60, `examples/halcyon-1` 36 (including the reviewer's `21-target-b`), `src/chrona/resources/presets` 22 (the eight bundles), `examples/controller-z-ja` 4, `tests/fixtures` 3, `examples/aster-ssd` 2, `examples/orion-asic` 1. All other unregistered names are read: `table-cell-secondary` (a View `textRole`, #1062).
3. **Pins.** Contexts pin no Theme content (their revision tokens are `example-*`; content identities pin the Project, actual sets, icons and fonts). Two derived Themes (`examples/aster-ssd/themes/onboarding-variation.yaml`, `examples/halcyon-1/themes/12-glyph-gates.yaml`) pin the base Theme they extend by source and content identity, and the preset library pins the bundle files; those re-pin when a base file changes. Scene provenance may record Theme identities, so every Scene is expected to change in its provenance line only.

Unverified (read per slice): which Scenes change beyond provenance (expected none); how many closures a bundled Theme serves.

## 2. Literal acceptance (copied from #1117, plus the owner's 2026-10-04 conditions)

| # | Criterion |
| --- | --- |
| A1 | The three unread declarations (`annotation-text.fill`, `table-header.fill`, `range.fill`) are gone from every bundled and corpus Theme (the reviewer's target-B files are edited by the reviewer). |
| A2 | A synthetic Theme declaring a role no consumer names fails at its pointer; existing Themes still resolve. |
| A3 | Synthetic tests with no `examples/` input; mutation check. |
| O1 | Each accepted-but-unread binding is honoured or removed, never silently ignored. |
| O2 | A corpus-wide check fails for unread bindings. |
| O3 | Theme edits follow the behaviour-change procedure: grouped diff review with images; pinned identities re-pinned as in #575 and #672. |

## 3. Design plan

Use cases: **U1** an author misspells a role (`as-of-lable.fill`) and is told at the pointer; **U2** a bundled Theme drifts and keeps a dead line; the corpus check fails in CI; **U3** a Theme shared by several Views keeps a custom axis or legend role that only some of them name, and keeps working.

## 4. Design (decisions; reverse = delete the check)

- **D1 honour or remove.** `table-header`, `annotation-text` and `range` are **removed**, not honoured: nothing in the design reads a role of that name, and honouring them would add three roles whose paint duplicates `tableColumnLabel` and the per-purpose annotation text roles. Reverse for any Theme: re-add the line; it is then reported (D2).
- **D2 the rule.** A role name a Theme declares in `roles` or `colorBindings` must be one of: a registered role contract; a `group:<id>` colour name; or a name some consumer can read. The consumers that make an unregistered name legitimate are named by the render closure: an axis tier role of the View, a table column `textRole` of the View, or a legend entry `role` of the Detail Profile. The check runs where the closure is complete (Theme, View and Detail Profile known), as a **typed warning** `W_THEME_ROLE_UNREAD` at `/body/roles/<name>` or `/body/colorBindings/<target>` on every render: a Theme is shared by several Views, so a name unread by this one View is legitimate for another and must not fail a render (U3). A name no closure in the repository reads is **dead** and is the corpus check's failure (D3).
- **D3 corpus check.** A conformance tool `tools/check_theme_role_consumers.py` (registered in `conformance/`) loads every manifest slide's closure and every bundled preset closure, computes for each Theme the names that no closure using that Theme reads, and **fails** with `E_THEME_ROLE_UNREAD:<theme>:<name>`. It has a synthetic twin in the PR-path tests (a Theme with one dead role); the sweep over the repository is `-m corpus` only together with that twin (AGENTS.md).
- **D4 no gate weakened.** The check adds a diagnostic and removes dead lines; contrast, perceptibility and role admission are untouched.
- **D5 Theme edits are behaviour-preserving by construction** (the lines are unread), so the expected corpus result is Scenes identical except provenance; any other change is a defect to explain.

## 5. Architecture review

- **Layers.** Theme declares; the closure (which knows View and Detail Profile) checks consumers; Layout, Scene and adapters are untouched. The check reads the existing consumer facts (`capabilities.py` contracts, View axis tiers and columns, Detail Profile legend roles); it adds no new vocabulary.
- **Compatibility.** A user Theme with a dead role begins to report a warning (not an error); nothing stops rendering. The bundled and corpus Themes lose three lines each.
- **Residual risks.** The corpus check must not call a role dead that only a Layout Profile token or a text typography role consumes; the audit above found none, and the check's own tests cover typography roles named by the Layout Profile. The two derived Themes and the preset library need re-pinning.

## 6. Implementation plan

| # | Slice | Files | Tests | Evidence |
| --- | --- | --- | --- | --- |
| 0 | This record (docs PR) | this file | conformance | none |
| 1 | The check and its twin | new `presentation/model/theme_role_consumers.py`, hook in `usecases/render_review.py`, `usecases/diagnostic_messages.py`, new `tools/check_theme_role_consumers.py` (not yet registered in `conformance/`), Specification 07 | synthetic: misspelt role warns at its pointer; a role named by an axis tier, a column `textRole`, a legend entry or `group:` does not; the tool fails on a synthetic dead role; mutation check | none (the corpus still carries the three lines, which the check reports until slice 2) |
| 2 | Remove the dead lines, then register the tool | the 55 Theme files except target B's (the reviewer's), re-pin of the two derived Themes and the preset library, `conformance/` registration | the corpus tool passes; `regenerate_public_examples --write` regenerates every Scene | grouped diff of every changed Scene by identical change (expected: provenance only), images read per group, unread slides listed |
| 3 | Acceptance review | `docs/reviews/current/issue-1117-*` | checker | exact-main three-OS run |

The tool is registered in conformance only in slice 2, and only once the reviewer's target-B Theme has dropped its three lines (their own change); until then the tool run by hand reports exactly that file as the one remaining dead declaration, so the registration is the last step and waits for it.

## 7. Result of slices 1 and 2

- Removed: 127 lines in 55 Theme files (the bundled presets, `examples/controller-z`, `controller-z-ja`, `halcyon-1` except `target-b.yaml`, `aster-ssd`, `orion-asic`, `tests/fixtures`); `table-header.fill`, `annotation-text.fill` and `range.fill` were each read by nothing. Re-pinned: `examples/aster-ssd/themes/onboarding-variation.yaml` and `examples/halcyon-1/themes/12-glyph-gates.yaml` (base source and content identity). Contexts and the preset library needed no change.
- Corpus regenerated (`regenerate_public_examples --write`, 64 slides): every SVG is byte identical; 63 Scenes change in exactly one field, `provenance.resources[].contentIdentity` of the Theme (a grouped diff of one identical change, so no image reading applies: no drawn pixel moves); `21-target-b` changes only by its diagnostics, now four `W_THEME_ROLE_UNREAD` warnings for the unedited target-B Theme (`annotation-text`, `table-header`, `range`, and `as-of-label` until #1110 registers the role).
- Tests: `tests/integration/test_theme_role_consumers.py` (misspelt and unknown roles reported at the pointer, registered roles, `group:` names and roles a column `textRole` names not reported, surfaced as a render warning) and `tests/unit/tools/test_check_theme_role_consumers.py` (the corpus tool on synthetic trees); 9 of 9 mutations killed. Full local suite: green except the schema-equivalence runtime-budget tests under load, which pass alone.
- The tool run by hand on this branch reports only `examples/halcyon-1/themes/target-b.yaml` (the reviewer's file). Registration in `conformance/` follows that Theme dropping its dead lines.

## 8. Registration

Reviewer PR #1061 (`c8ab6d9a`) dropped target B's dead lines; `tools/check_theme_role_consumers.py` prints PASS on the repository and is registered as the conformance check `theme-role-consumers` (after `layout-float-accumulation`), with a registration test in `tests/unit/tools/test_run_conformance.py`.
