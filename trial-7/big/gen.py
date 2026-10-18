import csv, random
from pathlib import Path
random.seed(7)
rows = []
names = ["Platform", "Payments", "Search", "Mobile", "Web", "Data", "Infra", "Security", "Support", "Marketing"]
for g, gname in enumerate(names):
    gid = f"g{g}"
    rows.append({"id": gid, "title": f"{gname} stream", "type": "group"})
    for i in range(40):
        tid = f"t{g}-{i}"
        preds = []
        if i >= 1:
            preds.append(f"t{g}-{i-1}")
        if i >= 3 and random.random() < 0.3:
            preds.append(f"t{g}-{random.randrange(0, i-1)}")
        if i >= 1 and g >= 1 and random.random() < 0.15:
            preds.append(f"t{random.randrange(0, g)}-{random.randrange(0, 40)}")
        row = {"id": tid, "title": f"{gname} work item {i+1}", "type": "task",
               "duration": f"{random.randint(2, 8)}wd", "parent": gid,
               "predecessors": ", ".join(dict.fromkeys(preds))}
        if i == 0:
            row["start"] = "2027-01-04"
        rows.append(row)
cols = ["id", "title", "type", "start", "duration", "parent", "predecessors"]
with open(Path(__file__).parent / "big.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in cols})
print(len(rows))
