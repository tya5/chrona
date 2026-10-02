# Architecture Review — Terse draft syntax (#148)

**Reviews:** [design](../../design/issue-148-terse-draft-syntax-design-2026-10-01.md) (plan:
[design plan](../planning/issue-148-terse-draft-syntax-design-plan-2026-10-01.md); slices:
[implementation plan](../planning/issue-148-terse-draft-syntax-implementation-plan-2026-10-01.md)).
**Base:** `main` at `1185e229` (2026-10-01).
**Reviewer note:** the same author wrote the design and this review. The review therefore attacks the design
from the repository's own constraints (checkers, existing code, adjacent specifications) rather than from
taste, and it records what changed because of the findings. An independent read by the lead is requested
before slice 1 starts, in particular of findings F6 and F7 and the open points in section 4.
This is a design review, not an issue acceptance review: it carries no literal acceptance table.

## 1. Verdict

**Accepted for implementation planning, with conditions C1-C8 (section 5), and with the case for the work
stated as moderate, not overwhelming.** The architecture is sound: a pure ingress compiler behind the adapter,
Core keeping every semantic rule, one-way, no schema change, no new dependency. Two parts of the original
framing did not survive review and were cut or gated: the "terse form helps beginners" argument (F6) and any
composition mechanism beyond hand-off (F7). Slices 2-4 are gated by a go/no-go check after slice 1.

## 2. What was checked

