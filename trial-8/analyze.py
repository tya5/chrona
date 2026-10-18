"""Compare consecutive weeks' Scenes per design. usage: analyze.py VARIANT"""
import json, re, sys, collections
from pathlib import Path

R = Path(__file__).resolve().parent
variant = sys.argv[1]
OUT = R / "out" / variant
DESIGNS = ["executive-light", "target-b", "marquee"]
OBJ_ROW = re.compile(r'review-lane:\[.*?"([^"]+)"\]')


def load_week(w):
    proj = json.loads((R / f"w{w}" / "project.yaml").read_text())
    sch = json.loads((R / f"w{w}" / "schedule.json").read_text())["placements"]
    act = json.loads((R / f"w{w}" / "actual.yaml").read_text())["body"]
    latest = {}
    for o in act["observations"]:
        if o["projectObjectId"] not in latest or o["sequence"] > latest[o["projectObjectId"]]["sequence"]:
            latest[o["projectObjectId"]] = o
    return proj, sch, act["asOf"], latest


def object_signatures(w):
    proj, sch, asof, latest = load_week(w)
    rels = {r["id"]: r for r in proj["relations"]}
    inc = collections.defaultdict(set)
    for rid, r in rels.items():
        inc[r["from"]["object"]].add(rid); inc[r["to"]["object"]].add(rid)
    sig = {}
    for oid, o in proj["objects"].items():
        a = latest.get(oid)
        a = dict(a["actual"]) if a else None
        if a and a.get("openUntil") == "asOf":
            a["openUntil"] = asof
        sig[oid] = json.dumps([o.get("title"), o.get("fields"), o.get("deadline"), sch.get(oid), a, sorted(inc[oid])], sort_keys=True)
    rsig = {rid: json.dumps(r, sort_keys=True) for rid, r in rels.items()}
    return sig, rsig, rels


def owner(p):
    sr = p.get("sourceRef", "")
    m = re.match(r"relation:\d+:(.+)$", sr)
    if m:
        return ("rel", m.group(1))
    m = OBJ_ROW.match(sr)
    if m:
        return ("obj", m.group(1))
    if p.get("laneMemberId"):
        return ("obj", p["laneMemberId"])
    return ("obj", sr) if sr else ("global", p["id"])


def norm_id(i):
    return re.sub(r"relation:\d+:", "relation:", i)


def row_index(scene):
    rows = []
    for r in scene["surfaces"][0]["rows"]:
        m = OBJ_ROW.match(r["id"])
        rows.append((r["bounds"]["block"], r["bounds"]["blockSize"], m.group(1) if m else r["id"]))
    rows.sort()
    return rows


def ny(y, rows):
    prev = None
    for b, s, oid in rows:
        if y < b - 0.01:
            break
        prev = (b, s, oid)
    if prev is None:
        return ("abs", round(y, 1))
    b, s, oid = prev
    return (oid, round(y - b, 1))


def mappts(x, f):
    if isinstance(x, dict):
        return {k: mappts(v, f) for k, v in x.items()}
    if isinstance(x, list):
        if len(x) == 2 and all(isinstance(v, (int, float)) for v in x):
            return [x[0], f(x[1])]
        return [mappts(v, f) for v in x]
    return x


def geom(p, rows=None):
    f = (lambda y: round(y, 1)) if rows is None else (lambda y: ny(y, rows))
    g = {"kind": p["kind"], "text": p.get("text"), "paint": json.dumps(p.get("paint"), sort_keys=True),
         "symbol": mappts(p.get("symbol"), f)}
    b = p.get("bounds")
    if b:
        g["b"] = (round(b["inline"], 1), f(b["block"]), round(b["inlineSize"], 1), round(b["blockSize"], 1))
    if p.get("points"):
        g["pts"] = [(round(x, 1), f(y)) for x, y in p["points"]]
    return g


def flat(x):
    if isinstance(x, dict):
        out = []
        for k in sorted(x):
            out += [k] + flat(x[k])
        return out
    if isinstance(x, (list, tuple)):
        out = ["["]
        for v in x:
            out += flat(v)
        return out + ["]"]
    return [x]


def same(a, b, tol=0.5):
    fa, fb = flat(a), flat(b)
    if len(fa) != len(fb):
        return False
    for x, y in zip(fa, fb):
        if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool):
            if abs(x - y) > tol:
                return False
        elif x != y:
            return False
    return True


def warn_counts(log, d, w):
    rec = next(x for x in log if x["design"] == d and x["week"] == w)
    c = collections.Counter()
    for x in rec["warnings"]:
        c[x["code"]] += x.get("count", 1)
    return c, rec


def text_overlaps(scene):
    t = [p for p in scene["surfaces"][0]["primitives"] if p["kind"] == "Text" and p.get("bounds")]
    n = 0; ex = []
    for i in range(len(t)):
        a = t[i]["bounds"]
        for j in range(i + 1, len(t)):
            b = t[j]["bounds"]
            ox = min(a["inline"] + a["inlineSize"], b["inline"] + b["inlineSize"]) - max(a["inline"], b["inline"])
            oy = min(a["block"] + a["blockSize"], b["block"] + b["blockSize"]) - max(a["block"], b["block"])
            if ox > 1 and oy > 1:
                n += 1; ex.append((t[i]["text"], t[j]["text"]))
    vb = scene["viewport"]
    clipped = [p["text"] for p in t if p["bounds"]["inline"] < -0.5 or p["bounds"]["inline"] + p["bounds"]["inlineSize"] > vb["inlineSize"] + 0.5
               or p["bounds"]["block"] + p["bounds"]["blockSize"] > vb["blockSize"] + 0.5]
    return n, ex[:6], clipped[:6]


