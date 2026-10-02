# Design Plan: Agent Interface, a Skill and an MCP Surface (#142)

**Status:** Proposed. Design: [issue-142-agent-interface-design-2026-10-01.md](../../design/issue-142-agent-interface-design-2026-10-01.md).
Review: [issue-142-agent-interface-architecture-review-2026-10-01.md](../reviews/issue-142-agent-interface-architecture-review-2026-10-01.md).
Implementation plan: [issue-142-agent-interface-implementation-plan-2026-10-01.md](issue-142-agent-interface-implementation-plan-2026-10-01.md).
**Base:** `main` at `1185e229` (observed 2026-10-01). Product code is not changed by this pack.

## Objective

Make chrona drivable by a coding or chat agent without that agent hand-writing a
slide, in the order the issue proposes (a skill, then an MCP surface), and keep one
engine behind every front end. The owner's positioning (README, PR #424, board #454
P2) is: a designer or an agent designs once, and chrona renders every revision.
Chrona's edge over a hand-drawn or agent-drawn slide is data fidelity, determinism,
diagnostics and reuse; that edge multiplies when an agent can call chrona directly.

## Verified starting point

Published on `main` and checked by running the commands in a scratch workspace:

- **The draft path exists.** #120 (draft render), #122 (PNG/PDF), #371 (diagnostic
  actionability), #372 (executable guides), #377 (default preset in the draft path)
  and #429 (`--preset <builtin id>`) are all closed. `chrona init DIR` writes a
  two-file starter, and `chrona render project.yaml -o plan.svg` renders it with the
  bundled `chrona-default-draft` preset. Two runs are byte-identical; the SVG holds
  no host path. A 3-object plan renders in about 1.6 s including interpreter
  start-up; the 24-object ASTER plan in about 4.8 s (SVG 65 KB, PNG 185 KB).
- **Diagnostics are JSON on stdout with an exit code.** Exit 1 is `rejected` (the
  document was understood and refused), exit 2 is `failed` (input, syntax, tool).
  Render warnings and infos are JSON lines on stderr. `validate` prints a bare `[]`
  on success, not an object.
- **The issue's "thin adapter over `usecases/`" premise is only partly true.**
  `usecases/` holds `render_review`, `preset_library`, `local_authoring`,
  `authoring_commands`, `materialize`, `review_projects`. There is no `validate` or
  `schedule` use case (the CLI calls `core.validation` and `scheduling` directly);
  the draft-render orchestration (`_run_draft_render`, builtin-preset temp copy,
  typesetter checks) and the whole failure-to-diagnostic ladder (`main()`'s
  `except` chain) live in `src/chrona/app/cli.py`; `command-check`/`command-apply`
  and `baseline-compare` live in `operational/`, which imports `usecases/`, so a
  `usecases` facade over them would create an import cycle.
- **The approval model is smaller than the issue states.** `ai-command-proposal/v0.1`
  and `authorization-decision/v0.1` are specified (Spec 10 §9.1) and have a
  conformance fixture, but no runtime code reads or issues them. What runs today is
  a revision-bound compare-and-set (`baseRevision`, `workspace revision`,
  `authoring-command-apply`) and an idempotent replay ledger for operational
  commands. There is no principal, policy or fingerprint check at runtime.
- **The doc-check mechanism does not cover a skill.** `tools/check_documented_commands.py`
  scans only `README.md` and `docs/guides/*.md`, validates every fenced `chrona`
  line against argparse, and (with `--execute`, run by conformance) runs unskipped
  commands in a temp directory seeded with `examples/` only.
- **Packaging.** The wheel is `packages = ["src/chrona"]` plus `force-include` of
  `schemas` and `examples/halcyon-1` under `chrona/resources/`; the console script is
  `chrona = chrona.app.cli:main`; extras are `dev` and `render`; the compressed
  wheel budget is 5 MB. `check_module_reachability.py` requires every module to be
  reachable from `chrona.app.cli` or `chrona.__main__`.
- **Python MCP SDK.** PyPI `mcp`: 2.2.0 (2026-09-07, Python 3.10+) and a maintained
  1.30.0 line released the same day. 2.x renamed the server class to
  `mcp.server.MCPServer`. Both pull in pydantic, starlette, uvicorn, httpx,
  sse-starlette, PyJWT with crypto and, on Windows, pywin32. Chrona's runtime
  dependencies today are PyYAML, jsonschema and fonttools.

### Survey re-check (2026-10-01)

