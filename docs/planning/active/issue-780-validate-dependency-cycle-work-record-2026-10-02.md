# Work Record: `validate` and dependency cycles (#780)

One living record for the baseline, design plan, design, architecture review and implementation plan of
[issue #780](https://github.com/tya5/chrona/issues/780) (found by the #142 design review). Base: `main` at `32a5fb4b`
(observed 2026-10-02). Owner-level decisions are also recorded on the issue.

## 1. Baseline

Published and reproduced on `main` with the starter project plus two relations that close a loop
(`design.end -> build.start`, `build.end -> design.start`):

| Command | Result |
| --- | --- |
| `chrona validate cycle.yaml` | `[]`, exit 0 |
| `chrona schedule cycle.yaml` | `rejected`, `E_FIXED_TARGET_VIOLATION` at `/relations/r2` ("Fixed target violates dependency lower bound") |
| non-fixed loop (two `scheduled` tasks) | `validate` `[]`; `schedule` `E_UNSUPPORTED_CYCLE` reported once per **pending object**, which includes objects that only sit downstream of the loop, at `/objects/<id>`, with a message that names no object and no relation |

Read in code: `usecases/project_checks.validate_project_*` is `core.validation.validate_project` only; `schedule_project_*`
calls `scheduling.scheduler.schedule`, which re-runs the same Core validation and then places objects by waiting for the
placement of every relation source (fixed objects are placed first and never wait; a rollup waits for its children). When a
pass places nothing, every still-pending object gets `E_UNSUPPORTED_CYCLE`, or `E_UNSATISFIABLE_DEPENDENCIES` when the
calendar-day-only relations contain a positive cycle (Spec 04 section 16; conformance `cycle("0d")` and `cycle("1d")`).
Spec 04 section 16 says a graph cycle "is not by itself defined as an error" (a zero or negative-lag cycle can be
satisfiable) and that an implementation limited to an acyclic subset MUST diagnose an unsupported cyclic system as a
capability limitation. `E_UNSUPPORTED_CYCLE` is that diagnostic; it is listed in the supplemental diagnostics table, in
the terse hints (`usecases/terse_compile.py`) and in the skill's diagnostics table.

Consumers that state the blind spot today and must change with the fix: the skill (`SKILL.md` rule 4 and tool table,
`references/diagnostics.md`), the MCP `validate_project` and `schedule_project` descriptions and the server `instructions`
(`app/agent_tools.py`, `app/mcp_server.py`), Spec 66 section 2 and section 6, the guide `docs/guides/agent-interface.md`,
and tests `test_validate_does_not_schedule_so_a_cycle_validates`, `test_validate_mirrors_the_cli_including_its_cycle_blind_spot`,
`test_validate_prints_an_empty_list_for_the_cycle_the_skill_says_it_misses` and two description assertions.

Unverified: golden CLI output for a cycle (to be read from the characterization run, not assumed).

## 2. Literal acceptance

- [ ] A cycle is reported with a code that names it, by the command the spec says reports it, with a test for a fixed-span
      cycle and a non-fixed cycle (duration or point modes).

## 3. Design plan

Use cases: (U1) an author or agent runs `validate`, gets a clean answer, and `schedule` never then fails on a cycle;
(U2) a cycle is named by the objects on it and the relation that closes it; (U3) the MCP tool and the CLI agree because
both call one use case; (U4) a consumer of the skill no longer has to run `schedule` to find a cycle.

Open decisions (resolved in section 4): which of the issue's two options; which code; what counts as a cycle (object-level
wait, endpoint-level loop, fixed objects); which layer; what `schedule` does.

Review questions: does `validate` reject anything `schedule` accepts; does it accept anything `schedule` rejects as a cycle;
does Core keep its "a cycle is not an error" stance; are scheduler internals untouched.

## 4. Design

**D1. Option 1: `validate` detects the cycle.** The issue's second option (document that `validate` is structural) is
rejected: agents trust `validate` and the skill, the guide and the MCP text all spend words apologising for it. Reversal:
restore the old texts and drop the use-case call (one function).

**D2. Keep the existing codes; add no `E_DEPENDENCY_CYCLE`.** `E_UNSUPPORTED_CYCLE` and `E_UNSATISFIABLE_DEPENDENCIES`
already name the condition, are specified (supplemental diagnostics, Spec 04 section 16), are pinned by conformance and by
the terse hints and the skill, and mean the capability limitation Spec 04 requires. A new Core code would say "a cycle is
invalid", which Spec 04 explicitly declines to say. The issue's "such as `E_DEPENDENCY_CYCLE`" is an example. What was
missing is the pointer and the message, not the code. Reversal: rename in one module and the tables.

**D3. Layer.** A pure function `find_dependency_cycles(project)` in `scheduling/dependency_cycles.py` (package `scheduling`
may import `core`). The use case `usecases.project_checks` owns the policy: `validate_project_mapping` runs Core validation
and, only when Core reports nothing, the cycle check; `schedule_project_mapping` runs the same `validate_project_mapping`
first and returns its diagnostics, then schedules. CLI and MCP reach both through the existing use-case functions, so
neither needs a patch. `core.validation` is untouched (Core keeps "a cycle is not an error"). `scheduling/scheduler.py` is
not edited (another change is in flight there); the new module reuses the scheduler's positive-cycle proof by import.
`render` keeps calling the scheduler and so reports the scheduler's own diagnostic for a cycle (same code, scheduler
wording); making `render` name the cycle too is a separate, optional step recorded as a successor if wanted.

**D4. What is a cycle.** Two checks, both over a Project that Core validation accepted:

