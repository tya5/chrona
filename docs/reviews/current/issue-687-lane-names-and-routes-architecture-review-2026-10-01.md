# Architecture Review — Lane Member Names Placed Before Routes (#687)

Reviews [the design](../../design/issue-687-lane-names-and-routes-design-2026-10-01.md) against AGENTS.md layer boundaries, Spec 50 §3.2-§3.3, Spec 33 §8.3 and the #592 phase tests, on main `2f0b83ef`. Mechanics: [implementation plan](../../planning/active/issue-687-lane-names-and-routes-implementation-plan-2026-10-01.md). Predecessor: the rejected first variant in the [#573 review addendum](issue-573-label-behaviour-knobs-architecture-review-2026-09-30.md).

Verdict: the issue's premise is partly wrong and its two proposed remedies (reserve the exit, rank `above`/`below`) do not work; the recommended option is a different, narrower one. Written to find problems, not to confirm the recommendation.

## Findings

**F1. The issue's premise does not match the measurements.** The issue describes an end-side name sitting where a route leaves its end port. No measured suppression has an `egress-collision` attempt; every attempt of the four public relations and of the synthetic seeds checked is `quality-rejected` (and four `no-route-found` on slide 16). The blocker is a wall of names across stacked lane rows, between the source's end and the target's start. Removing any one of three names in the seven-span fixture restores the route, including names that are not at either port. A fix that looks only at the ports cannot work (option A, measured).

**F2. The defect is not hypothetical on public slides.** The issue says the conflict showed up in a rejected variant. On current main four relations are already suppressed on four slides, and names are the cause (placing names after routes draws all four). #679's acceptance said no route changed; that is true of #679 and says nothing about routes already lost. The design targets draw every dependency, so these are visible gaps against the target, not only an ordering concern.

**F3. Option B is vacuous in lane mode.** No lane view and no preset declares `above` or `below` for member names (presets declare `end`, `start`, `suppress`), and a lane row is one name tall, so an `above`/`below` candidate has no room. Measured on both fixtures: putting `above`, `below` first leaves the route lost; declaring only them suppresses every name and the route is "saved" only because no name exists. Ranking cannot be the mechanism. Adding rungs to a declared ladder would also contradict "authored side/fallback order remains authoritative" (Spec 50 §3.2).

**F4. Option C (routes first) trades the wrong thing.** It draws all four relations and suppresses 40 names that are shown today (`02` 8, `03` 5, `11` 6, `12` 8, `16` 13), on `03` with no relation lost at all. Spec 50 §3.3 calls lane names required and forbids a route to cross one; the order exists for that reason. Rejected on the stop condition (a name suppressed that is shown today).

**F5. Option A as the issue states it is harmful.** A 12 px keep-clear at every relation port moves names on five slides, leaves `launch-leop` lost on three, draws `shipment-campaign` on `16` but loses `station-comms` there, and suppresses one name on each of three slides and 14 on `16`. It fires for every relation endpoint, not only the ones that are lost, which is why it is broad and wrong.

**F6. The recommended option (E) is conditional, so it needs a guard to be safe, and has one.** E reserves a corridor only for a relation lost today and only if a rehearsal shows the result is no worse (relations lost a strict subset, no new suppressed name). The guard is why E changes three slides and loses nothing; without it (E2) `16` loses three shown names for one route. The guard is deliberately strict: a repair that costs as many names as it saves routes (the seven-span fixture) is refused.

**F7. E leaves a known gap and says so.** `shipment-campaign` on slide 16 stays suppressed, because drawing it would suppress `frr`, `launch` and `leop`. The design target draws it. That is an owner decision (E2), recorded as open, not silently decided. A reference route that already avoids movable names might draw it at lower cost; not attempted.

**F8. Cost is real and concentrated.** The planner adds one route pass when nothing is lost and up to three when something is. On slide 16 the render goes from about 22 s to about 50-58 s because routing dominates (15 s per pass) and the failing searches are the expensive ones. Public regeneration's long pole grows by about 30 s. This is acceptable for one slice and should not be hidden: a route-search memo shared by the rehearsals is the follow-up.

**F9. The phase and ownership rules hold, with one wrinkle.** The composer still invokes member labels, routes, member labels, relation labels in that order on one index object, monotone, nothing removed: the rehearsals use private `copy()` indexes and run through the module functions, not the composer's phase hooks, so `test_surface_phase_wiring` is unaffected. The wrinkle is real: two throwaway indexes exist during planning. They are local values inside one function and never reach another phase, so "the obstacle index is the only shared mutable state" holds; the sentence in Spec 33 §8.3 should say that rehearsals use private copies. The planner is a new module (docstring `Owns ...; reads ...`, a Spec 33 row, reachability), and the composer stays under 400 lines.

**F10. Determinism and platform.** Corridor ids are derived from the relation id and segment number and the index orders by id, so insertion order does not matter. The single new float expression is `stroke + 2 * ROUTE_GRID_OFFSET`. `ROUTE_GRID_OFFSET` equals the router's existing default, so routing is unchanged. No sorting depends on a locale or dict order that differs across platforms.

**F11. Scene acceptance checks (association, host, 2 em) are safe by construction.** A yielding name goes through the same `place_member_name` candidate filter as every name; a moved name is emitted only inside its host's reach, or suppressed with the usual typed fact. The final rung of #679 is unchanged. The risk that remains is behavioural, not structural: a moved name changes `laneMembers` and `laneObstacles` facts and neighbouring placement (annotation boxes on `11` moved), which the corpus diff reviews one primitive at a time.

## What would change this verdict

- A reproduction of a true exit-port conflict (an `egress-collision` suppression caused by a name). E would still help, because the corridor includes the exit, but B and A would then deserve a second measurement.
- A slide where the guard refuses a repair that the owner wants. That is E2, a policy change, not a code defect.
- The cost of the extra passes proving unacceptable in CI; then the memo moves into this slice.

## Residual risks accepted, stated

1. Slide 16 keeps one lost dependency (F7).
2. Planning runs routing two or three more times on lane projects with relations (F8).
3. A moved name is a visible change on `02`, `11`, `12`; each is reviewed against the rule and the target, and none may be kept only to preserve today's look.
