"""One-shot edit of the copied target-b layout into the Nordic layout."""
import sys, yaml
path = sys.argv[1]
doc = yaml.safe_load(open(path))
doc["id"] = "nordic-paper"
vd = doc["viewDefaults"]
vd["shading"] = {"nonWorking": False, "exceptions": True}
vd["grouping"] = {"presentation": "header"}
vd["backgroundDecoration"] = {"rows": "rules", "groups": "none"}
# drop the filled quarter/month band tiers: hairline grid and labels only
vd["axis"]["tiers"] = [t for t in vd["axis"]["tiers"] if t["role"] != "band"]
root = doc["root"]
children = root["children"]
title = next(c for c in children if c["id"] == "title")
legend = next(c for c in children if c["id"] == "legend")
review = next(c for c in children if c["id"] == "review")
legend.update({"inlineSize": "content", "place": {"inline": "end", "block": "start", "safety": "safe"}})
head = {"id": "head", "kind": "row", "inlineSize": "fill", "blockSize": "content",
        "gap": {"token": "spacing.m"}, "padding": {"token": "spacing.none"},
        "alignItems": "start", "justifyContent": "space-between", "children": [title, legend]}
root["children"] = [head, review]
yaml.safe_dump(doc, open(path, "w"), sort_keys=False, allow_unicode=True, width=120)
