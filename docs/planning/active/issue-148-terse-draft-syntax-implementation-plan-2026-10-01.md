# Implementation Plan — Terse draft syntax (#148)

**Status:** Proposed; becomes the working plan once the lead has decided D1-D5 and the
[architecture review](../../reviews/current/issue-148-terse-draft-syntax-architecture-review-2026-10-01.md)
conditions C1-C8 are accepted. Behaviour is defined by the
[design](../../design/issue-148-terse-draft-syntax-design-2026-10-01.md) (and, from slice 1, by Spec 65); this
plan only orders the work. See the [design plan](issue-148-terse-draft-syntax-design-plan-2026-10-01.md) for the
literal acceptance inventory (A1-A12). Every PR and commit says `Refs #148` and never a closing keyword;
the issue closes only after the acceptance review and the three-OS run on the commit that publishes it.

## 0. Why the order differs from "parser, calendars, CLI, docs"

Two repository gates force slice contents (review F1): `tools/check_module_reachability.py` rejects a module no
entry point reaches, and `tools/check_documented_commands.py` requires every command and option to be
documented. So the smallest publishable useful slice already includes the `compile` command and a guide
section. The draft dispatch (render, validate, schedule) is still later and separate.

## 1. Slice overview

| Slice | Delivers | Needs lead decision first |
| --- | --- | --- |
| S0 | This design pack (docs only) | none |
| S1 | `chrona compile`: tasks, gates, groups, dates, spans, durations, dependencies | D3 (extension is only a convention here), D5, D6, D7, D8, D9 |
| checkpoint | Go/no-go (D11) on the agent check and bytes/retries record | the lead reads the record |
| S2 | Calendars, per-object calendar, lag calendar, anchors, bounds, ledger test, HALCYON golden | D1 |
| S3 | `.chrona` accepted by `render`, `validate`, `schedule`; positioned Core/scheduler errors | D4 |
| S4 | Guide, README, doc-check fence support, agent hook for #142 | none |
| S5 (optional) | Overlay `--with` or inline `key=value` fields | D2, only on evidence |

Each slice is one PR, independently reviewable and revertable, merged with `derived-ready` green.

## 2. Slice 1 - `chrona compile` (core grammar, no calendars)

**Scope of the grammar in S1:** `terse 0.1`; `project ID ["Title"]`; objects `NAME ["Title"] KIND` with kind
`task | gate | group`; schedule `DATE`, `DATE..DATE`, `AMOUNT` with `d`/`w` units; nesting under `group`;
`after` with default endpoints, `.start/.end/.at`, comma lists and signed `d`/`w` lag; comments, strings,
indentation; all lexical, structure, name, reference and value diagnostics. A `calendar` statement or a `wd`
amount, `from`/`until`, bounds, `in CAL` and a per-object `calendar` clause are recognised and answered with
`E_TERSE_UNSUPPORTED` ("arrives in the next release of the syntax"); Core's `E_CALENDAR_REQUIRED` would otherwise
be the first thing a `wd` user sees without any way to fix it.

**Files (new):**
- `src/chrona/terse/__init__.py`, `lexer.py`, `parser.py`, `compiler.py`, `emitter.py`, `diagnostics.py`
  (`TerseDiagnostic`, the code catalogue, hint helpers incl. nearest-name by a hand-written edit distance with
  stable tie-breaking).
- `src/chrona/usecases/terse_compile.py`: compile + `core.validate_project` + source-map positioning of Core
  findings; returns one result value (project bytes or diagnostics).
- `docs/specification/65-terse-plan-syntax.md` (grammar, mapping, ids, codes, determinism; Status Proposed),
  plus a line in `docs/specification/README.md`, one cross-reference sentence each in Spec 05 and Spec 51.
  Check open PRs and the directory for the number first. Then the design's section 3 and mapping table become a
  pointer (edit in place).
- `docs/guides/terse-plan.md`: minimal, accurate to S1 (what `compile` does, the grammar card, hand-off rule);
  regenerate `docs/guides/cli-reference.md` with the repository's tool.
- `.gitattributes`: `*.chrona text eol=lf` and the golden YAML under `tests/fixtures/terse/`.
- Tests (below).

**Files (edited):** `src/chrona/app/cli.py` (the `compile` subparser and `_run_compile`: read bytes, decode,
call the use case, atomic write, stream rule), `tools/check_import_direction.py` (row `"terse": {"core"}`, and
`terse` added to the `usecases` set; the commit message states the reason).

**Tests:**
- `tests/unit/chrona/terse/test_lexer.py`, `test_parser.py`, `test_compiler.py`, `test_emitter.py`.
- `tests/unit/chrona/terse/test_golden.py`: pairs in `tests/fixtures/terse/` (minimal starter, issue sketch
  without calendar clauses, groups, forward references, `on`/`no`/`null` names, a title with `#`, a comma and
  Japanese text). Output bytes equal expected; expected validates; placements and critical set of compiled and
  expected equal.
