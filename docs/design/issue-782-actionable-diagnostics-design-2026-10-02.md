# Design: Actionable and De-duplicated Diagnostics (#782)

**Status:** Proposed, pending the [architecture review](../reviews/current/issue-782-actionable-diagnostics-architecture-review-2026-10-02.md).
Plan: [design plan](../planning/active/issue-782-actionable-diagnostics-design-plan-2026-10-02.md),
[implementation plan](../planning/active/issue-782-actionable-diagnostics-implementation-plan-2026-10-02.md).
Living contract to update at implementation: [Spec 66](../specification/66-agent-interface.md) section 2 and
[`skills/chrona/references/diagnostics.md`](../../skills/chrona/references/diagnostics.md).

## Rule

A diagnostic row that an agent can see has a **message**: a sentence that says what
is wrong, names the offending value when the producer knows it, lists the valid
values when the set is small, and says what to do when only the code is known. A
finding that repeats with the same code and the same cause is **one row** that carries
a `count` and the first occurrence. No existing key changes; the new keys are
additive. The rule is implemented once, in the use-case layer, so the CLI and the MCP
tools cannot disagree.

## Decisions

Each is an owner-level judgement call, recorded with options and reversal on the issue.

**D1. What "same cause" means for a warning.**
Options: (a) same code; (b) identical rows only; (c) same code **and** same cause
sentence. Chosen (c). A warning's *cause* is the code's sentence with the
per-instance subject removed (for a fit warning the failure kind is part of the
cause: "text overflows" and "route fell back" are different causes even under one
code family). The *subject* is the per-instance part (a placement, an object, a
relation). Rows with equal `(code, severity, cause)` merge. Why: (a) hides a
second remedy behind the first; (b) leaves the seven label rows. Reverse: change
`describe_warning` so a family's cause includes its subject, and nothing collapses.

**D2. Where a warning's message lives.**
Options: (a) in each of the Scene and Layout producers; (b) in the Scene as a new
field; (c) in the use-case layer, from the identity string and family fields.
Chosen (c): `usecases/diagnostic_messages.py`, called by
`usecases/warning_ledger.py`. Why: the identity strings and the Scene `diagnostics`
list are public, byte-stable evidence (Scene fixtures, conformance) and Layout
owns geometry, not prose; (a) and (b) touch about 50 producers and every Scene
fixture. Reverse: move a template next to its producer and delete its entry; the
table keeps working for the rest.

**D3. The long tail of bare codes.**
233 CLI-reachable codes are raised with no detail (the inventory backlog). Options:
(a) fix every producer; (b) leave the rows bare; (c) a guarantee at the one place
every row passes (`diagnostic_record`): an informative message is kept; a bare one
is replaced by a curated sentence if the code has one, else by a derived one that
says no further detail is recorded. Chosen (c), plus curated sentences for the codes
whose producer cannot know the value and that an agent reaches by an ordinary
mistake, plus (a) where the producer knows the value: `E_BUILTIN_PRESET_UNKNOWN`,
`E_BUILTIN_PRESET_OUTPUT_EXISTS` and the "not a mapping" case of a Draft resource
file (`E_PROJECT_SCHEMA` and its siblings). The coverage test is that every row the
characterization golden and the skill's provoking tests produce is informative,
not that each has a curated entry. Why: (a) is
rewriting about 650 sites in Layout, Theme and font code that an agent only meets
as an internal invariant; (b) fails the issue. The derived sentence is honest
about its limit. The remaining producers stay in the derived inventory backlog and
become a successor issue (owner-local detail per code). Reverse: delete the derived
branch; a bare code then raises in tests, which shows the work left.

**D4. Additive keys, and when `count` appears.**
`message` is on every row (warnings gain it). `count` is present **only when it is
2 or more** (absent means one occurrence), on error rows and warning rows alike;
`occurrences` (warnings only) lists the distinct identity strings in order, capped
at 20 (`count` stays exact). `sourceRef` and every family field are those of the
first occurrence. Why: a row that occurred once is byte-identical to today except
for the new `message`, so single-finding consumers and most goldens stay stable.
`I_LAYOUT_PLOT_LABELS_SUPPRESSED` already has its own `count` (a number of labels,
already one row per surface) and is not collapsed. Reverse: always emit `count`.