| Area | Evidence examined | Result |
| --- | --- | --- |
| Project contract | `schemas/project-v0.7.schema.yaml`, Spec 05, `core/validation.py`, `core/temporal.py`, `scheduling/scheduler.py` | Mapping is total over the authorable subset; mode names differ from the issue sketch (`fixed-point`, `scheduled`) and the design uses the real ones |
| Identity | `core/store_address.py`, `common-v0.1` `slug`/`identifier`, Spec 02, `core/relation_identity.py` | `slug` is a subset of every id alphabet in use; object keys have no schema pattern at all (finding F3) |
| Diagnostics | `core/diagnostics.py`, `app/cli.py` `_diagnostic`/`_reject`, #371 design | No position model exists (F2); bare codes are discouraged, so every terse code has a message |
| Layering | `tools/check_import_direction.py`, `tools/check_module_reachability.py`, `tools/staged_modules.txt` | One new row and one new edge; two gates dictate slice 1 (F1) |
| Draft path | `_run_draft_render`, `resolve_draft_render`, `_resolve_preset_argument` | A temp-file hand-off has an in-repo precedent (F10) |
| Docs gates | `tools/check_documented_commands.py` | Needs a change to treat ```` ```chrona ```` fences correctly (F4) |
| Neighbours | Spec 51 and `presentation/model/authoring.py`; #142 text | Second compact source exists (F5); contract for #142 defined |
| Evidence | Throwaway spike (not committed): lexer, parser and mapper of the grammar, run against HALCYON-1 | 29 placements, 24 edges, critical set all equal; validates clean |

Not verified (and said so in the design): agent success rates; Windows temp-directory behaviour of the draft
hand-off; the exact nearest-name suggestion quality.

## 3. Findings

Severity: **B** blocks the design as first drafted (resolved by an edit already in the design), **M** accepted
with mitigation, **m** minor, **O** open for the lead.

### F1 (B, resolved) Two repository gates dictate what slice 1 must contain

`tools/check_module_reachability.py` fails a module no product entry point reaches (the allowance,
`tools/staged_modules.txt`, is currently empty and is for in-flight work). A parser-only first slice would be
unreachable, and `tools/check_documented_commands.py` requires every CLI command and option to be documented
in README or `docs/guides/`. So "parser first, CLI later" is not publishable as written.
*Resolution:* slice 1 includes the minimal `chrona compile` command and a stub guide section; no staged-module
entry is used. The implementation plan orders slices accordingly, which differs from the order in the
assignment text (parser, calendars, CLI and draft, docs) only by moving `compile` forward.

### F2 (B, resolved) Core cannot carry a source position, and its pointers are inconsistent

`Diagnostic` is `(id, message, path)`; the CLI's `sourceRef` is a JSON pointer. A terse author needs
`line:column`. Worse, the pointers are not uniform: `validate_project` reports `/relations/<index>` while the
scheduler's `E_FIXED_TARGET_VIOLATION` reports `/relations/<relation id>`. A one-key source map would silently
lose the scheduler's most likely error for terse users (gates carry dates, so a gate before its predecessor is
the commonest scheduling mistake).
*Resolution:* design 7.1 (subclass the Diagnostic base, additive JSON fields) and 7.6 (the source map is
keyed by both index and id, falls back to the nearest ancestor pointer, and is applied through the single
rejection path). Test: a scheduler error for each of fixed-target, cycle, contradictory-bounds is positioned.

### F3 (B, resolved) A terse name can silently become a non-string YAML key

Verified with the repository's own `safe_load`: a mapping key `on`, `no`, `yes`, `off`, `true`, `false` or
`null` loads as a boolean or `None`. Object ids are mapping keys, so an object named `no` would corrupt the
Project without any error, and `yaml.safe_dump` is not guaranteed to quote such keys the same way across
versions. This is also the reason an emitter that depends on PyYAML would break byte stability.
*Resolution:* design section 8: hand-written emitter with a quoting rule and a round-trip contract
(`safe_load(emitted) == project`) enforced on all fixtures and fuzz cases; golden fixtures include
`on`/`no`/`null` names.

### F4 (B, resolved) The doc-check would read a terse line as a CLI command

The command scanner treats any line in any fenced block whose first token is `chrona` as an invocation. A terse
object named `chrona` ("chrona "Chrona" task ...") would fail the docs gate. Fences also need to be
*executed* as terse, not merely skipped.
*Resolution:* design 9.4 and 13.10: fences with info string `chrona` are removed from command scanning and
compiled; markers `skip`, `expect-error`, `expect-yaml`. The change to the tool is part of slice 4 with its
own tests under `tests/unit/tools`.

### F5 (M) A second compact source now exists next to Spec 51

The guided `authoring-workspace` (Spec 51) is a compact YAML source normalised to a Project and claims to be
"the sole reader of guided syntax". A terse text syntax is a second compact front-end. They differ in
substance (workspace: YAML, fixed-date tasks, Actuals, presentation binding; terse: text, dependencies,
calendars, groups, Project only), and neither calls the other. The risk is user and agent confusion about which
to use, and a drift toward making the terse plan "also bind a preset".
*Mitigation:* design 11: distinct owners, one-sentence guidance in the guide, a cross-reference in Spec 51 at
slice 1, and an explicit non-goal (no presentation words). The lead should be aware that the repository will
have two answers to "how do I write a small plan quickly"; if the guided workspace is going to be retired the
terse plan should be told to its users as the successor path, and that is a product decision outside this design.

### F6 (O) The benefit is narrower than the issue implies; decide with open eyes

Measured (design 2.1): the beginner argument is gone (seven YAML lines versus four terse after #376/#377). The
remaining benefit is generated-output density (about 4x fewer bytes on a dependency-heavy plan, one clause per
dependency) and Markdown embedding, plus positioned errors. Against it, `fields` appears on nearly every object
of five of the six example Projects, so realistic plans leave the syntax at the point they need View grouping
(101 of 153 HALCYON object properties are expressible). There is a legitimate alternative of not building this:
ship the #142 skill with YAML templates and a validator, and accept longer agent output. The review does
not find that alternative clearly better, because positioned all-errors-in-one-pass diagnostics and a
fence-embeddable plan are things YAML cannot offer, but it finds the margin modest. Hence D11: a go/no-go after
slice 1 using the agent check (design 13.11). If agents produce compiling plans in at most one retry from a
one-page card, continue; if not, stop at `compile` and fold the diagnostics work into the YAML path.

### F7 (M) Composition is the weakest part of the issue's own sketch

"The two compose" is cheap to say and expensive to do. A merge of terse and YAML creates two co-owners of one
object, doubles the diagnostic source maps, needs YAML source marks for error positions, and needs a flag on
`render`. The design therefore ships only a one-way hand-off with two guards (no overwrite; a header comment),
specifies the overlay precisely (add-only, one owner per property, never overwrite) so the decision can be taken
quickly later, and recommends not building it. The cost accepted: a plan that keeps changing and also needs
`fields` cannot stay in terse form. The ledger test (5.3) keeps the grammar from quietly growing to cover that
gap one property at a time.

### F8 (M) Core rules must not be duplicated in the compiler

A compiler that wants good errors is tempted to re-implement `start < end`, calendar existence for working-day
amounts and rollup emptiness. Duplicated rules drift and create a second authority in practice. *Resolution:* the compiler
checks only what it needs to *resolve its own constructs* (names, defaults, forms) and returns Core's code for
the rest (design 7.3), positioned through the source map. The property test (13.5d) asserts that anything the
compiler accepts passes `validate_project`, which makes `E_TERSE_COMPILER_DEFECT` unreachable and proves the
compiler is never more permissive than Core.

### F9 (m) The stream rule deviates from the CLI convention on purpose

Every other command prints rejections to stdout. `compile > project.yaml` would put the rejection JSON inside
`project.yaml` if it followed the convention. The rule (diagnostics to the stream that does not carry the
artefact) is one sentence and is documented, but it is an exception agents must learn; the skill for #142 should
state it. Lead may overrule (D8); the alternative is to require `-o` and keep stdout for diagnostics always.

### F10 (M) Draft render via a temporary Project file

Rejected alternative: teaching `resolve_draft_render` (presentation) an in-memory source, which would either
import terse into presentation (forbidden by the table) or add a new source type for one caller. The temp-file
hand-off copies `_resolve_preset_argument`. Residual risks: a message that embeds the project path would show a
temp directory (slice 3 adds a test that no output contains the temp prefix); the draft closure identity is the
hash of the compile bytes, which is exactly what makes "render of terse equals render of its compile output" a
testable equality; `finally` cleanup must cover `PresentationIngressRejected` and `SystemExit` paths (they are
raised inside the `try` in `_run_draft_render` today).

### F11 (m) Column units

Columns are Unicode code points; editors that use UTF-16 will differ on astral characters in titles. Tabs are
rejected so tab width is not an issue. Accepted: no language-server surface is planned.

### F12 (M) The implicit default calendar (N1) is the one place "one construct, one mapping" bends

Taking the sketch literally (`calendar engineering ...` then `20wd` with no clause) requires deriving
`project.calendar` from the single declared calendar. It is deterministic and documented, and it never changes
meaning silently (a second calendar removes the default and the next working-day amount reports
`E_CALENDAR_REQUIRED` with a hint). Alternative: a mandatory `project ... calendar X`. The review accepts the
implicit rule because it is the shape the issue's author wrote; it should be revisited if agents trip on it in
the slice-1 check.

### F13 (m) Closed kinds

Only `task`, `gate`, `group` (the types the corpus uses). Spec 05 examples also show `milestone` and `phase`;
they are free labels in the schema. Closed is safer against typos (a misspelled kind is a silent new type) and
widening is a one-line change. A group takes no `after` in v0.1 because making a derived rollup the *target*
of a dependency is unspecified in Spec 04/05 wording; it can be a predecessor.

### F14 (m) Derived documents and diagnostic inventory

`docs/diagnostics/inventory.md` is derived and regenerated by the main sync; code PRs must not edit it, so the
new codes appear there only after slice 1 reaches `main`. Because #371 requires every CLI-reachable bare construction to
be classified, the terse codes are built with messages from the start, so no backlog disposition is created.
`docs/guides/cli-reference.md` is generated by `tools/check_documented_commands.py` and is committed with
slice 1; it is not on the forbidden list.

### F15 (m) Windows and encoding

`tools/check_text_encoding.py` requires an explicit `encoding=` on text I/O in `src`, `tools` and
`conformance`; the CLI must read bytes and decode itself to report `E_TERSE_ENCODING` with a position, and write
bytes (LF) for `-o`. `*.chrona` and the golden YAML need `text eol=lf` in `.gitattributes`, as the repository
already does for identity-bound YAML.

### F16 (m) Specification number

Spec 65 is the next free number. #142's parallel design may also claim one. The slice-1 PR checks open PRs
and the specification directory before choosing; the number is not part of any contract.

## 4. Open points for the lead

1. **D1/D2 scope and composition.** Recommendation: schedule-and-structure only, hand-off only. This is the
   decision with the most product consequence (F6, F7).
2. **D3 extension.** `.chrona` recommended; shares a visual stem with the `.chrona/` directory.
3. **D4 draft dispatch.** Suffix dispatch for `render`, `validate`, `schedule` recommended; compile-only is a
   legitimate smaller choice.
4. **D5 dependency.** None recommended; `lark` is the named alternative.
5. **Spec 51 relationship** (F5): whether the guided workspace and the terse plan are intended to coexist.

## 5. Conditions carried into the implementation plan

- **C1** Slice 1 contains `compile`, the minimal guide text and the import-direction edit; no staged module.
- **C2** Diagnostics carry `sourceRange`/`hint`/`source`, no bare codes, and the source map is
  keyed by index and id (F2).
- **C3** The emitter is hand-written and round-trip tested, with `on`/`no`/`null` fixtures (F3).
- **C4** The compiler duplicates no Core rule; the fuzz property "compiler-accepted implies Core-valid" runs in
  the PR path (F8).
- **C5** The doc-check treats ```` ```chrona ```` fences as terse and compiles them; a fixture object named
  `chrona` is in its tests (F4).
