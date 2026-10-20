# Issue 1810 — slip reading acceptance

Status: implementation verification in progress; release acceptance pending.
Design authority: Spec06 §7.4/§8.5, Specs28/50/60/63, and the
[living issue plan](https://github.com/tya5/chrona/issues/1810#issuecomment-6286459093).
Design publication: `62416caed6986875f6b9b61bd09a1bdbe4da360c` and
`9dcca78efae5dd902ef668741985ad6bc7abf9d2` (declared marker date visibility).
Implementation: `1f5d053261dc0b93c920b23afde3800d1c2ad07c`.
Warning-message integration: `b5eb2a40354ba0848933b42a68a811454cd6f89a`.

| Literal acceptance criterion | Status | Evidence |
| --- | --- | --- |
| update-a-plan has a "show slip against the original plan" step using `--forecast`, with an explanation of `*`. The Δ header names its reference (a wording key, e.g. "Δ vs baseline"), and `*` has a legend key when estimated deltas are drawn. | not met — release pending | Executable guide tests; reference/override tests; final-visible estimate witness and encoded/plain/completed/table/plot/folded controls. |
| An unresolved `{asOf}` (or any heading placeholder) emits a pointed warning. Subtitle and marker use one date format from the locale. | not met — release pending | Typed missing-fact warning transport and shared locale formatter tests; explicit label-only markers remain label-only. |
| The guide sentence is corrected, and the docs test covers it. | not met — release pending | `tests/integration/test_update_a_plan_guide.py` executes the documented commands and checks stdout warnings separately from stderr. |
| The trial-10 week-2 render shows the slip with a labelled Δ and a keyed `*`. | not met — release pending | [Inspected actual PNG](assets-1810/trial10-week2-forecast.png); unmodified [public trial inputs](https://github.com/tya5/chrona/tree/b17c50028fdd3e7a4e2368b5bdc8033654638da5/trial-10). |

## Actual output and architecture review

The same public week-2 Project/Actual/Snapshot/preset/View is rendered before
(`c35a0cc4665b94a3d66e7ffd6f2a82555be2b6f2`) and after this implementation.
After: `Δ vs baseline`, 12 unchanged starred deltas, one added text-only
`forecast (* estimated)` key, and `27 Oct` in the subtitle/marker date format
(the marker's Theme still lowercases its wording). No invented forecast swatch.
Primitives: 179 → 180; one added, none removed, 18 common primitives changed
(14 legend geometry, plus subtitle/header/two table-cell fits). All 45 non-legend
paths and all 10 complete Scene diagnostic strings are identical.
Existing palette/separability and marker-contrast warnings remain; they are
not claimed as resolved by this issue. PNG SHA-256:
`44683cb9cd393884062d154f8aa4e4a38791302235e7e8bcc7637aabf932fa45`.
The same render from a fresh non-editable wheel install produces byte-identical
PNG and Scene. Wheel SHA-256:
`06c9eb5e840cd8f86b1aff06dd9829097a5147e9d57e7be43f23da3005f62e8b`.
All four documented guide commands run successfully with its four declared
files in the existing docs checker's empty wheel workspace.

Focused verification: 138 heading/wording/content tests; 38 estimate/legend/
guide regression tests; 56 schema-equivalence/docs/closure-guard tests; final
25 changed-path tests all pass. Layout float accumulation and documented-command
checks pass. Full schema equivalence passes (five changed schema expansions,
39 equal; the same five existing invalid L2/L3 documents), as does schema
inventory; only the two intended wording keys are added and stale L1 records
are pruned. No local full pytest/public-materializer sweep.
The all-warning-code catalogue guard caught the missing human explanation
before PR CI; the corrected warning/heading suite passes 22 tests. The final
wheel's no-Actual trial render returns `ok` with a pointed subtitle/asOf warning
and the instruction to supply the fact or remove the placeholder.

Presentation owns the reference/wording/missing facts. Layout carries the typed
estimated-delta witness and selects/measures the explanation from final visible
placements. Scene/adapters and comparison arithmetic are unchanged. Official
public snapshot counts and exact review-containing main three-OS CI remain
required before acceptance; local focused tests alone do not close this issue.
