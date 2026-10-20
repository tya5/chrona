import csv, sys
out = sys.argv[1]
baseline = len(sys.argv) > 2 and sys.argv[2] == "baseline"
owners = ["Aiko", "Ben", "Chen", "Dana", "Eli"]
groups = [("discovery", "Discovery"), ("design", "Design"), ("build", "Build"), ("verify", "Verify"), ("launch-prep", "Launch prep")]
names = {
    "discovery": ["Stakeholder interviews", "Market scan", "Requirements draft", "Data audit", "Risk register", "Budget estimate", "Vendor shortlist", "Scope sign-off pack"],
    "design": ["Information architecture", "Service blueprint", "API contract", "Data model", "UI wireframes", "Visual design", "Security design", "Design hand-off"],
    "build": ["Auth service", "Billing service", "Catalogue service", "Search index", "Web front end", "Mobile app", "Admin console", "Integration glue"],
    "verify": ["Unit test hardening", "Integration tests", "Performance tests", "Accessibility audit", "Security pen test", "User acceptance", "Defect burn-down", "Release candidate"],
    "launch-prep": ["Training material", "Support runbooks", "Marketing site", "Data migration", "Pilot rollout", "Comms plan", "Go-live rehearsal", "Hypercare plan"],
}
durs = [6, 5, 8, 4, 7, 5, 6, 4]
H = ["id", "title", "type", "start", "duration", "parent", "predecessors", "deadline", "owner"]
rows = [dict(id="kickoff", title="Kickoff (milestone)", type="gate", start="2027-03-01")]
prev = "kickoff"
gate_after = {"discovery": ("scope-gate", "Scope gate"), "design": ("design-gate", "Design review gate"),
              "build": ("code-complete", "Code complete (milestone)"), "verify": ("go-no-go", "Go/no-go gate"),
              "launch-prep": ("launch", "Launch (milestone)")}
k = 0
for gi, (gid, gt) in enumerate(groups):
    rows.append(dict(id=gid, title=gt, type="group"))
    ids = []
    for i, n in enumerate(names[gid]):
        tid = f"{gid[:4]}-{i+1}"
        d = durs[(i + gi) % 8]
        if baseline:
            d = max(2, d - (1 if (i + gi) % 3 == 0 else 0))
        pred = prev if i < 2 else ids[i - 2]
        rows.append(dict(id=tid, title=n, type="task", duration=f"{d}wd", parent=gid, predecessors=pred, owner=owners[k % 5]))
        k += 1
        ids.append(tid)
    g, t = gate_after[gid]
    rows.append(dict(id=g, title=t, type="gate", predecessors=", ".join(ids[-2:]), parent=gid))
    prev = g
dl = {"disc-8": "2027-04-02", "desi-8": "2027-05-07", "buil-8": "2027-06-25", "veri-8": "2027-07-30", "launch": "2027-08-31", "go-no-go": "2027-08-06"}
if not baseline:
    for r in rows:
        if r["id"] in dl:
            r["deadline"] = dl[r["id"]]
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=H)
    w.writeheader()
    for r in rows:
        w.writerow(r)
print(sum(1 for r in rows if r.get("type") == "task"), "tasks")
