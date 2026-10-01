# Design Plan — Terse draft syntax that compiles to Project YAML (#148)

**Status:** In design. This is step 2 of the AGENTS.md sequence; the
[design](../../design/issue-148-terse-draft-syntax-design-2026-10-01.md), the
[architecture review](../../reviews/current/issue-148-terse-draft-syntax-architecture-review-2026-10-01.md)
and the [implementation plan](issue-148-terse-draft-syntax-implementation-plan-2026-10-01.md)
are published in the same docs-only PR. No product code, schema or example changes here.

## 1. Baseline (what is published, what is inferred, what is unverified)

Published and verified against `main` at `02a1c9b1` (2026-10-01):

- The unblock condition is met. #120 is closed and `chrona render project.yaml [--preset|--view --theme
  --scheme --layout] [--actual ...] -o out.svg` is the draft render path
  (`src/chrona/app/cli.py` `_run_draft_render`, `resolve_draft_render` in
  `src/chrona/presentation/model/closure.py`). #377 gave it a packaged default preset and #376 gave
  `chrona init` a three-file minimal starter, so the draft path needs no presentation files at all.
- The Project contract is `schemas/project-v0.7.schema.yaml` (`timeline/v0.7`). Schedule modes are
  `fixed-point`, `fixed-span`, `scheduled` (and `rollup`), not the shorthand names in the issue sketch.
  Scheduled amounts are `^[1-9]\d*(d|w|wd)$`; lags are signed (`d`, `w`, `wd` are what Core schedules);
  a span `end` is exclusive.
- Diagnostics today are `core.diagnostics.Diagnostic(id, message, path)` with a JSON-pointer `path`; the
  CLI renders them as `{code, severity, component, sourceRef, revisionRefs, message}` on stdout with exit
  code 1 (`_reject`, `_diagnostic`). Nothing in the repository carries a source line or column.
- Layering is enforced by `tools/check_import_direction.py` (an explicit allow-table) and module
  reachability by `tools/check_module_reachability.py`; documented commands are checked in both
  directions by `tools/check_documented_commands.py` (README and `docs/guides/*.md` only).
- There is already one compact source in the repository: the guided `authoring-workspace` facade
  (Spec 51, `src/chrona/presentation/model/authoring.py`). It is YAML, covers fixed-date tasks only, and
  owns presentation binding. It is not this issue, but the two must not be confused (design section 11).

Inferred (cited in the design where used): that agent-generation density and Markdown embedding are the
benefits that still justify the issue (issue comment 2); that a hand-written parser is enough.

Unverified until implementation: how an agent actually fares with the grammar (the design sets a
go/no-go check after slice 1); Windows behaviour of the draft temp-file hand-off (same pattern as the
existing `--preset <builtin id>` temp directory, so low risk).

I also ran a throwaway spike outside the repository (not committed): a 150-line compiler of the grammar in
the design compiled a 32-line terse rendering of the whole of HALCYON-1's schedule core, validated it, and
produced the same 29 placements, the same critical set and the same 24 dependency edges as
`examples/halcyon-1/project.yaml`. It is evidence that the mapping is sound, not product code.

## 2. Literal acceptance inventory

#148 has no acceptance table; these are its literal requirements (body plus the three comments), each
with the place the design answers it. The release review will carry one row per line.

| # | Literal requirement (source) | Answered in |
| --- | --- | --- |
| A1 | A one-file syntax, Markdown-fenceable, that emits a `timeline/v0.x` Project (issue body) | design 3, 9.4 |
| A2 | Every construct maps to exactly one Project construct (body) | design 4 (table), 5 |
| A3 | Anything the syntax cannot say is written in YAML and the two compose: `chrona compile plan.chrona > project.yaml`, or accepted directly by the draft render (body) | design 5, 9 |
| A4 | The compiler is one-way; no YAML-to-terse (body) | design 6.4, 12 |
| A5 | Markwhen is the scope reference: small grammar, good errors, no scheduling of its own (body) | design 3, 7, 12 |
| A6 | Not accepted anywhere an immutable closure is pinned; a Context references YAML always (non-goal) | design 9.3, 12 |
| A7 | Not a place for presentation (non-goal) | design 12 |
| A8 | Unblock: #120 landed (body) | met; section 1 |
| A9 | State the grammar's scope honestly against the Project properties; a rule for what belongs (comment 1) | design 2.3, 5 |
| A10 | Re-argue on agent generation and Markdown embedding, not beginner cost (comment 2) | design 2.1, 2.2 |
| A11 | Source positions land with the syntax (comment 3) | design 7 |
| A12 | Take `.start`/`.end` endpoint modifiers; do not take document-order reference resolution (comment 3) | design 3.4, 3.6 |

## 3. Dependencies and adjacent work

- Hard: none open. #120, #376 and #377 are closed and shipped.
- #142 (agent skill and MCP) is designed in parallel by another author. It consumes this syntax; this
  design only fixes the contract it can rely on (design section 11) and designs no skill or server.
- #454 is the reviewer-owned board; read only.
- Adjacent contracts that constrain the design: Spec 05 (Project format), Spec 51 (compact authoring
  workspace), Spec 56 (schema evolution, additive in place), #371 (diagnostics must not be bare codes),
  #372 (executable guides), ADR-0023-style "no second authority" (cited in issue comment 1).

## 4. Use cases

1. A person writes `plan.chrona` in an editor, runs `chrona render plan.chrona -o plan.svg`, sees a chart.
2. An agent emits a terse plan in one pass, gets all errors with line and column in one round trip, fixes,
   renders. This is the dominant case and drives the diagnostics design.
3. A plan outgrows the syntax: `chrona compile plan.chrona -o project.yaml`, then the YAML is the
   authority and is edited by hand (scenarios, fields, annotations).
4. A guide or README embeds a plan in a ```` ```chrona ```` fence and the doc-check compiles it.
5. Never: a Context, snapshot, baseline or Store carrying terse text.

## 5. Open decisions this work must close (design answers each, with a recommendation)

| ID | Decision | Design section |
| --- | --- | --- |
| D1 | Grammar scope: schedule-and-structure only, or also scalar object attributes | 2.3, 5 |
| D2 | Composition with YAML: hand-off, add-only overlay, or inline `key=value` fields | 5 |
| D3 | File extension and Markdown-fence info string | 9.5 |
| D4 | Draft-render dispatch: suffix dispatch in the adapter, or compile-only | 9.2 |
| D5 | Dependency: hand-written parser and emitter, or a parser library | 9.1 |
| D6 | Id policy: explicit names only, or title-derived ids | 6 |
| D7 | Kinds: closed set (`task`, `gate`, `group`) or any type word | 3.5 |
| D8 | Diagnostic stream and additive JSON fields (`sourceRange`, `hint`, `source`) | 7.2, 9.6 |
| D9 | Overwrite behaviour of `-o` | 9.6 |
| D10 | Normative home: new Spec 65, and a cross-reference to Spec 51 | 10 |
| D11 | Go/no-go checkpoint after slice 1 | 13.11, 14 and implementation plan |

## 6. Responsibility boundaries and data model (summary; detail in the design)

- Source text is an ingress syntax. It is read only by one package, `chrona.terse`, which imports only
  `core` (for the Diagnostic base) and emits an ordinary Project mapping plus a position map and bytes.
- A new use case `chrona.usecases.terse_compile` composes compile with `core.validate_project` and maps
  every diagnostic back to a source position. The CLI adapter owns file and stream handling and the draft
  dispatch. Presentation, scheduling, storage and operational layers never see terse text.
- No schema changes. No new resource kind. The output is `timeline/v0.7`, validated by the existing
  schema and Core rules.

## 7. Migration effects

None for existing users: no existing command changes behaviour on an existing input. New: one subcommand
(`compile`) and, in slice 3, three commands (`render`, `validate`, `schedule`) additionally accept a path
ending in `.chrona`. Implementation adds one allow-table edge (`usecases` may import `terse`), a Spec 65,
a guide, regenerated `docs/guides/cli-reference.md`, and `*.chrona text eol=lf` in `.gitattributes`.

## 8. Design review questions (answered in the architecture review)

1. Does any layer other than the adapter read terse text, and does the import table prove it?
2. Does the compiler duplicate a Core rule, and where does Core remain the only owner of semantics?
3. Can the grammar drift from the Project schema silently?
4. Is a second compact source (Spec 51) now in the repository, and are their owners distinct?
5. Is every error positioned, coded, actionable and never partial?
6. Is the output byte-stable on all three CI operating systems?
7. What does the user lose when they leave the syntax (hand-off), and is that honest?
8. Does the measured benefit justify the maintained surface?

## 9. Acceptance evidence the design phase needs

- The design resolves D1-D11 with a recommendation and a consequence each.
- The architecture review lists findings with dispositions and a verdict, and names what changed in the
  design because of them.
- The implementation plan has independently publishable slices, each with files, tests, proof and a
  "must not" list, and lists the gates (import direction, reachability, doc-check surface) that dictate
  slice contents.

## 10. Order of design slices

1. This PR: design plan, design, architecture review, implementation plan (docs only).
2. Lead decisions on D1-D5 (extension, dispatch, dependency, scope are the ones that need the lead).
3. Slice 1 onward per the implementation plan; each slice re-reads the issue body for new rows first.
