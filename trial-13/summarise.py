import json, re, collections, os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
P = "mission-light control-room-dark print-mono executive-light elevated-light editorial technical-print chrona-default-draft marquee sunday target-b titlecard yuya muted-executive wallboard-dark".split()
pat = re.compile(r"^W_SCENE_.*_CONTRAST$|^W_SCENE_ENCODING_CONTRAST$|^W_LEGEND_COLOR_NOT_SEPARABLE$|^W_PRESENTATION_SCALE_NOT_SEPARABLE$|^W_LEGEND_SWATCH_COLLISION$")
full = "-v" in sys.argv
summary = {}
for p in P:
    j = json.load(open(f"out/{p}.json"))
    c = collections.Counter()
    msgs = []
    for w in j.get("warnings", []):
        if pat.match(w["code"]):
            c[w["code"]] += w.get("count", 1)
            msgs.append(w["code"] + ": " + w["message"][:400] + (" " + json.dumps(w.get("measuredFacts")) if w.get("measuredFacts") else ""))
    s = json.load(open(f"out/{p}.scene.json"))
    roles = collections.Counter(pr.get("visualRole") for pr in s["surfaces"][0]["primitives"])
    fc = os.path.exists(f"out/{p}.noforecast")
    summary[p] = dict(total=sum(c.values()), codes=dict(c))
    print(p, "noFC" if fc else "FC", sum(c.values()), dict(c), "others:", sorted({w["code"] for w in j.get("warnings", [])} - set(c)))
    print("   roles:", dict(roles))
    if full:
        for m in msgs:
            print("     ", m)
json.dump(summary, open("out/warnings.json", "w"), indent=1)
