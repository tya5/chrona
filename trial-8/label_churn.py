"""Member labels of unchanged objects that appear/disappear between weeks (plain variant)."""
import json, sys
from pathlib import Path
R = Path(__file__).resolve().parent
sys.argv = ["analyze.py", "plain"]
src = (R / "analyze.py").read_text().split("\nlog = []")[0]
exec(src)
for d in ["executive-light", "target-b", "marquee"]:
    for w in range(2, 6):
        A = json.loads((R / f"out/plain/{d}-w{w-1}.scene.json").read_text())
        B = json.loads((R / f"out/plain/{d}-w{w}.scene.json").read_text())
        sa, _, _ = object_signatures(w - 1); sb, _, _ = object_signatures(w)
        un = {o for o in sa if o in sb and sa[o] == sb[o]}
        la = {p["sourceRef"] for p in A["surfaces"][0]["primitives"] if p.get("purpose") == "member-label"}
        lb = {p["sourceRef"] for p in B["surfaces"][0]["primitives"] if p.get("purpose") == "member-label"}
        print(d, w - 1, w, "gone", sorted((la - lb) & un), "new", sorted((lb - la) & un))