- `test_errors.py`: one negative fixture per `E_TERSE_*` code in the S1 catalogue with expected
  `(code, sourceRange)` and a hint check; completeness test both ways (every catalogue code has a
  fixture, every fixture names a catalogue code); the ten mistakes of design 7.4 verbatim.
- `test_properties.py`: seeded (`random.Random(148)`) mutation fuzz, thousands of cases, asserting design 13.5
  (a)-(e): never raises; diagnostics imply `project is None`; positions in range; accepted implies
  `validate_project` clean; second compile byte-equal.
- `test_determinism.py`: subprocess under different `PYTHONHASHSEED` and `LC_ALL` equals golden bytes.
- `test_slug_part.py`: the compiler's name pattern equals `common-v0.1`'s `slug`.
- `tests/cli/test_cli.py` additions: stdout mode, `-o` mode, `-` stdin, refuse-overwrite, rejection JSON on the
  correct stream with exit code 1, input I/O exit 2, redirect-safety (failure leaves an empty redirected file).
- Import direction: `python tools/check_import_direction.py` passes; a unit test shows `storage` importing
  `terse` would be flagged.

**Proof (recorded in the PR body):** compiling the issue sketch (calendar-free variant) and the minimal starter;
`chrona validate` and `chrona schedule` on the output; the HALCYON-shaped d/w fixture schedules identically to
its hand-written twin; focused pytest, conformance, `check_import_direction`, `check_module_reachability`,
`check_documented_commands`, `check_text_encoding`.

**Must NOT:** touch `render`, `validate` or `schedule`; import anything but `core` from `terse`; read files or
env inside `terse`; compute dates, cycles or float; add a dependency; edit a schema, example, derived document or
`docs/diagnostics/*`; embed the source path or a hash in the output; accept `.chrona` for any other command;
create a staged-module entry.

## 3. Checkpoint (D11)

After S1 merges, before S2: a short written record in this file (replace this paragraph): bytes and line
counts for three plans (minimal, groups-and-dependencies, a HALCYON-sized d/w plan) against their YAML;
the agent check of design 13.11 (one-page card, three prompts, compile attempts needed); and any friction found
in the grammar (for example the implicit default calendar, F12). Rule: continue to S2-S4 if agents reach a
compiling plan in at most one retry on the first two prompts; otherwise stop at `compile` and report to the
lead.

## 4. Slice 2 - calendars and schedule shaping

**Scope:** `calendar CAL days [except ...] [work ...]` (days, ranges, lists), `project ... calendar CAL`, the
single-calendar default (N1), per-object `calendar CAL`, lag `in CAL`, `wd` amounts and lags, `from`/`until`,
bounds, `E_TERSE_DAYS_INVALID`, `E_TERSE_CALENDAR_UNKNOWN`, `E_TERSE_CLAUSE_DUPLICATE`; the Core
`E_CALENDAR_REQUIRED` hint. Remove `E_TERSE_UNSUPPORTED` use for these constructs (the code stays reserved).

**Files:** the same `terse` modules (extended), `terse/ledger.py` (the mapped/yaml-only classification),
`tests/unit/chrona/terse/test_ledger.py` (walks `schemas/project-v0.7.schema.yaml`; fails when an authorable
property is unclassified), Spec 65 and the guide updated in place.

**Tests:** golden pairs for both calendar forms (`except`, `work`, either order), anchors and bounds, a lag in
another calendar, two calendars with an explicit project calendar and without (error plus hint); the
32-line HALCYON core as `tests/fixtures/terse/halcyon-1-core.chrona` with a hand-written twin copy of the
equivalent YAML (PR path), and one test marked `corpus` comparing it with `examples/halcyon-1/project.yaml`
(placements, critical set, edges modulo relation ids); fuzz extended to calendar syntax.

**Proof:** the HALCYON equivalence (29 placements, 24 edges, same critical set: the spike's result, now as a
test); ledger test red when a property is added to a copy of the schema.

**Must NOT:** add `fiscalStartMonth`, `mo`/`y` lags, successor endpoints other than `start`/`at`, date ranges in
`except` (one date is one record); edit `examples/halcyon-1`; change any schema.

## 5. Slice 3 - draft ingress and positioned downstream errors

**Scope:** the adapter dispatches on the `.chrona` suffix in `render`, `validate` and `schedule`:
`validate`/`schedule` in `_load_primary_project`; `render` through a `TemporaryDirectory` holding the compiled
`project.yaml` (the `_resolve_preset_argument` pattern), cleaned in `finally`. The use case returns the source
map; `_reject` and the closure-failure path accept an optional map and add `sourceRange`/`hint`
to Core and scheduler diagnostics (pointers keyed by index and by relation id, with nearest-ancestor fallback);
the hint table for Core codes (`E_CALENDAR_REQUIRED`, `E_INVALID_SPAN`, `E_FIXED_TARGET_VIOLATION`,
`E_UNSUPPORTED_CYCLE`, `E_CONTRADICTORY_BOUNDS`, `E_ROLLUP_EMPTY`, `E_ENDPOINT_MODE_MISMATCH`) lives in the use
case.

