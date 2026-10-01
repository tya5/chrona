# Design Plan: Actionable and De-duplicated Diagnostics (#782)

**Status:** Proposed. Design: [issue-782-actionable-diagnostics-design-2026-10-02.md](../../design/issue-782-actionable-diagnostics-design-2026-10-02.md).
Review: [issue-782-actionable-diagnostics-architecture-review-2026-10-02.md](../../reviews/current/issue-782-actionable-diagnostics-architecture-review-2026-10-02.md).
Implementation plan: [issue-782-actionable-diagnostics-implementation-plan-2026-10-02.md](issue-782-actionable-diagnostics-implementation-plan-2026-10-02.md).
**Base:** `main` at `32a5fb4b` (observed 2026-10-02). Product code is not changed by this pack.

## Objective

An agent reads diagnostics to decide its next edit. Today it has to de-duplicate
render warnings by hand and, for some codes, guess what the code means. Make every
row an agent can see carry a message that says what is wrong, and make a repeated
finding one row with a count, in the shared use-case layer, so `chrona` and the MCP
tools (#142) behave the same by construction.

## Literal issue acceptance (copied from #782)

| # | Criterion | Source |
| ---: | --- | --- |
| 1 | A test fails for any diagnostic code that is raised with an empty message | Acceptance |
| 2 | The render warnings that repeat per primitive appear once with a count | Acceptance |
| 3 | The CLI JSON shape stays additive-compatible | Acceptance |
| 4 | A small, general rule: every diagnostic row has a message that names the offending value and, where the set is small, the valid values | Decide |
| 5 | A repeated warning with the same code and cause is collapsed into one row with a count and the first `sourceRef`; the structured fields stay stable | Decide |
| 6 | Check which codes lack a message with a one-off scan of the diagnostic inventory | Decide |

Rows 4 to 6 are the issue's "Decide" section; they are recorded as rows so the
acceptance review answers them. The issue body also names two concrete cases
(about 14 near-duplicate `render` rows; `E_BUILTIN_PRESET_UNKNOWN` without ids).

## Verified starting point

Observed by running the commands on `main` in a scratch workspace and by reading
the sources named here.

- **The 14-row case does not reproduce.** A bad `scheduled` object gives one row
  from `validate` (`E_SCHEMA`) and one from `render` (`E_PROJECT_SCHEMA`); five
  other structural mutations (six in all) also give one row each from both. The union-branch explosion
  the #142 review saw in 2026-10-01 is gone on this base (schema errors are
  explained once by `explain_errors`). What does reproduce is duplication of
  render **warnings**: the Halcyon fixture prints seven `W_LAYOUT_LABEL_SUPPRESSED`
  rows (one per member label) on stderr, and the characterization suite records
  `W_LAYOUT_ACTUAL_INCOMPLETE` twice for one cause.
- **Render warnings have no message.** `usecases/warning_ledger.py` builds each
  record from the identity string (`W_LAYOUT_LABEL_SUPPRESSED:member-label:eps:eps`)
  and the family fields; only scale-collision and attachment records carry a
  `message`. The MCP adapter fills `""` for the rest
  (`app/agent_tools.py::_warning`), which Spec 66 section 2 states as a known gap.
- **Error rows can be a bare code.** The failure ladder maps a bare `ValueError`
  to `code = str(error)`, `message = str(error)`. Twelve rows in the CLI
  characterization golden have a message equal to, or beginning with, their code:
  `E_BUILTIN_PRESET_UNKNOWN` (three cases), `E_BUILTIN_PRESET_OUTPUT_EXISTS`,
  `E_PROJECT_SCHEMA` (a Project that is not a mapping), `E_ACTUAL_REQUIRED`,
  `E_SCHEME_INTENT_UNKNOWN`, `E_LAYOUT_TOKEN_REQUIREMENT_UNAVAILABLE` and three
  importer codes. A multi-line `ValueError` text becomes the **code**
  (`command-check-broken-json`): a defect in the ladder, not only a missing message.
  `LayoutError` and `ColorSchemeError` carry a path or source reference and a
  token that the ladder drops.
- **The inventory is a backlog, not a gate.** `docs/diagnostics/inventory.md`
  (derived) lists 1,291 literal construction sites; 657 CLI-reachable ones (233
  codes) have no detail argument, and `defaultBacklog` classifies every one as
  backlog. The largest are internal invariants (`E_PRESENTATION_PRIMITIVE_INVALID`
  76 sites, `E_FONT_METRICS_UNAVAILABLE` 27, `E_THEME_TOKEN_TYPE` 21).
- **De-duplication exists, in the wrong place.** The MCP adapter drops exact
  duplicate rows and caps at 50 (`_envelope`); the CLI does neither, so the two
  front ends disagree on the same failure.
- **The CLI bytes are frozen by a characterization suite** (110 invocations,
  `tests/cli/test_cli_characterization.py`); a change to a row is an intended golden
  change and has to be explained.

## Use cases

1. An agent runs `chrona render plan.yaml --preset editorial2` and learns which
   preset ids exist from the diagnostic alone.
2. An agent renders a dense plan and receives one row per kind of warning with a
   count and the first occurrence, not forty lines to de-duplicate.
3. An agent calls the MCP `render_draft` or `validate_project` and gets the same
   rows, counts and messages as the CLI.
4. A maintainer adds a new diagnostic code and a test tells them if an agent would
   see it with no message.

## Open decisions (resolved in the design, recorded on the issue)

- D1: what "same cause" means for a warning.
- D2: where messages for warnings live (producers, Scene, or the use-case layer).
- D3: what an agent sees for the long tail of bare internal codes.
- D4: which additive keys, and when `count` appears.
- D5: how `E_BUILTIN_PRESET_UNKNOWN` carries the valid ids.
- D6: what to do with the issue's 14-row claim that no longer reproduces.
- D7: which of the MCP adapter's transforms move to the shared layer.

## Responsibility boundaries

The use-case layer (`usecases/failure_report.py`, `usecases/warning_ledger.py`,
`usecases/draft_render.py`, a new `usecases/diagnostic_messages.py`) owns what a
diagnostic row says and how repeats collapse. Core, Scheduler and Scene producers
keep their identity strings; the Scene JSON `diagnostics` list is unchanged. The CLI
and `app/agent_tools.py` print or wrap what the use cases return. Scrubbing host
paths and the 50-row cap stay in the MCP adapter (they are a transport concern).

## Out of scope

The scheduler and `W_DEADLINE` (another owner), `chrona validate` passing a cycle
(#780), the other open #780/#781/#789/#810 work, #454, and rewriting the 233 codes'
bare producers. The last is a successor issue (owner-local detail per
code), not a prerequisite.

## Acceptance evidence needed

A shared-layer test that a row can never leave with an empty or code-equal
message; a test per warning code that every code a render can emit has a message
template; a collapse test with a mutation check; the characterization golden diff
with an explanation per changed case; the MCP envelope equal to the CLI rows; Spec
66 and the skill's diagnostics table updated; the inventory regenerated by
derived-sync, never by hand.

## Order of design slices

1. This design plan. 2. The design. 3. The architecture review. 4. The
implementation plan. Each is its own docs-only PR; implementation (S1, S2) starts
after the plan is merged.