- **C6** A ledger test classifies every authorable Project property as mapped or yaml-only (design 5.3).
- **C7** Slice 3 proves render-of-terse equals render-of-compile-output and that no output exposes the temp
  path (F10).
- **C8** A go/no-go check follows slice 1 (F6); slices 2-4 are not started on momentum; the overlay and
  inline-field options are built only on the lead's explicit decision.

## 6. Rejected alternatives (with the reason)

| Alternative | Reason rejected |
| --- | --- |
| Do not build; ship the #142 skill with YAML templates | Legitimate; not chosen because positioned all-errors diagnostics and a fence-embeddable plan are not available in YAML; kept alive through the D11 checkpoint |
| A compact YAML dialect (Spec 05 section 7 reserves `from: fw.end`) | Needs a schema change, still carries YAML noise, and gives no positions or one-pass repair |
| Parser library (`lark`) | New runtime dependency and generic error positions for a 25-production grammar |
| Title-derived ids | The derivation becomes a frozen contract; rewording a title renames an object |
| Teach presentation or storage the syntax | Violates the import table and "a Context references YAML always" |
| YAML-to-terse, regeneration, source hash in output | A second authority; the issue's own non-goal |
| Merge/overlay in v0.1 | Two owners per object, two source maps, YAML marks (F7) |
| A scenario or fields syntax | Free maps and cross-section references fail the scope rule (design 2.3) |
| Document-order reference resolution (markwhen) | Discards capability Chrona already has (issue comment 3) |
| Emit through `yaml.safe_dump` | Byte instability across PyYAML versions and the key hazard (F3) |

## 7. Whole-architecture check

| Boundary | Statement | Result |
| --- | --- | --- |
| Project is semantic truth | The compiler emits a Project and Core validates it; terse text is never read after the adapter | Preserved |
| Layers | `terse` imports only `core`; `usecases` may import it; `app` only through the use case; presentation, scheduling, storage, operational, release cannot | Preserved, machine-checked |
| Scheduler | Compiler never computes dates, cycles or float | Preserved |
| Presentation | No presentation words; draft path unchanged | Preserved |
| Immutable closures | Contexts, snapshots, baselines, Stores never see terse text | Preserved |
| Schema ownership | No schema change; ledger forces a decision on schema growth | Preserved |
| Diagnostics | Additive fields, stable codes, messages everywhere | Preserved with an extension of the CLI shape |
| Determinism | Pure function, own emitter, LF bytes, no source hash | Preserved |
| Spec 51 | Distinct owners; cross-reference | Preserved with residual confusion risk (F5) |
| #142 | Contract defined (design 11); nothing of the skill or MCP is designed here | Compatible |