The 2026-09-22 survey and its correction comment still hold: no Gantt or timeline
MCP server with real scheduling has traction. Searches (`mcp gantt`, `gantt mcp
server`, `mcp project schedule critical path`, `gantt skill claude`, topic `gantt`
with `mcp`) return only 0-3 star repositories created recently:
`ragomes102030-cpu/mcp-cronograma-server` (PERT/CPM, critical path, S-curve; 0
stars; pushed 2026-10-01) with a companion `mcp-gantt-lob-server` (0 stars),
`trondegil/xlsx-gantt` (xlsx output with an MCP server, 0), `kbichave/timeline-generator-mcp`
(3, draws a timeline from a config, no scheduling) and `augmdc/projectlibre-mcp`
(read-only over ProjectLibre files, 0). The Mermaid MCP servers remain the working
path (`hustcc/mcp-mermaid` 639 stars). `antvis/mcp-server-chart` has 4 388 stars; the
"no Gantt tool" claim was not re-verified here. New since the survey: a scheduling
(PERT/CPM) MCP now exists but with no adoption and no presentation layer. The
conclusion for the design is unchanged: the room is for a *deterministic scheduler
plus renderer behind one agent surface*, and the closest popular comparator for the
skill is hand-placed SVG (`diagram-design`, 42k stars), not Mermaid.

## Literal acceptance (issue #142 body, copied)

| # | Literal item | Where addressed |
| --- | --- | --- |
| 1 | A `chrona` Agent Skill: `SKILL.md` teaching the authoring model (Project is semantic truth, View selects, Theme paints, the CLI renders), with the eight-file layout, a worked example and the diagnostic codes an agent will meet; tells the agent not to hand-write SVG and not to reach for Mermaid when scheduling matters; depends on #120 | Design D1; slices S1, S2 |
| 2 | An MCP server over the use cases, one tool per use case: `validate_project`, `schedule_project`, `render_review` (SVG, PNG once #122 lands), `compare_baseline`, `apply_command` (`command-check`/`command-apply`, the existing proposal-and-approval contract) | Design D2; slices S0, S3, S4, S6 |
| 3 | Position against the default: Mermaid for a sketch, chrona when dates have to be right, the plan lives in git, and the same input must produce the same picture next quarter | Design D1.4 |
| 4 | Order: #120, skill, MCP server | Design D3 (confirmed with one revision: a prerequisite refactor) |
| 5 | (comment 2026-09-22 correction) Argue against hand-placed pictures, not only Mermaid; consider one reference file per topic and a worked example | Design D1.4, D1.2 |

The issue stays open after this pack; no slice is implemented here.

## Open decisions (each is resolved in the design or put to the lead)

1. Skill location and delivery: repo directory, wheel, or both; a `chrona skill`
   command or not (D1.1; **lead**).
2. How the skill's commands are tested so it cannot rot (D1.3; decided).
3. MCP dependency: the SDK, its pin, optional extra versus separate distribution,
   or a hand-written stdio protocol (D2.1; **lead**).
4. Tool set, schemas, path scoping, diagnostics, determinism, images, Windows
   (D2.2 to D2.8; decided, with the numeric limits marked as initial values).
5. Mutating tools: whether v1 has any, given the approval exchange is not
   implemented (D2.7; **lead**).
6. The layer rule: the brief wants the MCP adapter to import use cases only, but
   `operational/` cannot be fronted by a use case without a cycle (D2.9; **lead**).
7. Compatibility with #148 (terse syntax) and the source-position follow-up (D4).

## Responsibility boundaries

| Concern | Owner | Not the owner |
| --- | --- | --- |
| Semantics, scheduling, diagnostics codes | `core`, `scheduling` (unchanged) | skill, MCP adapter |
| One pipeline per request (validate, schedule, draft render, failure report) | `usecases/` (new modules in S0) | `app/cli.py`, MCP adapter |
| Argument grammar, stdout/stderr/exit formatting | `app/cli.py` | use cases |
| Tool schemas, workspace scoping, result envelope | `app/agent_*` (SDK-free) | SDK binding |
| Protocol transport (stdio, JSON-RPC) | `app/mcp_server.py` over the SDK | tool core |
| Authoring guidance for agents | `skills/chrona/` | specification (the skill points to it, never restates a rule) |

## Design review questions

1. Does S0 change any observable CLI byte (stdout, stderr, exit code, SVG)?
2. Can every path an agent can name reach the filesystem only through
   `core/store_address.py`, including paths inside documents and a Store config's
   `root`?
3. Can an agent obtain a result that differs between two runs on the same inputs
   (clock, host path, ordering, install-dependent default)?
4. Does any tool offer a way around Store integrity defaults (#723/#727)?
5. Does the skill promise anything (a code meaning, a flag, a preset id) that a
   test does not execute?
6. Is the SDK dependency absent from a default `pip install chrona`, and does the
   CLI still import without it?
7. Does the design stay compatible with a terse front end that compiles to Project
   YAML (#148) without teaching the MCP layer a syntax?

## Acceptance evidence for the design pack

- Four published files (this one, the design, the architecture review with
  findings, the implementation plan), every relative link resolving.
- `tools/check_issue_acceptance_reviews.py` exit 0; `conformance` docs checks green.
- No product code, schema, example or derived document changed.

## Order of design slices

1. Baseline and survey re-check (this file).
2. Design (decisions D1 to D4 with consequences).
3. Architecture review (findings F1 to F13, dispositions; lead decisions L1 to L5).
4. Implementation plan (slices S0 to S7, each with files, tests, proof, prohibitions).
