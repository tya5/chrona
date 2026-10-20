import json, sys, datetime as dt
sched = json.load(open(sys.argv[1]))["placements"]
out = sys.argv[2]
asof = dt.date(2027, 5, 10)
D = dt.date.fromisoformat
lines = ["version: chrona/actual-set/v0.3", "kind: actual-set", "id: launch-programme-observed", "body:",
         f"  asOf: '{asof}'", "  observations:"]
n = 0
for oid, p in sched.items():
    if oid in ("discovery", "design", "build", "verify", "launch-prep"):
        continue
    n += 1
    slip = [0, 1, 2, 0, 3, -1, 1][n % 7]
    if "at" in p:
        at = D(p["at"])
        if at <= asof:
            a = at + dt.timedelta(days=max(0, slip))
            lines.append(f"    - {{id: {oid}-obs, sequence: 1, projectObjectId: {oid}, actual: {{at: '{a}'}}}}")
        continue
    s, e = D(p["start"]), D(p["end"])
    if s >= asof:
        continue
    st = s + dt.timedelta(days=max(0, slip // 2))
    if e + dt.timedelta(days=slip) <= asof:
        fin = e + dt.timedelta(days=slip)
        if fin <= st:
            fin = st + dt.timedelta(days=1)
        lines.append(f"    - {{id: {oid}-obs, sequence: 1, projectObjectId: {oid}, actual: {{start: '{st}', finish: '{fin}', progress: 1}}}}")
    else:
        frac = round(min(0.9, max(0.1, (asof - s).days / max(1, (e - s).days) - 0.15)), 2)
        lines.append(f"    - {{id: {oid}-obs, sequence: 1, projectObjectId: {oid}, actual: {{start: '{st}', openUntil: asOf, progress: {frac}}}}}")
open(out, "w").write("\n".join(lines) + "\n")
print(len(lines) - 6, "observations")
