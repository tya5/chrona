# Design: Agent Interface, a Skill and an MCP Surface (#142)

**Status:** Proposed, pending architecture review and lead decisions.
**Plan:** [issue-142-agent-interface-design-plan-2026-10-01.md](../planning/active/issue-142-agent-interface-design-plan-2026-10-01.md)
**Review:** [issue-142-agent-interface-architecture-review-2026-10-01.md](../reviews/current/issue-142-agent-interface-architecture-review-2026-10-01.md)
**Implementation plan:** [issue-142-agent-interface-implementation-plan-2026-10-01.md](../planning/active/issue-142-agent-interface-implementation-plan-2026-10-01.md)
**Depends on:** Spec 09 (application architecture), Spec 10 §9.1 (AI proposal and authorization), Spec 57 (schedule analysis), `src/chrona/core/store_address.py`, the Store config contract (#723, #727).
**Does not design:** the terse draft syntax (#148, a parallel design by another author).

## 0. Principle

One engine, three front ends. The CLI, the skill and the MCP server expose the same
use cases; none may add behavior. A tool is a use case with a typed envelope. If a CLI
command and the tool of the same name ever disagree on a verdict, a diagnostic code or
a byte of output, that is a defect in one of them, and a cross-surface equality test
(S3) is the standing proof.

Decisions are labelled **Decided** (the design commits) or **Lead** (a recommendation
with its consequence, awaiting the lead engineer).

## 1. The skill

### D1.1 Location and delivery

**Lead: ship in the repository and in the wheel.**

- Canonical source: `skills/chrona/` at the repository root, in the layout every
  agent-skill host reads (`SKILL.md` with YAML front matter, optional `references/`
  and `examples/` beside it). It is a plain tree under version control, reviewed like
  any document, and it matches the plugin layout (`<plugin root>/skills/<name>/SKILL.md`),
  so a later `.claude-plugin/` manifest can make the repository installable without
  moving a file. (The exact plugin manifest shape must be verified against the host's
  current documentation when that optional slice is taken; this design does not depend
  on it.)
- Wheel: `[tool.hatch.build.targets.wheel.force-include]` adds
  `"skills/chrona" = "chrona/resources/skills/chrona"`, the same mechanism that already
  carries `schemas` and `examples/halcyon-1`. There is no second tree in git, so the
  copy cannot drift; a test compares the packaged tree with the source tree
  byte for byte in both editable and wheel installs.
- Delivery to an agent: a new command `chrona skill copy --output DIR`, which copies
  the packaged tree into an **empty or absent** directory and refuses a non-empty one
  (the exact grammar of `chrona preset copy <id> --output DIR`, which already exists).
  A user runs `chrona skill copy --output .claude/skills/chrona` (project scope) or
  the host's user-level skills directory. The skill's own text says how to refresh it
  (copy again into a new directory and diff).
- Why not "repository only": a user who `pip install chrona` has no clone, and the
  skill must match the installed CLI version, so it must travel with the version.
  Why not "wheel only": reviewers and hosts that install from a git URL need a
  readable tree, and the skill is the first thing a contributor will edit.
- Consequence: one new public CLI command (the generated `docs/guides/cli-reference.md`
  changes; the doc-check surface gate requires the command and its option to be
  documented in a guide, which D1.3 supplies), roughly 20 KB added to a wheel with a
  5 MB budget, and a `skills/__init__.py` (not packaged) so `importlib.resources` can
  resolve the source tree in development, the way `schemas/__init__.py` does.

### D1.2 Content

**Decided.** Files:

```text
skills/chrona/SKILL.md                      # at most 200 lines; host hard cap 500
skills/chrona/references/authoring-model.md
skills/chrona/references/diagnostics.md
skills/chrona/references/mermaid-or-chrona.md
skills/chrona/examples/launch.yaml          # a real Project that validates, schedules, renders
```

`SKILL.md` front matter: `name: chrona` (equal to the directory name) and a
`description` of at most 1 024 characters that names the triggers (Gantt chart,
project timeline, schedule with dependencies or working days, milestones, roadmap
slide, plan versus actual) and the one-line promise (compute the schedule and draw it
deterministically from a YAML plan). `SKILL.md` contains, in this order:

1. **When to use.** Dates that must be right (working-day calendars, dependencies,
   lags), a plan that will be edited and re-rendered, a slide a reviewer will diff,
   a picture that must be reproduced next quarter.
2. **Rules that cost an agent the most when broken.** Never hand-write or edit SVG;
   chrona derives it. Never compute a date by hand: read it from `chrona schedule`
   (an `end` is exclusive, the first working day after the last day of work: a
   5-working-day task starting Monday 2026-11-02 ends Monday 2026-11-09, and a
   15-working-day task whose range crosses a calendar exception moves again, so a
   hand count is wrong exactly where it matters). Edit `project.yaml`, then re-render, never
   the generated file. Do not edit a copied preset in place to change one token;
   `chrona preset copy` once, then edit the copy. Treat a rejected render as
   information: read `code` and `sourceRef` first.
3. **The loop.** `init`, edit, `validate`, `schedule`, `render`, read diagnostics,
   fix, re-render; and "an identical input produces identical bytes, so a changed
   SVG means a changed plan".
4. **The model** in five lines (D1.2a), pointing to `references/authoring-model.md`.
5. **The draft path** instead of the eight-file ceremony (D1.2b).
6. **Diagnostics** in one paragraph and a pointer to `references/diagnostics.md`.
7. **Choosing a tool** in four lines and a pointer to `references/mermaid-or-chrona.md`.

#### D1.2a The authoring model (taught, not restated)

Project is the semantic truth: objects, schedule modes (`fixed-point`, `fixed-span`,
`scheduled` with an `amount` such as `15wd`, `rollup`), relations with endpoints and
lags, calendars. View selects what is shown and in what rows. Theme paints (tokens).
Color Scheme assigns colors. Layout composes the surface. The CLI renders, and nothing
a renderer produces is ever read back as project data. The reference file links
Spec 05 and Spec 06/07/33 for the rules and carries no rule of its own. This is the
vocabulary of the owner's positioning: a designer or agent designs once, chrona
renders every revision.

#### D1.2b The draft path, not eight files

The Project, View, Theme, Color Scheme, Layout, Actual Set, Summary Profile and Detail
Profile are the full model. The skill teaches the path that exists today and needs
only two of them: the agent writes `project.yaml` (and optionally `actual.yaml`), and a
**preset** (bundled `chrona-default-draft`, or one of the seven builtin ids from
`chrona preset list`) supplies View, Theme, Scheme, Layout and Detail together.
`render` takes explicit `--view/--theme/--scheme/--layout` only to override a preset
member. The skill states that an Immutable Render Context, snapshots and Store config
are the reproducible-evidence path and that an agent should not reach for them unless
the user asks for pinned evidence.

#### D1.2c Diagnostics the agent meets

`references/diagnostics.md` is a table of `code | command that emits it | what it
means | what to change`, limited to codes observed on the draft path. Verified by
running the CLI on 2026-10-01:

| Code | Meaning for the agent |
| --- | --- |
| `E_SCHEMA` (validate, schedule) and `E_PROJECT_SCHEMA` (render) | Structural error at `sourceRef`. Render can repeat one finding once per union branch (14 findings were observed for one bad object): read the first `sourceRef`, fix, re-run. For `/objects/<id>/schedule` the legal forms are `fixed-point` (`at`), `fixed-span` (`start`, `end`), `scheduled` (`amount`) and `rollup`. |
| `E_REFERENCE` | An id (relation endpoint, calendar, parent) names nothing. |
| `E_ENDPOINT_MODE_MISMATCH` | The endpoint does not exist for that object's schedule mode (a gate has `at`, not `start`). |
| `E_INVALID_SPAN`, `E_INVALID_AMOUNT`, `E_CALENDAR_REQUIRED` | A span must have `start < end`; an `amount` is a positive `d`, `w` or `wd`; `wd` needs a calendar. |
| `E_UNSUPPORTED_CYCLE`, `E_UNSATISFIABLE_DEPENDENCIES` | Dependency cycle. Emitted by `schedule` and `render`, **not by `validate`** (a two-task cycle validates as `[]`). Run `schedule`, not only `validate`. |
| `E_FIXED_TARGET_VIOLATION`, `E_CONTRADICTORY_BOUNDS`, `E_NON_WORKING_ANCHOR` | A fixed date or constraint contradicts what the dependencies require, or falls on a non-working day. Move the fixed date or loosen the relation or constraint. |
| `E_INPUT_IO`, `E_INPUT_YAML`, `E_COMMAND_SYNTAX` | Exit 2: a missing file, invalid YAML, or a bad flag. Not a plan problem. |
| `E_BUILTIN_PRESET_UNKNOWN` | `--preset` is not a builtin id; run `chrona preset list`. (The message is only the code today; see review finding F8.) |
| `E_RENDER_OUTPUT_EXTENSION`, `E_RENDER_OUTPUT_FORMAT_MISMATCH` | Output suffix unknown or disagrees with `--format`. |
| `E_RENDER_RASTERIZER_UNAVAILABLE` | PNG needs the `render` extra (`pip install 'chrona[render]'`). |
| `E_RESOURCE_VERSION_UNSUPPORTED` | A copied preset is stale; copy it again and re-apply edits. |
| `W_LAYOUT_*`, `W_FONT_*` (stderr, exit 0) | The render succeeded and something is clipped, suppressed or substituted. Shorten a title, widen `--viewport`, or accept. |
| `I_*` (stderr, exit 0) | Informational (a treatment the visual profile cannot paint, plot labels suppressed). No action needed. |

Warnings carry no `message` today, only a code and ledger fields, so the table is the
agent's only explanation; that is why D1.3 tests it.

### D1.3 How the skill cannot rot

**Decided.** Four mechanisms, all in CI (the `documented-commands` check already runs
inside `conformance`).

1. **Every command block is run.** `tools/check_documented_commands.py::documents()`
   additionally yields `skills/chrona/SKILL.md` and `skills/chrona/references/*.md`;
   the fixture workspace for `execute()` copies `skills/` beside `examples/`. The same
   fence parser validates every `chrona` line against argparse and runs it. A block
   that cannot run (a deliberately failing example) carries the existing
   `<!-- chrona:doc-check skip: reason -->` marker with a reason, and a rejected
   example is shown as a quoted result, not as a command to run. The reverse surface
   gate is unchanged: it needs each CLI command documented once anywhere.
2. **The worked example is a file, not prose.** `examples/launch.yaml` is validated,
   scheduled and rendered by commands in the skill that doc-check runs. A unit test
   asserts that any YAML fence in the skill equals the corresponding example file
   (so an edited fence without the file, or the reverse, fails).
3. **Every diagnostic code in the skill is real and means what it says.**
   `tests/unit/skills/test_chrona_skill_diagnostics.py` (a) extracts every
   `E_/W_/I_` token from the skill and fails if one is not constructed anywhere in
   `src/chrona` (reusing `tools/diagnostic_inventory.py`'s scanner), and (b) for each
   code in the D1.2c table that is reachable from a small synthetic Project, provokes it
   through `chrona.app.cli.main` and asserts the code is emitted by the command the
   table names. A code that is only reachable from a corpus is listed in a
   `# unprovoked: reason` allowlist with a reason, like the doc-check skip.
4. **Shape checks.** Front-matter `name` equals the directory, description length is
   within the limit, `SKILL.md` is at most 200 lines, and every relative link
   resolves. A test pins the preset ids named in the skill to `chrona preset list`.

What this does not prove: that an agent following the skill produces a good plan. That
is evaluated, not unit-tested; S1 records a small manual scenario set (a four-task plan
with a holiday, a cycle introduced by mistake, a preset change) in the implementation
review, with the transcript attached to the PR, and does not gate on it.

### D1.4 Mermaid versus chrona, honestly

`references/mermaid-or-chrona.md` states the trade, with its cost to chrona:

- **Use Mermaid** when a sketch inside a README or PR must render with no tooling,
  the task count is small, and nobody will recompute it. Mermaid's `after a1, 20d`
  is shorter than chrona's Project today (a three-task plan is about a dozen YAML
  lines against a one-line-per-task form). Until the terse form of #148 exists,
  chrona's input is longer and its structural errors can be terse (see F8). Chrona
  also needs Python and, for PNG, the `render` extra.
- **Use a hand-drawn or agent-placed picture** (SVG or an image skill) only for a
  one-off illustration whose dates are decoration. The hazard is not ugliness: a
  hand-placed bar is correct only until someone edits the plan, because nothing
  recomputes it, and the next prompt draws a different picture. This is the
  comparison that matters now that agent skills for hand-placed diagrams are
  popular (the 2026-09-22 survey correction), and it is the one the skill makes.
- **Use chrona** when dates come from durations, working calendars, dependencies and
  lags; when the plan lives in git and is edited again; when a reviewer needs the
  same input to yield the same bytes next quarter; when actuals or a baseline are
  compared to plan; when a Theme or preset must be shared across many plans.
- The skill never promises what chrona lacks: no resource leveling at the draft
  surface, no interactive editing, cycles are rejected rather than analysed.

### D1.5 Compatibility with #148

The skill never teaches a syntax beyond the Project YAML. `SKILL.md` says "the
Project is a YAML file"; if #148 lands, one added paragraph and one reference file
(`references/terse-form.md`) describe it, and the doc-check rule above runs its
commands. The skill must not describe `chrona compile` or any #148 grammar before it
exists.

## 2. The MCP server

### D2.1 Transport, dependency, packaging

**Transport (Decided):** stdio only. No HTTP, no SSE, no listener, no authentication
(section 4). The command is `chrona mcp [--workspace DIR] [--list-tools]`, a
subcommand of the existing CLI, so there is no new console script, `python -m chrona mcp`
works on Windows without `Scripts` on `PATH`, `check_module_reachability.py` is
satisfied through the CLI import, and a host config is
`{"command": "chrona", "args": ["mcp", "--workspace", "."]}` or
`uvx --from 'chrona[mcp]' chrona mcp`.

**SDK (Lead):** the Python SDK, PyPI `mcp`, as an optional extra
`mcp = ["mcp>=2.2,<3"]` in `pyproject.toml`.

| Option | Weight | Risk | Verdict |
| --- | --- | --- | --- |
| `chrona[mcp]` extra, `mcp>=2.2,<3` | Not in a default install. Transitives for a stdio server: pydantic, starlette, uvicorn, httpx, sse-starlette, PyJWT with crypto (a compiled `cryptography`), and `pywin32` on Windows | 2.0 shipped 2026-07-28 with a renamed server class; 1.30 is maintained in parallel. API may still move within 2.x | **Recommended.** Only `app/mcp_server.py` imports the SDK; the tool core is SDK-free, so a switch to `mcp>=1.30,<2` or a re-pin costs one module |
| Hand-written stdio JSON-RPC, no dependency | About 250 lines | Chrona then owns protocol-version negotiation, `initialize` capabilities, cancellation, pagination and error shapes, and tests them only against an SDK client anyway | Fallback if the transitive set becomes a problem on a platform |
| Separate distribution `chrona-mcp` (precedent: `packages/chrona-fonts-noto-cjk`) | Keeps `chrona` extras minimal | A second release stream version-locked to chrona's internal API; the subcommand could not live in `chrona` | Defer until a release-cadence reason appears |

Exact-versus-range pin: the `render` extras are pinned exactly because they change
output bytes. The SDK changes no output byte (the tool core builds every result), so a
range with a compatible-major cap is right; a dedicated CI lane exercises the floor
and the latest release. Without the extra, `chrona mcp` exits 2 with `E_MCP_UNAVAILABLE`
and the install hint, and `chrona mcp --list-tools` still works (it needs no SDK), so
the documented-command check can execute it.

PNG requires the existing `render` extra independently (`chrona[mcp,render]`); the
server reports PNG availability in its result rather than failing at start-up.

### D2.2 Modules and layers (**Decided**, one rule is **Lead**, see D2.9)

```text
app/agent_workspace.py   WorkspaceScope: path guard, scrubber, size caps          (SDK-free)
app/agent_tools.py       ToolSpec registry, JSON schemas, handlers, envelope      (SDK-free)
app/mcp_server.py        SDK binding: registers ToolSpecs, stdio run, resources   (the only SDK import)
app/cli.py               `chrona mcp` subcommand; lazy import of the two above
usecases/project_checks.py   validate and schedule as use cases                   (S0a)
usecases/draft_render.py     the draft-render pipeline lifted out of cli.py        (S0b)
usecases/failure_report.py   exception to typed diagnostics, shared with cli.py    (S0a)
```

The handlers call `usecases/` only (plus `core.store_address` and the `core`
diagnostic and identity types, which point inward). The CLI and the handlers share
`failure_report`, so "typed, never a raw traceback" is one implementation.

### D2.3 Tools

**Decided** for the first release (all read-only, all workspace-scoped). The issue's
five names are kept where the meaning survives; `render_review` becomes
`render_draft` because the issue's table maps it to the Context path (`render-review`,
which needs a Store) while the useful agent path is the draft path that #120 made
possible; the immutable path is `render_review` in a later slice (S6). Every
tool maps to exactly one CLI command.

| Tool | CLI equivalent | Use case |
| --- | --- | --- |
| `validate_project` | `chrona validate P` | `usecases/project_checks.validate_project_file` |
| `schedule_project` | `chrona schedule P` | `usecases/project_checks.schedule_project_file` |
| `render_draft` | `chrona render P ...` | `usecases/draft_render.render_draft` |
| `list_presets` | `chrona preset list` | `usecases/preset_library.list_builtin_presets` |

Later (S6, **Lead**): `render_review`, `compare_baseline`, `workspace_revision`,
`check_command`, `apply_command`, `apply_authoring_command`, `init_project`.

Mirroring means mirroring defects: `validate_project` returns `ok` for a cyclic plan
exactly as `chrona validate` does. The tool description says so and points to
`schedule_project`. Changing validate to catch cycles is a semantic change owned by a
separate issue, not by the agent interface.

#### D2.3a Common definitions (JSON Schema 2020-12)

```json
{
  "$defs": {
    "workspacePath": {
      "type": "string", "minLength": 1, "maxLength": 512,
      "description": "A '/'-separated path relative to the workspace root. No drive, no leading '/', no '..', no backslash or colon."
    },
    "sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
    "status": {"enum": ["ok", "rejected", "failed"]},
    "diagnostic": {
      "type": "object", "required": ["code", "severity", "component", "sourceRef", "message"],
      "additionalProperties": false,
      "properties": {
        "code": {"type": "string", "pattern": "^[EWI]_[A-Z0-9_]+$"},
        "severity": {"enum": ["error", "warning", "info"]},
        "component": {"type": "string"},
        "sourceRef": {"type": "string", "description": "RFC 6901 JSON pointer into the named document, or '/'."},
        "message": {"type": "string"},
        "revisionRefs": {"type": "array", "items": {"type": "string"}},
        "resourceKind": {"type": "string"}, "resourceIdentity": {"type": "string"},
        "phase": {"type": "string"}, "rule": {"type": "string"},
        "detail": {"type": "object", "description": "Remaining ledger fields of a warning or info, verbatim."}
      }
    },
    "envelope": {
      "type": "object", "required": ["status", "diagnostics"],
      "properties": {
        "status": {"$ref": "#/$defs/status"},
        "diagnostics": {"type": "array", "items": {"$ref": "#/$defs/diagnostic"}, "maxItems": 50},
        "omittedDiagnostics": {"type": "integer", "minimum": 1}
      }
    }
  }
}
```

`status` follows the CLI exit code: `ok` is exit 0, `rejected` is exit 1 (the request
was understood, the document is refused), `failed` is exit 2 or any adapter-level
refusal. Every tool result is `envelope` plus its own fields. `rejected` is a normal
result, not an MCP error: the MCP `isError` flag is set **only for `failed`**, because
a validation tool that reports a plan's problems has done its job, and a client that
treats a rejection as a tool crash tends to retry blindly. Consequence: an agent
must read `status`, not only `isError`; `chrona://guide/authoring` and the tool
descriptions say so.

Unknown tool names, malformed arguments and missing required fields are MCP protocol
errors produced by the SDK from the input schema (`additionalProperties: false` on
every input), never a chrona envelope.

#### D2.3b `validate_project`

Input: `{"project": workspacePath}` (required, no other property).
Output: `envelope` plus `"projectIdentity": sha256` of the file bytes when readable.
`ok` carries `diagnostics: []` (the CLI's bare `[]` becomes the envelope).

#### D2.3c `schedule_project`

Input: `{"project": workspacePath}`.
Output: `envelope` plus, when `ok`:

```json
{
  "placements": {"<objectId>": {"start": "2026-11-02", "end": "2026-11-24"}},
  "analysis": {"criticalObjectIds": ["kickoff", "ship"], "totalFloat": {"build": 4}}
}
```

A placement is `{start, end}` or `{at}` with ISO dates. `totalFloat` is the
non-negative integer calendar distance of Spec 57. Key order is the Project's object
order, exactly as the CLI prints it.

#### D2.3d `render_draft`

Input (`additionalProperties: false`):

| Property | Type | Meaning |
| --- | --- | --- |
| `project` (required) | `workspacePath` | Draft Project YAML |
| `actual` | `workspacePath` | Actual Set YAML |
| `preset` | string | A builtin id (`list_presets`) or a workspace path ending `.yaml` or `.yml`; omitted means the bundled `chrona-default-draft` |
| `view`, `theme`, `scheme`, `layout` | `workspacePath` | Override one preset member, as the CLI flags do |
| `viewport` | string `^[1-9][0-9]{2,4}x([1-9][0-9]{2,4}\|auto)$` | default `1600xauto` |
| `locale` | `en-US` or `ja-JP` | default `en-US` |
| `format` | `svg` or `png` | the artifact that is identified; default `svg` |
| `inline` | `none`, `image` or `svg` | what the result carries; default `image` |

Not offered in the first release, with the reason: `--system-fonts` (depends on the
host's installed fonts, so outputs would differ between machines), `--font-metrics`
and `--icon-catalog` (paths into arbitrary descriptors; a later, guarded addition),
`--visual-profile` (a preset names its preferred profile; an explicit value is an
advanced override that needs the same validation as the CLI and can be added with the
enum), `typst` and `tikz` (need a typesetter descriptor), `pdf` (a binary artifact
the agent cannot read), `--emit-scene` (writes a file), and anything named
`allow-missing-content-identity`.

Output: `envelope` plus, when `ok`:

```json
{
  "format": "svg", "contentIdentity": "sha256:...", "byteLength": 14614,
  "pngAvailable": true,
  "warnings": [{"code": "W_LAYOUT_VISIBLE_OVERFLOW", "severity": "warning",
                "sourceRef": "/root/children/1", "message": "...", "detail": {}}]
}
```

Content blocks (MCP `content`): block 0 is always the text JSON of the structured
result (so a client that ignores structured output loses nothing). With
`inline: "image"` block 1 is `{"type": "image", "mimeType": "image/png", "data": <base64>}`
rendered from the same inputs; with `inline: "svg"` block 1 is an embedded resource
`{"type": "resource", "resource": {"uri": "chrona://render/<contentIdentity>.svg",
"mimeType": "image/svg+xml", "text": "<svg ...>"}}`. If PNG is unavailable the image
is omitted and `pngAvailable` is `false` (no failure, no silent substitution); a
request for `format: "png"` without the extra is `failed` with the CLI's
`E_RENDER_RASTERIZER_UNAVAILABLE`.

Why the default is an image, not SVG text: a 3-object plan is 14 KB of SVG and the
24-object ASTER plan 65 KB (observed), which an agent pays for in context and cannot
interpret as a picture, while the same plan as PNG is a fixed-cost image that a
multimodal client can look at. SVG text is one flag away for a client that wants
to forward it. Inline payloads are capped (`E_MCP_RESULT_TOO_LARGE` above 1 MiB of
SVG or 1.5 MiB of PNG; initial values to be tuned from S3 measurements) and the
error says to lower the viewport or use the CLI, where a file output has no cap.

`warnings` come from the same ledger that the CLI prints to stderr
(`RenderedReview.warning_records` and info records) as `warning` or `info` severity
entries; none is dropped, none is invented.

#### D2.3e `list_presets`

Input: `{}`. Output: `envelope` plus
`{"presets": [{"id": "mission-light", "gallerySet": "..."}], "default": "chrona-default-draft"}`
in the CLI's order. It exists so that `E_BUILTIN_PRESET_UNKNOWN` (whose message is
only the code) can be answered without a guess.

### D2.4 Path scoping (**Decided**)

The server starts with `--workspace DIR` (default: the current directory). It resolves
`DIR` once, refuses a filesystem root (`E_MCP_WORKSPACE_TOO_BROAD`, exit 2), and from
then on only uses paths below it.

1. **Every path an agent supplies** passes through `resolve_store_address(workspace,
   value, charset="file-name")`: syntax is OS-independent (no backslash, colon, drive,
   anchor, control character, empty or all-dot segment), the resolved target
   (symlinks followed) must lie strictly inside the workspace. `charset="file-name"`
   is deliberate: plan file names are an operator's, and non-ASCII names such as
   Japanese titles are legitimate; the stricter `address` charset is for Store
   addresses. A refusal is `E_MCP_PATH_SYNTAX` or `E_MCP_PATH_CONTAINMENT`.
2. **Two additions the shared guard does not make**, done in `agent_workspace.py` and
   proposed for the shared guard later: refuse a segment whose stem is a Windows
   reserved device name (`CON`, `PRN`, `AUX`, `NUL`, `COM1` to `COM9`, `LPT1` to
   `LPT9`, with any extension) on every OS, the same OS-independent policy the guard
   already has; and require `is_file()` for every input (no FIFO, device or directory
   is ever opened).
3. **References inside documents** already go through the guard against their own
   directory (preset members, Theme `extends`, icon assets, font assets), so a
   workspace document cannot name a path above its own directory. The adapter adds
   nothing there and does not weaken it.
4. **The Store config** (first used by S6) is not discovered by walking upward (the
   CLI's `discover_store_configuration` walks to filesystem parents). The adapter
   passes the explicit path `<workspace>/.chrona/store.yaml`, and refuses a config
   whose `root` resolves outside the workspace (`E_MCP_STORE_OUTSIDE_WORKSPACE`):
   `root` is an arbitrary string today, and `chrona init --example` writes it
   as an absolute host path (F7).
5. **Size and time.** An input file larger than 2 MiB is refused
   (`E_MCP_INPUT_TOO_LARGE`; YAML alias expansion is otherwise unbounded). Calls are
   serialized by a lock; there is no cancellation (a render cannot be interrupted),
   and the 24-object plan takes 1.6 to 4.8 s, so the first release documents the
   limit rather than hiding it.
6. **No `--allow-missing-content-identity` and no Store integrity override** in any
   tool input. The Store config's own `integrity` field is the only source, as in
   the CLI (#723, #727).
7. **Residual risk:** the check and the open are two steps (a TOCTOU window if
   another process swaps a path component for a symlink between them). The workspace
   is the user's own, the server holds no secret and writes nothing in the first
   release, so this is recorded and accepted.

### D2.5 Diagnostics and errors (**Decided**)

- One implementation of "exception to typed diagnostics": `usecases/failure_report.py`,
  extracted from `main()`'s `except` ladder in S0a, used by the CLI and the tools. The
  CLI's stdout is byte-identical to today.
- The tool layer applies three **adapter-only** transforms that the CLI does not
  (so the CLI contract is untouched): drop exact duplicate diagnostics (the 14-finding
  render rejection contains duplicate rows), cap at 50 with `omittedDiagnostics`, and
  scrub host paths.
- **No raw traceback and no host path ever reaches a result.** `E_INPUT_IO`
  currently carries `str(OSError)` (which contains the path as the process saw it);
  the scrubber replaces the workspace root, in both its given and resolved forms,
  with the empty prefix (leaving the workspace-relative path) and replaces any
  remaining absolute path with `<path>`. The CLI's last-resort `E_TOOL_FAILURE`
  returns `str(error)`; the tool returns the fixed message
  `internal error: <ExceptionClass>`, and the traceback goes to stderr (a stdio server
  may log there; the stream the host does not parse as protocol).
- **Nothing is ever written to stdout except protocol.** No `print` exists outside
  `app/cli.py` today (checked); the adapter configures logging to stderr only, and a
  test fails if a handler writes to `sys.stdout`.
- `status` mapping, `isError`, and protocol errors are as in D2.3a.
- New codes the adapter owns (`E_MCP_*`; component `mcp`): `E_MCP_PATH_SYNTAX`,
  `E_MCP_PATH_CONTAINMENT`, `E_MCP_INPUT_TOO_LARGE`, `E_MCP_RESULT_TOO_LARGE`,
  `E_MCP_WORKSPACE_TOO_BROAD`, `E_MCP_UNAVAILABLE`, and from S6 `E_MCP_WRITE_DISABLED`
  and `E_MCP_STORE_OUTSIDE_WORKSPACE`. Each follows the diagnostic-actionability
  policy of #371 (a message that names the next action).
- **Source positions.** `sourceRef` is a JSON pointer. A source-range field
  (line and column) is not available today and is not invented; the schema reserves
  an optional `sourceRange` addition for the follow-up that the #148 prior-art
  comment calls for.

### D2.6 Determinism (**Decided**)

A result is a pure function of (workspace file bytes, tool arguments, chrona version,
pinned renderer versions). Specifically: no timestamp, no duration, no process id and
no host path in any result; object and diagnostic order is the use case's order (the
adapter sorts nothing it does not have to); identities are `sha256:` content
identities; locale defaults to `en-US` explicitly, never from the environment;
system fonts are never consulted (SVG measurement uses packaged metrics; PNG
rasterization passes `skip_system_fonts=True`); PNG bytes depend on the pinned
`resvg-py` of the `render` extra and are therefore reported with `contentIdentity`
only for the artifact the caller asked for. The server's name and version appear
only in the MCP `initialize` result. Proofs: the same call twice and from two working
directories yields equal JSON and equal bytes; and for the same inputs the SVG bytes
equal the CLI's output file bytes (the cross-surface equality test).

### D2.7 Mutating commands and the approval contract (**Lead**)

What exists is smaller than the issue supposes, so the design states it plainly.

- Two mutation surfaces are reachable from the CLI today. (a) Guided authoring:
  `workspace revision` returns the workspace's content identity;
  `authoring-command-apply` applies one `chrona/authoring-command/v0.1`
  (`setWorkspaceTask`, `setWorkspaceActual`, `selectPresentationPreset`,
  `setPresentationOverride`, `materializePresentationPreset`) only if its
  `baseRevision` equals the current identity, writing by compare-and-set; a stale base
  is `E_AUTHORING_BASE_REVISION`. (b) Operational: `command-check` (read-only
  verification) and `command-apply`, `actual-intake`, `actual-resolve`,
  `baseline-capture`, which require a Store config, check `baseRevision`, and use an
  idempotent replay ledger.
- Neither has a principal, a policy or a command fingerprint at runtime.
  `ai-command-proposal/v0.1` and `authorization-decision/v0.1` (Spec 10 §9.1) are a
  specified exchange with a conformance fixture and **no implementation**. A compare-and-set
  prevents a stale write; it does not authorize one.

**Recommendation:** the first MCP release has **no mutating tool**. The tools an
agent most needs (validate, schedule, render) are read-only, and the
coding-agent path writes files with its own file tools or the CLI. A mutating
tool added now would either claim an authorization the product does not implement or
silently skip one. When mutation is added (S6), the contract is:

1. `check_command` is read-only and returns the CLI's `automation-result` plus its
   `requestContentIdentity`.
2. `apply_command` requires `confirm`, equal to the `requestContentIdentity` that
   `check_command` returned for the same command, and the server was started with
   `--allow-write`; otherwise `E_MCP_WRITE_DISABLED` or a rejected `confirm`.
   `confirm` binds "exactly this command"; it is named `confirm`, not `authorization`.
3. Tool annotations declare `readOnlyHint: false` and `destructiveHint: true`, so the
   host's own tool-approval prompt is the human gate. The server does not add a
   second, weaker one.
4. The proposal and decision documents are not emulated. When a runtime for them
   exists, `apply_command` gains `proposal` and `decision` inputs and `confirm`
   retires; that is a breaking tool-schema change, announced in the tool description
   and covered by a versioned tool-set (`chrona/agent-tools/v0.x`).

Consequence of the recommendation: an agent cannot append an Actual or capture a
baseline through MCP in the first release, and the issue's `apply_command` row is
deferred, not met. Consequence of the alternative (ship `apply_command` now behind
`--allow-write`): faster feature parity, at the price of a surface whose safety
claim is "the host asked the human" and "the base revision matched", which is true
and weaker than the spec's exchange.

### D2.8 Windows (**Decided**)

- Start with `chrona mcp` or `python -m chrona mcp`; both work without `Scripts` on
  `PATH`. The host config documents both.
- Tool paths are always `/`-separated relative paths; backslash, drive letters and
  colons are refused on every OS (so Windows alternate data streams and `C:` forms
  never reach the filesystem). Results use `/`.
- Reserved device names are refused (D2.4.2); reading `CON.yaml` would otherwise
  address the console device.
- Stdout carries protocol only; the SDK writes UTF-8 on its own binary-safe stream.
  No chrona code prints, so there is no `\r\n` translation to corrupt a frame.
  Images are base64, so PNG bytes are untouched.
- Non-ASCII workspace and file names (Japanese plan titles) are allowed
  (`charset="file-name"`).
- `pywin32` arrives as an SDK transitive on Windows; the three-OS full matrix
  installs the `mcp` extra and runs the SDK lane there, so a missing wheel is caught
  by CI, not by a user.
- The workspace argument may be a Windows path; it is a host argument, not a tool
  input, and is never echoed into a result.

### D2.9 Layer rule (**Lead**)

`tools/check_import_direction.py` allows `app` to import `usecases`, `core`,
`operational`, `presentation`, `scheduling`, `storage` and `resources`. The brief for
this design asks for stricter: the MCP adapter imports use cases only. The design
meets that for the first release (validate, schedule, draft render, presets all become
`usecases/` modules in S0) and enforces it with a per-module rule: S3 adds to the tool
a small table of module-prefix overrides, so `chrona.app.agent_*` and
`chrona.app.mcp_server` may import only `usecases` and the `core` modules that are
contract types (`diagnostics`, `identity`, `store_address`); a violation fails the same
check. The cost of the stricter rule appears in S6: `operational/` imports `usecases/`,
so a `usecases` facade over `check_command` or `compare_baseline` would be a cycle
(`usecases` -> `operational` -> `usecases`). Options at S6: (a) one explicit
override that lets the adapter import `operational.command_engine` and
`operational.baselines`, with its reason recorded in the tool (the tool's own contract:
"adding an edge is a deliberate edit here"); (b) relocate those two modules into
`usecases` (a large behavior-preserving move touching conformance and tests); (c) keep
the tools out. **Recommendation:** (c) for now, and (a) when S6 is approved.

### D2.10 Resources and instructions (**Decided**, small)

The MCP `initialize` result carries `instructions`: a short text (under 1 KB) that
states the model in three sentences, says `rejected` is a result, names
`schedule_project` as the cycle check, and points to the resources. The server
exposes two read-only resources read from the **packaged skill** so that a client with
no skills support still gets the same words: `chrona://guide/authoring` (the body of
`SKILL.md`) and `chrona://guide/diagnostics` (`references/diagnostics.md`). There is
one source of text, and the skill tests (D1.3) therefore also guard the MCP's
guidance. Prompts and subscriptions are not offered.

## 3. Order of slices

**Confirmed with one revision.** The issue's order is #120, skill, MCP. Evidence:

- #120 (and #122, #371, #372, #377, #429) are closed, so the skill can teach the draft
  path instead of snapshot roots; the issue's blocking condition is met.
- The skill needs no new dependency and no code except one tool change
  (`documents()` and the fixture copy), so it is the smallest slice and delivers
  value to every coding agent immediately. The survey the issue cites (`mcp_excalidraw`)
  makes the same ordering: skill plus CLI for coding agents, MCP second.
- **The revision:** the MCP server is not "nearly free" after #120. `validate` and
  `schedule` are not use cases, the draft-render orchestration and the failure ladder
  live in `app/cli.py`, and the operational commands cannot be fronted by a use case
  without a cycle (F1, F2). A behavior-preserving extraction (S0) is the real
  prerequisite, and it is independent of the skill, so it can run in parallel.
- The MCP is split into an SDK-free tool core (S3) and a thin SDK binding (S4), so the
  contract, scoping and determinism are tested without the dependency, and the
  dependency lands only after the contract is proven.

Order: S1 (skill) and S0a/S0b (extraction) in parallel; S2 (delivery) after S1; S3 after
S0; S4 after S3; S5 after S2 and S4; S6, S7 conditional. Detail, files and proof are
in the [implementation plan](../planning/active/issue-142-agent-interface-implementation-plan-2026-10-01.md).

## 4. Out of scope

- A hosted or remote service, any HTTP transport, and therefore authentication,
  authorization, rate limiting and multi-tenant isolation. A local stdio process
  inherits the user's trust boundary; the workspace guard is a safety rail, not a
  sandbox against a hostile agent with its own shell.
- Long-running or stateful behavior: no sessions, no job queue, no cancellation or
  progress, no cache that survives a call, no file watching.
- The terse draft syntax (#148), source ranges in diagnostics, and a `chrona compile`
  tool until it exists.
- Making `validate` detect cycles; implementing `ai-command-proposal` and
  `authorization-decision` at runtime; moving `operational/` into `usecases/`.
- A plugin or marketplace manifest (optional follow-up after S2), skill evaluation
  harnesses, telemetry.
- Resource leveling, interactive editing, and any change to the specification of the
  Project, View, Theme or Layout.

## 5. Compatibility and migration

No existing command, flag, schema, diagnostic code or byte of output changes. New
public surface: `chrona skill copy`, `chrona mcp`, the `mcp` extra, the `E_MCP_*`
codes, and Spec 66 (written in S3). The CLI keeps importing without the SDK. S0 is
proven byte-identical on the CLI before anything is built on it.