1. *Wait cycle (exactly the scheduler's stall).* Graph over objects where a non-fixed object points at the source object of
   each relation that targets it, and a rollup points at its children. A strongly connected set with more than one object, or
   an object that waits on itself, is a cycle. Fixed objects never wait, so they cannot be on it. This is the set of objects
   the scheduler cannot place, without the downstream objects the scheduler also lists.
2. *Endpoint loop through a fixed object.* Graph over `(object, endpoint)` with one edge per relation and, for every span
   (`scheduled`, `fixed-span`, `rollup`), an edge from `start` to `end`. A relation with a negative lag breaks the loop for
   this check (Spec 04 section 16: a negative-lag cycle can be satisfiable, so the date check decides). A loop is reported
   only if it touches a fixed object and is not already reported by check 1. This is the issue's starter-project case: the
   fixed-span loop that `schedule` today rejects only as `E_FIXED_TARGET_VIOLATION`.

A loop of non-negative relations through fixed objects is satisfiable only if every date on it is equal, so the check
rejects nothing a real plan needs. Recorded consequence: two fixed gates on one date that depend on each other with `0d`
used to schedule and now are `E_UNSUPPORTED_CYCLE` in `validate` and `schedule`. A loop with a negative-lag relation and
only fixed objects is still decided by the date check, as today.

**D5. Diagnostic shape.** One diagnostic per cycle (not per pending object). `id`: `E_UNSATISFIABLE_DEPENDENCIES` when the
relations on the cycle contain a positive calendar-day cycle (the scheduler's rule, applied to those relations), otherwise
`E_UNSUPPORTED_CYCLE`. `path`: `/relations/<index>` of the relation that closes the cycle, the one declared last among the
relations inside it (the index form `core.validation` uses). `message`: `Dependency cycle among a, b, c (objects in Project
order); the relation at this path closes it. Remove or redirect one relation.` Object ids are Project text, so no host path
appears. Cycles are ordered by their first object in Project order, and the search is deterministic (no set iteration).

**D6. `schedule` through the use case.** Because `schedule_project_mapping` calls `validate_project_mapping`, a cycle is
reported by both with identical diagnostics (U1, U3). The scheduler's own stall diagnostic stays as the backstop for any
caller that reaches it directly.

**D7. Consumers.** Skill rule 4 and the tool table, the diagnostics reference (`E_UNSUPPORTED_CYCLE` is now emitted by
`validate` too), the MCP `validate_project`/`schedule_project` descriptions and server instructions, Spec 66 sections 2 and
6, the guide, and the Spec 04 section 16 paragraph (the reference profile reports the capability diagnostic from `validate`
as well as `schedule`) all change in the implementation PR. `schedule_project` is still the way to learn dates, so the text
keeps "run `schedule_project` to read dates" but no longer calls it the cycle check.

**Whole-architecture review.** Core: unchanged and still project-independent. Scheduling: one new pure module, no scheduler
edit. Use cases: policy lives where both adapters already meet. App and MCP: description text only. Presentation, View,
Theme, Layout, Scene: not involved. Terse: `compile` validates through Core only and says a cycle is the scheduler's code;
`validate`/`schedule` on a terse file now report it positioned through the source map by the existing mapping (the code is
already mapped), checked by a test. No schema change, no version bump. The intended incompatibility is D4's gate case and
the new `sourceRef`/message of an existing code; both are stated in the PR.

**Alternatives rejected.** Cycle detection inside `core.validation`: makes Core call a cycle invalid. Run the scheduler
inside `validate`: pays a full schedule, and returns date diagnostics from a command whose contract is no dates. One
endpoint-level check only: misses the scheduler's own wait cycles that are acyclic at endpoint level (`A.start -> B.start`,
`B.end -> A.end` on two scheduled tasks), so `validate` would stay clean for a plan `schedule` rejects.

## 5. Implementation plan

Publication units: this record (docs PR), then one code PR, then the acceptance review.

| Step | Files | Evidence |
| --- | --- | --- |
| T1 reproduce, failing first | `tests/unit/chrona/usecases/test_project_checks.py`, a new `tests/unit/chrona/scheduling/test_dependency_cycles.py`, the skill diagnostics test | fixed-span cycle (the issue's starter case), duration-mode cycle, point-mode cycle, acyclic endpoint-level wait cycle, nested SS/FF fixed (accepted), negative-lag fixed loop (not reported), self relation, downstream-not-listed, ordering and determinism; each fails on `main` |
| T2 module + use case | `src/chrona/scheduling/dependency_cycles.py`, `src/chrona/usecases/project_checks.py` | T1 green; `tools/check_import_direction.py`, `tools/check_module_reachability.py` |
| T3 adapters agree | `tests/unit/chrona/app/test_agent_tools.py`, `tests/mcp/*`, CLI test | `validate_project` and `chrona validate` return the same diagnostics for the same file; terse file positioned |
| T4 text | skill, diagnostics reference, MCP descriptions and instructions, Spec 04 and 66, guide, supplemental table note | text tests updated, doc-check |
| T5 goldens | `tests/fixtures/cli_characterization/golden.json` only if a cycle case changes | diff reviewed and stated in the PR |
| T6 mutation check | three mutants (drop check 2, drop the use-case call in `schedule`, flip the negative-lag rule) each fail a named test | recorded in the PR |

Conformance (`conformance/run_conformance.py`) and the examples must stay green: no example may contain a reported cycle.

Not changed: the scheduler, `W_DEADLINE` (#810), `totalFloat` order (#789), Core validation, schemas.