def label_side(scene):
    prims = scene["surfaces"][0]["primitives"]
    bars = {p["sourceRef"]: p["bounds"] for p in prims if p.get("purpose") == "planned" and p.get("bounds")}
    sides = {}
    for p in prims:
        if p.get("purpose") == "member-label":
            bar = bars.get(p["sourceRef"])
            if not bar:
                continue
            lb = p["bounds"]
            if lb["inline"] >= bar["inline"] + bar["inlineSize"] - 2:
                s = "end"
            elif lb["inline"] + lb["inlineSize"] <= bar["inline"] + 2:
                s = "start"
            else:
                s = "inside"
            sides[p["sourceRef"]] = s
    return sides


log = []
for f in OUT.glob("log-*.json"):
    log += json.loads(f.read_text())
sigs = {w: object_signatures(w) for w in range(1, 6)}
rows_out = []
detail = {}
for d in DESIGNS:
    scenes = {}
    for w in range(1, 6):
        p = OUT / f"{d}-w{w}.scene.json"
        if p.exists():
            scenes[w] = json.loads(p.read_text())
    for w in range(1, 6):
        if w not in scenes:
            continue
        n, ex, cl = text_overlaps(scenes[w])
        wc, rec = warn_counts(log, d, w)
        legend = [p["text"] for p in scenes[w]["surfaces"][0]["primitives"] if p.get("purpose") == "legend-label"]
        detail[f"{d}-w{w}"] = {"canvas": scenes[w]["viewport"], "textOverlaps": n, "overlapExamples": ex, "clippedText": cl,
                               "legend": legend, "warnings": dict(wc), "seconds": rec["seconds"],
                               "domain": [scenes[w]["surfaces"][0]["scale"]["domainStart"], scenes[w]["surfaces"][0]["scale"]["domainEnd"]]}
    for w in range(2, 6):
        if w not in scenes or w - 1 not in scenes:
            continue
        A, B = scenes[w - 1], scenes[w]
        (sa, ra, rels_a), (sb, rb, rels_b) = sigs[w - 1], sigs[w]
        unchanged_obj = {o for o in sa if o in sb and sa[o] == sb[o]}
        unchanged_rel = {r for r in ra if r in rb and ra[r] == rb[r]
                         and rels_a[r]["from"]["object"] in unchanged_obj and rels_a[r]["to"]["object"] in unchanged_obj}
        rowsA, rowsB = row_index(A), row_index(B)
        pa = {norm_id(p["id"]): p for p in A["surfaces"][0]["primitives"]}
        pb = {norm_id(p["id"]): p for p in B["surfaces"][0]["primitives"]}
        rawid_a = {p["id"] for p in A["surfaces"][0]["primitives"]}
        rawid_b = {p["id"] for p in B["surfaces"][0]["primitives"]}
        cnt = collections.Counter(); ex = collections.defaultdict(list)
        total_unch = 0
        for i, p in pa.items():
            kind, oid = owner(p)
            if not ((kind == "obj" and oid in unchanged_obj) or (kind == "rel" and oid in unchanged_rel)):
                continue
            total_unch += 1
            q = pb.get(i)
            if q is None:
                cnt["removed"] += 1; ex["removed"].append(i[:90]); continue
            if p["id"] not in rawid_b:
                cnt["id-renumbered"] += 1
            if not same(geom(p), geom(q)):
                cnt["raw"] += 1
                if not same(geom(p, rowsA), geom(q, rowsB)):
                    cnt["row-normalised"] += 1
                    cat = (kind if kind == "rel" else p.get("purpose"))
                    cnt["rn:" + str(cat)] += 1
                    ex["rn:" + str(cat)].append(oid)
        for i, q in pb.items():
            kind, oid = owner(q)
            if ((kind == "obj" and oid in unchanged_obj) or (kind == "rel" and oid in unchanged_rel)) and i not in pa:
                cnt["added"] += 1; ex["added"].append(i[:90])
        sa_side, sb_side = label_side(A), label_side(B)
        flips = [o for o in sa_side if o in sb_side and o in unchanged_obj and sa_side[o] != sb_side[o]]
        wa, _ = warn_counts(log, d, w - 1); wb, _ = warn_counts(log, d, w)
        wdelta = {k: wb.get(k, 0) - wa.get(k, 0) for k in set(wa) | set(wb) if wb.get(k, 0) != wa.get(k, 0)}
        rows_out.append({"design": d, "pair": f"w{w-1}->w{w}", "unchangedObjects": len(unchanged_obj), "unchangedRelations": len(unchanged_rel),
                         "primsOfUnchanged": total_unch, **dict(cnt), "labelSideFlips": flips,
                         "canvas": (A["viewport"]["blockSize"], B["viewport"]["blockSize"]),
                         "warnDelta": wdelta, "examples": {k: sorted(set(v))[:12] for k, v in ex.items()}})
(OUT / "analysis.json").write_text(json.dumps({"pairs": rows_out, "weeks": detail}, indent=1, default=str))
for r in rows_out:
    print(r["design"], r["pair"], {k: v for k, v in r.items() if k not in ("design", "pair", "examples")})
for k, v in detail.items():
    print(k, v["canvas"], "overlaps", v["textOverlaps"], v["overlapExamples"][:3], "clipped", v["clippedText"], "legend", v["legend"], v["seconds"], v["domain"])