**D5. `E_BUILTIN_PRESET_UNKNOWN`.**
Raised as a `StableFailure` with message
`unknown builtin preset 'nope'; valid ids: mission-light, control-room-dark, ...
(chrona preset list); a value with '/' or a .yaml suffix is read as a path`. The
set is the seven ids of `library.yaml`, so it is listed in full, in catalogue order,
read from the catalogue at raise time. Code, component (`presentation`), `sourceRef`
(`/`) and exit status (1) are unchanged. Reverse: raise `ValueError(code)` again.

**D6. The 14-row case.** It does not reproduce on `main` (design plan). No special
rule is added for it. The generic exact-duplicate collapse is kept in the shared
layer for error rows, so a regression of that shape would show as one row with a
count rather than fourteen, and the MCP adapter's own duplicate filter is removed
in its favour.

**D7. What stays in the MCP adapter.** The 50-row cap and
`omittedDiagnostics`, host-path scrubbing and the fixed `E_TOOL_FAILURE` text are
transport concerns and stay. De-duplication and messages move to the shared layer;
the adapter collapses again after scrubbing (two rows can become equal once a path
is scrubbed) using the same function, summing counts.

**D8. A Project that is not a mapping.** `chrona validate` and `schedule` on an
empty file or a YAML list reach Core with a non-mapping and fail with
`E_TOOL_FAILURE` and a Python message (`'list' object has no attribute 'get'`,
status `failed`, exit 2), while `render` on the same input is already
`E_PROJECT_SCHEMA`, rejected, exit 1. Options: (a) leave; (b) a clear
`E_SCHEMA` message and rejected/exit 1, as `render`; (c) a clear message and keep
`failed`/exit 2. Chosen (b), in `usecases/project_checks.py`. Why: an unreadable
plan shape is a rejected input, not a tool failure, and the three commands should
agree. This is the one deliberate change of status and exit code in this issue;
it is in the golden diff and the Spec 66 note. Reverse: remove the guard.

**D9. Tool-set version.** Spec 66 section 2 says a change to an output schema
changes the tool-set version. The tool result schema gains optional `count` and
`occurrences`, so `chrona/agent-tools/v0.1` becomes `v0.2` (both properties in one
bump, so slice S2 needs none). Options: keep `v0.1` because the properties are
optional; bump. Chosen: bump, because the rule is stated and a consumer pinning the
set should see the change. Reverse: keep the property additions and restore the
string.

## Contracts

### Error rows

`diagnostic_record(code, message, component, source_ref, ...)` is the one builder.
It returns the six fixed keys unchanged, with `message` passed through
`error_message(code, message)`:

- informative (non-blank, and more than the code and a bare `source=<ref>` suffix)
  -> unchanged;
- else the curated sentence for the code, if one exists;
- else `<code words>: no further detail is recorded for this code (<CODE>)`, built
  from the code, never empty and never equal to the code.

The failure ladder (`report_failure`) changes in three places, all in
`usecases/failure_report.py`:

- a bare `ValueError` text is split into a **code** (the leading `E_[A-Z0-9_]+`
  token) and a message (the whole text, so detail after `:` is kept); today a
  multi-line text becomes the **code** (`command-check-broken-json`);
- an empty `str(error)` in the last-resort branch becomes the exception class name;
- `rejection_report` and the ingress report call `collapse_records`, which merges
  rows equal in every key and adds `count` to the first.

`LayoutError` and `ColorSchemeError` reach the ladder already converted
(`RenderFailed` with a `sourceRef`, and `ClosureError` with one), so the ladder does
not change for them. Two conversions do: `render_review` drops the token or node a
`LayoutError` carries (`E_LAYOUT_TOKEN_REQUIREMENT_UNAVAILABLE` names the token in
`node_id`), so its message now guarantees a sentence and appends `(<node_id>)`; and
`usecases/project_checks.py` rejects a non-mapping Project (D8). The Draft-resource
loader in `presentation/model/closure.py` names what was found (`a project file must
be a YAML mapping; found a list`) in place of the bare `E_PROJECT_SCHEMA`.

