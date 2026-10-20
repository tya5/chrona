import yaml
p = "nordic/theme.yaml"; d = yaml.safe_load(open(p))
b = d["body"]; v = b["values"]; r = b["roles"]; c = b["colorBindings"]
v["as-of-width"] = {"type": "number", "value": 1.25}
for k in ("asOf", "as-of"): r[k]["strokeWidth"] = "as-of-width"
c.update({"milestone.fill": "category:milestone", "gate.fill": "category:milestone", "gate.stroke": "category:milestone"})
yaml.safe_dump(d, open(p, "w"), sort_keys=False, allow_unicode=True, width=120)

p = "nordic/layout.yaml"; d = yaml.safe_load(open(p))
head = d["root"]["children"][0]
legend = head["children"][1]
legend.update({"columns": 3, "inlineSize": "content"})
legend.pop("itemMinInlineSize", None); legend.pop("direction", None)
d["root"]["children"][0]["alignItems"] = "end"
yaml.safe_dump(d, open(p, "w"), sort_keys=False, allow_unicode=True, width=120)
