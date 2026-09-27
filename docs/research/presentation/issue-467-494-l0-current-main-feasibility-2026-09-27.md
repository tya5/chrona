# L0 Current-Main Feasibility Gate (#467, #494)

**Status:** read-only gate result on published `main` `68f487a6beaa1c47da430e5b39dd571f7423595f`. This is scheduler and existing-geometry evidence only; it does not establish lane or route acceptance. **Plan:** [recompletion design plan](../../planning/active/issue-467-494-lane-feasibility-recompletion-design-plan-2026-09-27.md) and [implementation amendment](../../planning/active/issue-467-494-lane-feasibility-implementation-amendment-2026-09-27.md). **Design:** [feasibility/route correction](../../design/issue-467-494-lane-feasibility-route-correction-2026-09-27.md).

## Baseline and reproducibility

Worktree: `/tmp/chrona-467-l0-20260927`, detached at the published SHA above. The project environment was created there with `python3 -m venv .venv` and the checkout installed using `.venv/bin/pip install -e .`. No tracked product file, Project, Actual, snapshot, Scene, or SVG was changed. The Project candidates below were deep copies held in memory.

The issue bodies/comments were checked on 2026-09-27: [#467](https://github.com/tya5/chrona/issues/467) has six acceptance rows, including the ≤12-lane named chain; [#494](https://github.com/tya5/chrona/issues/494) has three rows requiring per-relation suppression causes and no route crossing required labels. Latest handoff comments confirm the unmerged WIP is not acceptance evidence.

Scheduler command (from the worktree root; ordinary `chrona.scheduling.scheduler.schedule` path):

```sh
.venv/bin/python - <<'PY'
from copy import deepcopy
from pathlib import Path
import yaml
from chrona.scheduling.scheduler import schedule

project = yaml.safe_load(Path("examples/halcyon-1/project.yaml").read_text())
for lag in ("2wd", "3wd", "4wd"):
    candidate = deepcopy(project)
    next(r for r in candidate["relations"] if r["id"] == "avionics-bustest")["lag"] = lag
    result = schedule(candidate)
    print(lag, result.placements["avionics"], result.placements["bus-test"],
          result.analysis.total_float["bus-test"] if result.analysis else None)
PY
```

Output, with no scheduler diagnostics:

| `avionics-bustest` lag | Avionics planned | Bus-test planned | Bus-test total float |
|---|---|---|---:|
| 2wd (published) | Apr 6–Apr 27 | Apr 29–May 13 | 41 days |
| 3wd (candidate) | Apr 6–Apr 27 | Apr 30–May 14 | 40 days |
| 4wd (candidate) | Apr 6–Apr 27 | May 3–May 17 | 39 days |

Dates are in 2027. Comparing 2wd and 4wd results across all scheduled objects showed only `bus-test` placement changed; only its reported total float changed. The frozen `snapshots/baseline-2027-06/project.yaml` still declares 2wd. The Actual resource records avionics finish as 2027-04-30. Therefore 3wd starts bus-test on that same date; 4wd starts it May 3. These are scheduler facts, not proof that any lane fits.

Existing published `02-programme-board.scene.json` has 26 rows, one per selected object. On its current time scale (3.476981818 px/day), avionics actual ends at x=1132.448909 and bus-test planned starts at x=1128.971927: the mark intervals overlap by one day (3.476982 px). The Scene's task names and deltas remain table cells, not lane labels. This confirms the present geometry/overlap constraint only; it is not a candidate lane layout.

Scene extraction command:

```sh
.venv/bin/python - <<'PY'
import json
from pathlib import Path
s = json.loads(Path("examples/halcyon-1/generated/02-programme-board.scene.json").read_text())["surfaces"][0]
print("rows", len(s["rows"]))
for p in s["primitives"]:
    if p.get("id") in {"actual:avionics:avionics", "planned:bus-test:bus-test"}:
        print(p["id"], p["bounds"])
PY
```

## Lane and route gate result

The requested 4wd-plus-third-label-row lane result cannot be faithfully simulated against this published code baseline:

- `schemas/view-v0.26.schema.yaml` admits only `rows.mode: automatic|explicit`; `src/chrona/presentation/model/projection.py` composes non-explicit rows as one row per item. There is no lane allocator in `src/chrona/presentation/layout/` and no current-main lane-mode composer path.
- Specification 38 §3.1 and the approved correction describe intended lane behavior, including a bounded third stagger row and required-name obstacles, but those published design statements do not provide executable lane geometry on this SHA.
- The checked-in Scene has no candidate lane membership, third-row label placement, lane row extent, or corresponding route/obstacle state. Consequently a lane count, chain-on-one-lane result, candidate label/delta fit, required-label crossing result, or lane-route failure cause cannot be measured here. Reporting zero failures or transferring the unmerged WIP/monkeypatch outcomes would be unsupported.

## Gate disposition

**Scheduler subcheck:** reproduced. **Lane/route L0 acceptance:** not measurable on this baseline; the gate is not passed. The implementation amendment currently places the lane/route measurements before L1–L3, while the approved allocator and route instrumentation are first introduced in L3. This is circular for final lane-membership, label, and cause-specific route evidence. Amend the design/implementation plan before product changes: keep the reproducible date-only scheduler check here, and move ≤12 lanes, the chain, label/row geometry, no-crossing, and per-relation route-cause acceptance measurements to L3, where the implementation can emit those observations. L3 must still stop and return to design if the measured criteria fail. Do not infer acceptance from the old L0 estimate or unmerged WIP.