### Warning rows

`collect_render_warnings` builds each record with `message` from
`describe_warning`; `warning_payloads` returns the collapsed list. Message form:
`<cause>: <subject>` for one, `<cause>: <subject> and N more (first shown)` for
several. Example (Halcyon): seven `W_LAYOUT_LABEL_SUPPRESSED` rows become

```json
{"code": "W_LAYOUT_LABEL_SUPPRESSED", "count": 7, "diagnostic": "W_LAYOUT_LABEL_SUPPRESSED:member-label:eps:eps",
 "message": "a label was left out because it does not fit: member-label:eps:eps and 6 more",
 "occurrences": ["...", "..."], "severity": "warning"}
```

**Multiplicity invariant.** The CLI used to list one stderr line per Scene warning
and a test (`test_cli_warning_inventory_equals_scene_diagnostics_for_attached_milestones`)
pins `Counter(CLI identities) == Counter(Scene identities)`; that was the guard
against a transport dropping a warning. Collapsing replaces the guard by a
stricter statement that does not depend on row count: for every code, the sum of
`count` (1 when absent) over its rows equals the number of Scene `diagnostics` of
that code, and the first identity and every listed `occurrences` entry is a Scene
identity. The Scene itself keeps every per-placement fact (Spec 50 requires the
`I_LAYOUT_PLOT_LABELS_SUPPRESSED` count to equal the number of per-placement
`W_LAYOUT_LABEL_SUPPRESSED` facts; those facts stay in the Scene unchanged, and the
info row is not collapsed. The warning row's `count` also includes label kinds other
than member labels, as the per-placement rows always did).

`describe_warning` is a table of every `W_` code a render can emit
(`W_LAYOUT_*`, `W_FONT_*`, `W_SCENE_*`, `W_PRESENTATION_SCALE_NOT_SEPARABLE`,
`W_PROJECT_ATTACHED_OUTSIDE_HOST`), read from the identity string or the family
fields. An unknown code falls back to the derived sentence, but a test fails for
an emitted code with no entry, so the fallback is a safety net, not a design.

### Compatibility

Every existing key keeps its name, type and position (CLI error rows keep six
fixed keys in order; stderr lines stay sorted-key JSON). New: `message` on warning
rows, `count` and `occurrences`. Changed values, all intended and listed in the
golden diff: messages that were a bare code (a layout finding now names its
token); the **code** of a `ValueError` whose text had detail; the number of stderr
warning lines; the D8 status and exit code; the tool-set version (D9).
The Scene JSON, the `diagnostics` list of a Scene, the SVG and PNG bytes and the
schedule output are unchanged.

## Failure behavior

The message guarantee cannot raise: an unexpected input to `error_message` yields
the derived sentence. A warning with an unknown shape yields the derived sentence
and an empty `occurrences`. The collapse never reorders: the merged row sits at
the first occurrence's position, so stderr order and MCP order stay deterministic.

## Layer connections

`failure_report`, `warning_ledger` and `draft_render` import
`diagnostic_messages`; it imports nothing from `presentation/` or the adapters
(it reads strings and mappings). `app/cli.py` and `app/agent_tools.py` import only
use cases, as today (`tools/check_import_direction.py`).

## Extension points

A new code needs no table entry to be safe (derived sentence) and one entry to be
good; the test list names the codes that must have one. A new warning family adds
one `describe_warning` case.

## Test design

Synthetic fixtures for the rule (an empty, a code-equal and a `source=` message for
every code the inventory derives, through the record builder and through the ladder; collapse of equal, near-equal and interleaved
rows; cap and counts); a per-code test that every `W_` literal the source emits has
a curated entry; the Halcyon fixture end to end for the real warning set; CLI and
MCP equality of rows and counts; the characterization golden diff, reviewed row by
row. Each new test is mutation-checked (the guard removed, the collapse key
weakened) and the result is recorded in the implementation plan.