**Files:** `src/chrona/app/cli.py`, `src/chrona/usecases/terse_compile.py` (source-map application),
`terse/compiler.py` (source-map entries completed), tests, guide text.

**Tests:** render of `plan.chrona` is byte-identical (SVG) to compile-then-render of the YAML, same flags and
`--actual`; positioned errors for a gate earlier than its predecessor, a cycle, contradictory bounds, an empty
group, an empty span; no output contains the temporary directory prefix; `render-review`, `review`,
`baseline-*`, `materialize` and `--snapshot-reference` reject a `.chrona` path (each named in a test); import
direction unchanged (no new edge).

**Proof:** the same HALCYON core rendered both ways with identical bytes; an agent-style failing plan shows
`line:column` for a scheduler error.

**Must NOT:** change `resolve_draft_render` or anything under `presentation`, `storage`, `operational`; cache
compile results on disk; add a flag to `render`; keep the temp directory after exit.

## 6. Slice 4 - documentation, doc-check and the agent hook

**Scope:** `docs/guides/terse-plan.md` completed (grammar card, mapping examples as executable pairs, error
catalogue excerpts, the hand-off rule, how it differs from the guided workspace, the stream rule); a short
README paragraph and a pointer from `docs/guides/first-project.md`; `tools/check_documented_commands.py`:
fences with info string `chrona` are excluded from command scanning and compiled (in process through the
use case), markers `<!-- chrona:doc-check skip: reason -->` (existing), `expect-error: CODE` and `expect-yaml:
next` (the next ```` ```yaml ```` fence must equal the emitted Project minus the header comment).
Hand-over note for #142: a one-page grammar card in Spec 65 and the frozen contract of design 11; the skill and
MCP are not written here.

**Tests:** `tests/unit/tools/` cases for the new fence handling, including a fixture whose object is named
`chrona`, a wrong example with `expect-error`, a mismatched `expect-yaml` failing; the live doc-check over
README and guides passes.

**Must NOT:** author the agent skill or any MCP tool; add a Markdown reader to the CLI; document a construct the
grammar does not accept.

## 7. Slice 5 (optional, lead-gated) - overlay or inline fields

Only on the lead's explicit decision after real use (D2). Overlay: `chrona compile --with extras.yaml` per
design 5.2, codes `E_TERSE_OVERLAY_*`, YAML source marks for positions, a second source map, and a ledger update.
Cheaper alternative if only `fields` is missed: one clause `key=value` (strings only) mapping to `fields`. Both
come with their own design amendment before code.

## 8. Gates and commands every code slice runs

`python tools/check_import_direction.py`, `python tools/check_module_reachability.py`,
`python tools/check_text_encoding.py`, `python tools/check_documented_commands.py --check` (and `--execute`
when the guide changes), `python conformance/run_conformance.py`, focused pytest for `tests/unit/chrona/terse`
and `tests/cli`, and `python tools/check_issue_acceptance_reviews.py`. No schema is edited, so
`tools.schema_equivalence` is not required; if a slice ever touches `schemas/` it runs it and records the result.
Derived evidence is never edited; PRs touch no `examples/*/generated/*`, `docs/diagnostics/*` or
`docs/gallery/presentation-coverage.md`.

## 9. Acceptance and release

At release a single review in `docs/reviews/current/` carries one row per literal item A1-A12 of the design plan
with direct evidence (commit, PR, test names, a rendered `.chrona` output inspected, the three-OS run on the
publishing commit). A1-A3 need S1-S3 plus S4's fence form; A6 needs S3's negative tests; A9 needs the ledger
(S2); A11 needs S1's property test. If the lead chooses compile-only for D4, A3's "or accepted directly by the
draft render" is met by `compile` alone (the issue says either) and S3 is dropped.

## 10. Risks and what would change the plan

| Risk | Signal | Response |
| --- | --- | --- |
| Agents do not benefit | Checkpoint fails (D11) | Stop after S1; fold the positioned-diagnostics idea into the YAML path |
| Grammar drift from the schema | Ledger test red | Decide per property (mapped or yaml-only); never auto-extend |
| Spec number collision with #142 | Open PR or new spec file | Take the next free number; the number is not part of any contract |
| Doc-check tool change conflicts with #372 work | Open PR touching the tool | Coordinate in S4; rebase |
| Windows temp-file behaviour | CI failure on Windows in S3 | Close the file before the render and clean up in `finally`; same fix as the preset path |
