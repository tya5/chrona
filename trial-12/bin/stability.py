"""Count Scene primitives of unchanged objects that move between consecutive weeks.

An object is 'unchanged' between week k-1 and k when its scheduled placement and its latest actual are equal.
For each primitive id present in both Scenes whose sourceRef is /objects/<id> of an unchanged object (or a
relation whose two endpoints are unchanged), compare bounds. Inline movement and block movement are counted
separately (row insertion/removal legitimately shifts rows vertically on table surfaces).
"""
import glob, json, os, sys, yaml
T = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def latest_actuals(k):
    d = yaml.safe_load(open(f"{T}/w{k}/actual.yaml"))
    best = {}
    for o in d["body"]["observations"]:
        if o["projectObjectId"] not in best or o["sequence"] > best[o["projectObjectId"]]["sequence"]:
            best[o["projectObjectId"]] = o
    return {k2: v["actual"] for k2, v in best.items()}


def unchanged(k):
    a = json.load(open(f"{T}/w{k-1}/schedule.json"))["placements"]
    b = json.load(open(f"{T}/w{k}/schedule.json"))["placements"]
    aa, ab = latest_actuals(k - 1), latest_actuals(k)
    return {o for o in a if o in b and a[o] == b[o] and aa.get(o) == ab.get(o)}


def objs_of(p):
    ref = p.get("sourceRef", "")
    if ref.startswith("/objects/"):
        return [ref.split("/")[2]]
    if ref.startswith("relation:id:"):
        rid = ref[len("relation:id:"):]
        return None if True else []
    return []


def rel_ends(k):
    proj = yaml.safe_load(open(f"{T}/w{k}/project.yaml"))
    return {r["id"]: (r["from"]["object"], r["to"]["object"]) for r in proj["relations"]}


def prims(path):
    d = json.load(open(path))
    out = {}
    for s in d["surfaces"]:
        for p in s["primitives"]:
            out[p["id"]] = p
    return out


rows = []
for k in (1, 2, 3):
    same = unchanged(k)
    rels = rel_ends(k)
    for cur in sorted(glob.glob(f"{T}/out/w{k}/*.scene.json")):
        name = os.path.basename(cur)
        prev = f"{T}/out/w{k-1}/{name}"
        if not os.path.exists(prev):
            continue
        a, b = prims(prev), prims(cur)
        n = mx = my = 0
        examples = []
        for pid, pb in b.items():
            pa = a.get(pid)
            if pa is None or "bounds" not in pb or "bounds" not in pa:
                continue
            ref = pb.get("sourceRef", "")
            if pb.get("sourceKind") == "object" or ref.startswith("/objects/"):
                ok = ref.split("/")[-1] in same
            elif ref.startswith("relation:id:"):
                e = rels.get(ref[len("relation:id:"):])
                ok = bool(e) and e[0] in same and e[1] in same
            else:
                continue
            if not ok:
                continue
            n += 1
            ba, bb = pa["bounds"], pb["bounds"]
            dx = abs(ba["inline"] - bb["inline"]) + abs(ba["inlineSize"] - bb["inlineSize"])
            dy = abs(ba["block"] - bb["block"]) + abs(ba["blockSize"] - bb["blockSize"])
            if dx > 0.01:
                mx += 1
                if len(examples) < 3 and pb.get("sourceKind") == "object":
                    examples.append(f"{pid[:60]} dx={dx:.1f}")
            if dy > 0.01:
                my += 1
        rows.append((f"w{k-1}->w{k}", name.replace(".scene.json", ""), n, mx, my, "; ".join(examples)))
for r in rows:
    print("\t".join(map(str, r)))
