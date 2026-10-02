# Issue #142 — Agent Interface Architecture Review

**Decision:** Accept the design **with conditions**. The skill-first order and the
tool set stand, but two premises of the issue do not hold on `main` (the MCP server
is not a thin adapter over existing use cases; the mutating path has no runtime
approval model), and four decisions need the lead before the slices that depend on
them. Nothing here is a rubber stamp: findings F1 to F4 change the plan.

Reviewed: [design](../../design/issue-142-agent-interface-design-2026-10-01.md),
[design plan](../planning/issue-142-agent-interface-design-plan-2026-10-01.md),
[implementation plan](../planning/issue-142-agent-interface-implementation-plan-2026-10-01.md),
against `main` observed 2026-10-01, ADR-0005, ADR-0025, Spec 09 (§ dependency
direction, the CLI/GUI/AI → Command Engine flow), Spec 10 §9.1, the
[#148 draft-syntax issue](https://github.com/tya5/chrona/issues/148), and the
[#142 issue](https://github.com/tya5/chrona/issues/142) with its 2026-09-22 comments.
Checked by running the CLI in a scratch workspace and reading the sources named in the
findings; not checked, and recorded as such: the Python SDK 2.x API (not installed
here), any agent host's skill discovery or plugin manifest rules, and how an agent
actually behaves with the skill.

## Boundary audit

| Boundary | Decision | Result |
| --- | --- | --- |
| Skill text -> specification | The skill teaches and links; it restates no rule (`references/authoring-model.md` links Specs 05, 06, 07, 33) | Preserved |
| Skill -> CLI | Every command block is run by the existing doc-check (extended to `skills/`); the CLI grammar remains the only authority | Preserved, requires a tool change (F4) |
| MCP adapter -> use cases | Handlers call `usecases/` only | **Does not hold today** (F1, F2); restored by S0 for the first tool set |
| MCP adapter -> filesystem | Only through `core/store_address.py` plus two adapter checks | Preserved with additions (F5, F7) |
| MCP adapter -> SDK | One module imports the SDK; the tool core is SDK-free | Preserved |
| Tool result -> product semantics | Tools mirror CLI verdicts, including defects (validate accepts a cycle) | Preserved (F6) |
| Mutation -> approval model | No mutating tool in the first release | **Premise corrected** (F3) |
| Default install -> optional dependency | `mcp` extra only; `chrona mcp --list-tools` works without it | Preserved |
| Skill/MCP -> #148 | No syntax taught or parsed; only Project YAML paths | Preserved |

## Findings

Severity is the effect on the design if ignored. "Disposition" is what this pack does.

### F1 (high): the MCP server is not a thin adapter; three use cases do not exist

The issue says the server is "a thin adapter" and "nearly free" after #120. On `main`,
`validate` and `schedule` have no use case: `app/cli.py` calls
`core.validation.validate_project` and `scheduling.scheduler.schedule` itself. The
draft-render pipeline (`_run_draft_render`: builtin-preset temp copy through
`copy_builtin_preset`, typesetter checks, `resolve_draft_render`, the version-error
rewrite, `_render_review`, warning emission) is private to the CLI module, and
`resolve_draft_render` sits in `presentation/model/closure.py`, below the use-case
layer. The conversion of failures to typed diagnostics is the `except` ladder in
`main()` (eleven branches), with no importable form.
*Disposition:* accepted and made the first code slice. S0a extracts
`usecases/project_checks.py` and `usecases/failure_report.py`; S0b extracts
`usecases/draft_render.py`. The proof is a CLI characterization suite written
**before** the move (stdout, stderr, exit code, SVG bytes for a fixed scenario set),
green before and after. Without S0 an adapter would have to import
`presentation.model.closure` and duplicate the ladder, giving a second authority for
the error contract.

### F2 (high): `operational/` cannot be fronted by a use case without a cycle

`command-check`, `command-apply`, `actual-*`, `baseline-capture` and
`baseline-compare` live in `operational/` (`command_engine.py`, `baselines.py`).
`tools/check_import_direction.py` lets `operational` import `usecases`, and does not
let `usecases` import `operational`. A `usecases/operational_commands.py` facade
would add `usecases -> operational`, and the tool reports any two-package cycle. The
issue's table (`compare_baseline`, `apply_command`) therefore cannot meet "use cases
only" without moving code.
*Disposition:* the first tool set excludes them. The design offers three options
(explicit adapter override, relocate two modules, keep out) and recommends keeping
them out until S6 is approved. **Lead decision L4.**

### F3 (high): the "existing proposal-and-approval contract" is specified but not implemented

The issue says `ai-command-proposal-v0.1` and `authorization-decision-v0.1` mean
"the mutating path already has an approval model". Searching `src/`, `schemas/` and
`tests/` finds both names only in Spec 10 §9.1 and in
`conformance/ai-command-proposal-v0.1.yaml`: no code validates a proposal, computes a
command fingerprint, evaluates a policy or issues a decision, and UC-06 in the use-case
catalog says "Library + tests, Not exposed". What runs is a base-revision
compare-and-set and an idempotent replay ledger. A compare-and-set stops a stale write;
it does not decide that an agent may write. Exposing `apply_command` today would either
claim an authorization the product lacks or silently omit one, and Spec 09 routes AI
clients through the Command Engine for exactly that reason.
*Disposition:* the first release has no mutating tool; S6 is conditional and, if
approved, uses a read-only `check_command`, a write-gated `apply_command` bound to the
exact command by a `confirm` identity (named so it is not mistaken for authorization),
host tool-approval annotations, and no emulation of the proposal documents.
**Lead decision L3.** The issue's `apply_command` row is therefore *deferred*, not met,
in any acceptance review.

### F4 (medium): the doc-check mechanism does not see a skill, and its fixture cannot run one

`tools/check_documented_commands.py::documents()` yields only `README.md` and
`docs/guides/*.md`, and `execute()` seeds the temp workspace with `examples/` only.
A skill placed under `skills/` would be unchecked and, if checked, its worked example
file would not exist in the fixture. This is the reason the design extends `documents()`
and the fixture copy rather than adding a parallel checker (a second runner is a second
authority over the CLI grammar, which #372's review rejected). Risk: the skill's
commands must run in CI on every OS in the existing `documented-commands` check; a
PNG command needs the `render` extra, which every CI install already has.
*Disposition:* S1 changes the tool and adds a unit test for the new document set.

### F5 (medium): the shared guard is not enough for a workspace-scoped agent surface

`resolve_store_address` is the right primitive (OS-independent syntax, symlinks
followed, strictly inside the root). Three gaps matter once an agent names paths.
(a) It does not refuse Windows reserved device names (`CON.yaml`, `NUL`); on Windows
opening one addresses a device. (b) It does not require a regular file; a FIFO or
device inside the workspace would block a read. (c) The check and the open are
separate steps (a TOCTOU window). The CLI's own explicit arguments
(`--actual`, `--layout`, ...) use plain `Path` with no guard at all, which is acceptable
for a human at a shell and is not acceptable for an agent surface.
*Disposition:* the adapter adds (a) and (b) in `agent_workspace.py` (OS-independent,
like the guard) and proposes lifting (a) into the shared guard as a separate change; (c)
is recorded as accepted residual risk because the first release writes nothing and the
workspace is the user's own. The design states plainly that the workspace guard is a
safety rail, not a sandbox against a hostile agent that has its own shell.

### F6 (medium): `validate` accepts a dependency cycle, and its success output is a bare `[]`

Observed: a two-task cycle gives `[]` and exit 0 from `validate`, and
`E_UNSUPPORTED_CYCLE` from `schedule` and `render`. `validate` also prints a JSON array
on success and an object on failure. The design mirrors both (tools are use cases, not
new behavior) and normalizes only the envelope shape; the skill and the tool description
say "run `schedule`". Changing `validate` is a semantic decision owned by a separate
issue (candidate successor, not filed here). The review flags the risk that an agent
reports "valid" for a cyclic plan if it trusts `validate_project` alone.

### F7 (high for the Store tools, none for the first release): Store config `root` is unconstrained and `init --example` writes a host path

`store-config-v0.1` accepts any string for `root`;
`discover_store_configuration` walks upward from the start directory through every
parent; `chrona init --example` writes `root: <absolute path of the creator's
machine>`. Used from an agent, a config can point a Store at any directory the process
can read, and a committed example Store is not portable (a clone elsewhere refers to the
original absolute path). The first release does not read a Store, so nothing ships
exposed. *Disposition:* S6 must pass an explicit `<workspace>/.chrona/store.yaml` and
refuse a root outside the workspace (`E_MCP_STORE_OUTSIDE_WORKSPACE`). Recommended
successor (not filed): resolve a relative `root` against the config file's directory and
write relative roots from `init`. Integrity defaults (#723, #727) are untouched: no tool
accepts an integrity override, and no Store tool ships before the successor is decided.

### F8 (medium): diagnostics are weakest exactly where an agent depends on them

Observed on 2026-10-01: a bad `scheduled` object gives one structural diagnostic from
`validate` ("expected one permitted form: mode='fixed-point'; ...") and **fourteen**
rows from `render`, many exact duplicates, one per union branch; `E_BUILTIN_PRESET_UNKNOWN`
has a message equal to its own code and no list of valid ids; render warnings (`W_LAYOUT_*`)
carry a code and ledger fields but no message; `E_INPUT_IO` embeds the host path in the
errno text; the last-resort `E_TOOL_FAILURE` returns `str(error)`. The #371 policy
covers some of this and the corpus is large.
*Disposition:* the adapter (never the CLI, whose bytes are frozen by S0) drops exact
duplicates, caps at 50, scrubs paths and replaces `E_TOOL_FAILURE` text with a fixed
message; the skill's diagnostics table (tested, D1.3) supplies the explanations the
product does not; `list_presets` answers the unknown-preset case. The real repair
belongs to a diagnostic-actionability successor; this design does not scope it.

### F9 (medium): where an agent host looks for a skill is not under our control

`skills/chrona/` at the repository root is the right canonical place (reviewable, and
shaped like a plugin's `skills/` directory), but a host discovers skills from its own
directories (for example a project's `.claude/skills/`), and a symlink would break
Windows checkouts and the wheel. So delivery depends on a command (`chrona skill copy`)
rather than on a convention the repository cannot guarantee. The review could not verify
any host's current discovery or plugin-manifest rules from inside this repository;
the design therefore makes the plugin manifest an optional, separately verified slice
and does not depend on it. A user who never runs the command and never opens the
repository gets no skill; the guide and the README link are the only mitigation.

### F10 (medium): dependency weight and SDK churn

`mcp` 2.2.0 requires pydantic, starlette, uvicorn, httpx, sse-starlette, PyJWT with
crypto (a compiled `cryptography`) and, on Windows, `pywin32`; chrona's default
install is PyYAML, jsonschema and fonttools. The SDK is two months into a new major
(2.0.0 on 2026-07-28) with a parallel 1.30 line, and the server class was renamed. A
stdio-only server uses none of the HTTP stack. *Disposition:* optional extra, range pin
with a major cap, SDK confined to one module, a CI lane on floor and latest, the
three-OS matrix installing the extra, and a documented fallback (hand-written stdio) if
the transitive set blocks a platform. **Lead decision L1.**

### F11 (low): the tool set departs from the issue's table

The issue maps `render_review` to `usecases/render_review.py`. That use case consumes a
resolved closure; from an agent's point of view the useful input is a Project path and a
preset, which is the draft path, and the immutable path needs a Store (F2, F7). The design
names the draft tool `render_draft` and reserves `render_review` for the Context path
(S6). `compare_baseline` and `apply_command` are deferred (F2, F3). The acceptance
review for #142 must list these as `narrowed` or `deferred` with this review as the
reason, not as `met`.

### F12 (low): cost and cancellation

Inline SVG text costs an agent context (14 KB for 3 objects, 65 KB for 24) and gives it
nothing it can see; a PNG image is a fixed cost and viewable. A render cannot be
cancelled and takes 1.6 to 4.8 s for the plans measured; asking for both the SVG artifact
and an image preview renders twice in the first release (the use case produces one target
per call). The design defaults to an image, caps inline payloads, serializes calls and
documents the limits; a one-pass "SVG plus raster of the same Scene" use case is a
later optimization, not a contract change.

### F13 (low): new public surface needs the repository's own gates

`chrona skill copy` and `chrona mcp` change the generated CLI reference and fail the
documented-surface gate until a guide documents each command and option;
`check_module_reachability.py` is satisfied only through the CLI import; the `E_MCP_*`
codes enter the diagnostic inventory (a derived document the sync regenerates, which a PR
must not edit); a tool/result contract of this kind is public and belongs in a numbered
specification (Spec 66, written in S3) rather than only in a design file. The design
chooses a specification plus a registry-derived JSON Schema checked by test over adding
files under `schemas/` in the first release, to avoid the schema-inventory and
annotation gates for a contract that will still change; promotion to `schemas/` is a
later step. *Disposition:* each slice lists the gate it touches.

## Whole-system consistency

- **ADR-0005 (renderer is not source of truth):** preserved. No tool reads an SVG
  back; `render_draft` has no input that is a rendered artifact, and the `contentIdentity`
  is of an output, never an input.
- **ADR-0025 (immutable automation commands) and Spec 09 (AI clients reach the Command
  Engine):** the first release does not mutate, so it neither bypasses nor weakens the
  engine; S6 routes only through it.
- **#723 and #727 (Store integrity):** no tool exposes the opt-out; the only integrity
  source remains the Store config entry.
- **#372 (executable guides):** extended, not replaced; the skill's commands are in the
  same run, and its skip marker means the same thing.
- **#376 and #377 (minimal init, default preset):** the skill's loop is exactly
  `init` plus the draft render; it adds no second onboarding path.
- **#429 (presets):** the skill and `list_presets` use the builtin ids, and a test pins
  the ids named in the skill to `chrona preset list`, so a renamed preset breaks a test
  rather than a conversation.
- **#148 (terse syntax, parallel design):** the design takes `project` as an opaque
  path to a document the ingress understands. It does not parse, generate or describe
  the terse form; when #148 accepts a terse file directly in `render`, the tools accept
  it with no change, and a `chrona compile` tool would be one line in the registry. The
  #148 prior-art comment asks for source ranges in diagnostics; the result schema
  reserves an additive `sourceRange` and invents none.
- **Determinism:** no timestamp, duration or host path enters a result; two real
  sources of variation are named and handled (installed fonts, excluded by not offering
  `--system-fonts`; PNG bytes, tied to the exact `resvg-py` pin).
- **Owner positioning (README, PR #424, board #454 P2):** the skill is where "design once,
  render every revision" becomes an instruction an agent follows, and its Mermaid
  section argues from the owner's edge (fidelity, determinism, diagnostics, reuse)
  against hand-placed pictures, the comparator that matters after the 2026-09-22
  correction. PR #424 is open and edits the README; the skill must not quote README
  wording that PR changes, and S1 rebases on it.

## Rejected alternatives

- **A parallel documentation checker for the skill:** a second authority over CLI
  grammar; rejected for the reason #372 rejected running arbitrary shell.
- **Shelling out to the CLI from the MCP server:** simplest, but returns diagnostics
  as text to re-parse, pays interpreter start-up on every call (0.75 s observed), cannot
  scope paths below the process, and bypasses the use-case layer the issue asks the
  adapter to use.
- **An MCP tool per CLI command:** exposes font and icon import, materialize
  and gallery commands that write files, with no agent need; the surface should be the
  agent's task, not the CLI's inventory.
- **Returning the SVG as the default:** costs context and shows nothing to the model.
- **A bundled skill without a repository copy, or the reverse:** see D1.1.
- **An HTTP transport "for chat clients":** needs authentication, origin policy and a
  threat model that this project has not scoped; a local stdio process inherits the
  user's trust boundary and nothing larger.
- **Stub authorization** (a fixed `allow` decision so `apply_command` can ship): a
  fake approval is worse than none.

## Lead decisions

| ID | Decision | Recommendation | Consequence |
| --- | --- | --- | --- |
| L1 | New dependency: the `mcp` SDK | Optional extra `chrona[mcp]`, `mcp>=2.2,<3`, SDK in one module | Heavy transitives only for users who opt in; one lane to maintain; fallback documented |
| L2 | Packaging of the skill | Repository `skills/chrona/` plus wheel `force-include` plus `chrona skill copy` | One new CLI command; about 20 KB in the wheel; version-matched skill |
| L3 | Mutating tools | None in the first release; S6 only with `check`/`confirm`/write flag if approved | `apply_command` row deferred; no false authorization claim |
| L4 | Layer rule for `operational/` | Keep store tools out until S6; then one explicit, recorded override | First release stays use-cases-only; S6 pays an exception |
| L5 | Scope of the first MCP release | Read-only, draft path, four tools, SVG or PNG, stdio | Coding agents use skill plus CLI for files; chat clients get inline preview |

## Verdict by criterion

| Criterion | Result |
| --- | --- |
| Layer boundaries and import direction | Holds after S0; S0 itself must be proven byte-identical |
| Failure behavior | Typed, deduplicated, scrubbed, never a traceback; protocol errors left to the SDK |
| Extension points | Tool registry (one ToolSpec per use case); `sourceRange`; tool-set version |
| Intended incompatibilities | None for existing behavior; new surface only |
| Whole-architecture check | Consistent with ADR-0005, ADR-0025, Spec 09, #148, #723/#727 |
| Open risks carried | F5(c) TOCTOU, F6 validate gap, F8 diagnostics quality, F9 host discovery, F10 SDK churn |
