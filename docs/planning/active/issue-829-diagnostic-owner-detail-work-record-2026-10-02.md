# Work Record: Owner-local diagnostic detail and automation-result messages (#829)

**Status:** Design and implementation plan, one record (local defect class, one owner per slice, no
Core/Scene/Layout contract change). Successor of #782; baseline in the
[#782 acceptance review](../../reviews/current/issue-782-actionable-diagnostics-acceptance-review-2026-10-02.md)
and [`usecases/diagnostic_messages.py`](../../../src/chrona/usecases/diagnostic_messages.py).
**Base:** `main` at `e4429030` (observed 2026-10-02).

## Baseline (measured)

`python -m tools.diagnostic_inventory` on the base: **656 CLI-reachable construction sites with no detail argument,
232 codes**. Every row an agent sees is already non-empty (#782); what is missing is the offending value. Sites by
package (codes in parentheses):

| Package | Sites | Who meets it |
| --- | ---: | --- |
| `presentation/layout` | 153 (48) | internal invariants of Layout (lane, mark, route, annotation inputs) |
| `presentation/model` | 137 (58) | `projection`, `closure`, `theme_inheritance`, `font_*`, `placement_candidates`, `authoring`: the render/validate input path |
| `presentation/renderers` | 66 (12) | `v05_svg`, `v05_typeset`, `registry`: adapter invariants |
| `presentation/icons` | 61 (22) | icon normalizer and importer (tooling commands) |
| `usecases` | 59 (31) | `materialize` 30, `preset_library` 14, `skill_library`, authoring |
| `presentation/scene` | 55 (9) | `E_PRESENTATION_PRIMITIVE_INVALID` (76 sites across Scene and Layout) |
| `presentation/review` | 37 (26) | review content and lane membership |
| `operational` | 24 (12) | references, store config, command engine: automation commands |
| `presentation/contracts` | 20 (13) | packaged-resource loaders |
| `presentation` (top) | 15 (7) | `color_scheme` |
| `resources` | 11 (8) | resource loading |
| `storage` | 10 (4) | snapshots, revision store |
| `presentation/fonts`, `schema_diagnostics`, `commands` | 8 (5) | |

Not yet verified: how often each code is reached by an ordinary author mistake (the inventory counts sites, not
hits). The slice order below uses the paths a Project author or agent drives (`validate`, `schedule`, `render`,
preset, resource, store) as a proxy; internal invariants (Layout, Scene, renderers) are last.

## Literal acceptance (copied from #829)

| # | Criterion |
| ---: | --- |
| 1 | The backlog table in the derived inventory is empty, or every remaining code is classified `sufficient` with a reason. |
| 2 | A test fails for a user-facing code whose raise site carries no detail and that has no classification (a ratchet; today `defaultBacklog` accepts every new bare site). |
| 3 | Automation-result rows carry a message, or the disposition is recorded. |
| 4 | (Owner comment, 2026-10-01) Unify the diagnostic transport: `chrona render` emits bare JSON lines on stderr, other commands use the stdout envelope. |
| 5 | (Body, "What is left" 3) Warning subjects: a producer-side `sourceRef` for `W_LAYOUT_*` identity-string warnings. |

Rows 1 to 3 are the acceptance checkboxes; 4 and 5 are requirements the issue states outside its checkboxes and
are given rows so the review answers them.

## Decisions (owner-level; each is also recorded on the issue)

- **D1, the ratchet.** Options: (a) forbid bare sites outright (656 exist, impossible now); (b) a per-code **site
  count baseline** in `conformance/resolvability-quality-policy-v0.1.yaml`; (c) per-site anchors (brittle:
  every line shift moves them). Choice **(b)**: every bare reachable code needs an explicit entry (`backlog` with its
  `sites` count, or `sufficient` with a reason); `defaultBacklog` is removed, so a new code or an extra site fails
  `validate`; a count that fell below its entry also fails, so each slice must tighten the baseline in the same PR
  (it can only go down). A pytest runs it on the real tree, so PR shards enforce it. Reverse: restore
  `defaultBacklog` and drop the count check.
- **D2, automation-result message.** Options: (a) a new result version with a required `message`; (b) the existing
  open diagnostic row (`additionalProperties: true`) gains a documented optional `message`, filled by the owner and,
  as a floor, by the single builder `stamp_automation_result` through `error_message`; (c) leave code-only and record
  the disposition. Choice **(b)**: additive, no version bump (Spec 56 section 3.2), same guarantee as #782, one place.
  The schema declares `message`; `schema_equivalence` is run. Reverse: remove the property; the builder stops adding it.
- **D3, what counts as `sufficient`.** Only a code whose identifier is the whole message and where no value exists
  to name (a pure state such as "closure required"). Default is to add detail; `sufficient` needs a reason sentence.
- **D4, transport (row 4).** `render` writes the SVG to a file and diagnostics to stderr as JSON lines, with the
  exit code carrying the outcome; other commands print one JSON envelope. Unifying changes the CLI contract of the
  most used command and every consumer reading stderr. Decision: **not in this issue's slices**; a distinct
  successor issue (opened after a duplicate search) owns the choice between a `--json` mode and the envelope.
- **D5, `sourceRef` for identity-string warnings (row 5).** Needs a producer-side Project pointer through Layout and
  Scene identities, a Scene/Layout contract change, not a message change. Successor issue, same duplicate search.

## Slices (each one PR, `Refs #829`, mergeable alone)

| Slice | Content | Files (owner) | Tests and evidence |
| --- | --- | --- | --- |
| S1 | The ratchet (D1): baseline of 232 codes with counts, loader and `validate` change, real-tree test | `tools/diagnostic_inventory.py`, the policy yaml, `tests/unit/tools/test_diagnostic_inventory.py` | the old "does not hide a new bare site" test inverts; mutation-check: remove the count check, add a bare site; inventory regenerated by derived-sync |
| S2 | Store, preset, resource, storage paths: `preset_library`, `resources/__init__`, `store_config`, `storage/*`, `skill_library`, `local_authoring` (about 52 sites) | those modules | per-code message test; CLI golden rows reviewed |
| S3 | Automation-result rows (D2): schema `message`, `stamp_automation_result` floor, owner detail in `command_engine`, `references`, `baselines`, the `cli.py` literal | `operational/*`, `app/cli.py` (literal only), `schemas/automation-result-v0.2.schema.yaml`, Spec 35 | result tests; `schema_equivalence`; golden |
| S4 | Render/validate input path: `projection`, `closure`, `contracts/resources`, `theme_inheritance`, `authoring` | `presentation/model`, `presentation/contracts` | per-code tests; golden |
| S5 | `usecases/materialize` and authoring materialization | `usecases/*` | per-code tests |
| Rest | Layout, Scene, renderers, icons, review, fonts: recorded as the measured gap with a count per package; one successor issue per distinct area after a duplicate search | | the baseline file is the record |

Each slice names the offending value and, where the set is small, the valid values, at the raise site (a
`ValueError("E_X: <detail>")` or the owner's own exception), never in `diagnostic_messages.CURATED_MESSAGES`
(the stopgap). A slice lowers or deletes its codes' baseline entries in the same PR, and a new test per code
asserts the raised text contains the value (mutation-checked by removing the detail). The CLI characterization
golden is re-recorded only for rows the slice intends to change, each explained in the PR.

Publication boundary: the S1 baseline is generated from the tree at S1's base; later slices rebase onto it.
Files owned by concurrent work (#813 `agent_tools.py`, `mcp_server.py`; #586 derived header figures; #880
presets/axis) are not touched.

## Architecture review

No new import edge: `operational` may already import `usecases` (`tools/check_import_direction.py`). The ratchet is
a tool plus data; product behavior changes only in message text (error rows keep their six fixed keys) and the
optional automation-result `message`. Layers stay as declared: Layout and Scene keep raising their own invariants;
only their text gains the value.

## Progress

Nothing implemented yet.
