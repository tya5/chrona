"""Generate the 80-task Atlas programme CSV (week 0)."""
import csv, random, sys

random.seed(12)
TEAMS = ["platform", "payments", "mobile", "web", "data", "ops"]
PHASES = [("discover", "Discovery"), ("build", "Build"), ("launch", "Launch readiness")]
RISK = ["low", "medium", "high"]
DELIVS = ["del-api", "del-app", "del-portal", "del-runbook", "del-report"]
# tasks per (phase, team): totals 80
COUNTS = {
    "discover": [3, 3, 2, 3, 3, 2],   # 16
    "build":    [7, 7, 6, 6, 5, 5],   # 36
    "launch":   [5, 5, 5, 5, 4, 4],   # 28
}
rows = []
H = ["id", "title", "type", "start", "end", "duration", "parent", "predecessors", "deadline",
     "progress", "actual_start", "actual_finish", "team", "risk", "external", "deliverable"]
def row(**k):
    rows.append({h: k.get(h, "") for h in H})

row(id="atlas", title="Atlas programme", type="group")
row(id="kickoff", title="Programme kickoff", type="gate", start="2026-11-02", parent="atlas",
    actual_start="2026-11-02")
last_of = {}
n = 0
for pid, ptitle in PHASES:
    row(id=f"ph-{pid}", title=ptitle, type="group", parent="atlas")
    for ti, team in enumerate(TEAMS):
        ws = f"ws-{pid}-{team}"
        row(id=ws, title=f"{team.capitalize()} {ptitle.lower()}", type="group", parent=f"ph-{pid}")
        prev = None
        for k in range(COUNTS[pid][ti]):
            n += 1
            tid = f"{pid[:3]}-{team[:3]}-{k+1}"
            preds = []
            if prev:
                preds.append(prev)
            elif pid == "discover":
                preds.append("kickoff")
            elif pid == "build":
                preds.append("discovery-done")
            else:
                preds.append(f"build-{team[:3]}-done" if False else "build-complete")
            # cross-team dependency every few tasks
            if pid != "discover" and k == 2 and ti > 0:
                other = TEAMS[ti - 1]
                preds.append(f"{pid[:3]}-{other[:3]}-2")
            dur = random.choice([3, 4, 5, 6, 8, 10])
            deadline = ""
            if k == COUNTS[pid][ti] - 1 and ti % 2 == 0:
                deadline = {"discover": "2026-11-20", "build": "2027-03-19", "launch": "2027-05-14"}[pid]
            row(id=tid, title=f"{team.capitalize()} {ptitle.split()[0].lower()} step {k+1}", type="task",
                duration=f"{dur}wd", parent=ws, predecessors=", ".join(preds), deadline=deadline,
                team=team, risk=random.choice(RISK), external=random.choice(["true", "false"]),
                deliverable=random.choice(DELIVS))
            prev = tid
        last_of[(pid, team)] = prev
    gate = {"discover": ("discovery-done", "Discovery complete"), "build": ("build-complete", "Build complete"),
            "launch": ("launch", "Public launch")}[pid]
    preds = ", ".join(last_of[(pid, t)] for t in TEAMS)
    dl = {"discover": "2026-12-18", "build": "2027-03-26", "launch": "2027-05-28"}[pid]
    row(id=gate[0], title=gate[1], type="gate", parent=f"ph-{pid}", predecessors=preds, deadline=dl)
assert n == 80, n
with open(sys.argv[1], "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=H)
    w.writeheader()
    w.writerows(rows)
print(n, "tasks,", len(rows), "rows")
