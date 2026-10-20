"""One-shot edit of the copied target-b theme into the Nordic theme (kept for the record)."""
import sys, yaml
path = sys.argv[1]
doc = yaml.safe_load(open(path))
doc["id"] = "nordic-paper"
b = doc["body"]
v = b["values"]
def num(name, value): v[name] = {"type": "number", "value": value}
v["editorial"]["value"] = "Noto Sans, Noto Sans JP, Hiragino Sans, Yu Gothic, sans-serif"
num("size.heading", 26)
num("size.body", 12)
num("size.group", 11.5)
num("size.legend", 10.5)
num("size.axis", 10.5)
num("size.asof", 10)
num("header-size", 10)
num("spacing.m", 20)
v["spacing.l"] = {"type": "number", "value": {"expr": "2.4 * {spacing.m}"}}
num("timeline-row-height", 25)
num("timeline-group-header-size", 30)
num("row-rule.width", 0.5)
num("opacity.row-rule", 1)
num("stroke-width", 0.75)
num("hairline", 0.5)
num("axis-lane-quarter", 24)
num("axis-lane-month", 22)
num("legend-gap", 18)
num("legend-item-min", 60)
num("legend-swatch-inline-size", 16)
num("legend-swatch-block-size", 8)
num("legend-point-swatch-size", 8)
num("legend-block", 18)
num("mark-height-planned", 0.42)
num("mark-height-actual", 0.16)
num("mark-height-ghost", 0.62)
num("symbol-height-actual", 0.55)
num("symbol-height-ghost", 0.55)
num("radius-plan", 0)
num("radius-actual", 0)
num("radius-ghost", 0)
num("header-spacing", 0.06)
num("small-caps-scale", 0.8)
num("group-spacing", 0.1)
v["small-caps"] = {"type": "textTransform", "value": "small-caps"}
v["text-transform-none"] = {"type": "textTransform", "value": "none"}
v["dash.as-of"] = {"type": "dashPattern", "value": [1, 0]}
circle = "M50 0A50 50 0 1 1 49.999 0Z"
v["milestone-symbol"]["value"]["parts"] = [{"d": circle, "paint": "fill"}]
v["milestone-symbol-baseline"]["value"]["parts"] = [{"d": "M50 6A44 44 0 1 1 49.999 6Z", "paint": "stroke"}]
v["arrow"]["value"].update({"headLength": 4, "headWidth": 4})

r = b["roles"]
r["heading"]["fontWeight"] = "weight.regular"
r["groupHeader"].update({"textTransform": "small-caps", "smallCapsScale": "small-caps-scale",
                         "letterSpacing": "group-spacing", "fontWeight": "weight.bold"})
r["legend"]["textTransform"] = "text-transform-none"
r["as-of-label"]["textTransform"] = "text-transform-none"
r["axisQuarter"]["fontWeight"] = "weight.regular"
r["axisQuarter"].update({"textTransform": "small-caps", "smallCapsScale": "small-caps-scale", "letterSpacing": "header-spacing"})
r["group-header-band"]["backgroundTreatment"] = "none"
r["axis-band-decoration"]["backgroundTreatment"] = "none"
r["row-rule"]["strokeWidth"] = "hairline"
r["axis-minor"]["strokeWidth"] = "hairline"
r["axis-major"]["strokeWidth"] = "hairline"
r["axis-rule"]["strokeWidth"] = "hairline"
r["dependency"]["strokeWidth"] = "hairline"
r["snapshot"]["strokeWidth"] = "stroke-width"
r["planned"]["strokeWidth"] = "hairline"

c = b["colorBindings"]
c.update({
    "axis-major.stroke": "rule",
    "axis-minor.stroke": "rule",
    "axis-band-decoration.fill": "surface",
    "axis-band-decoration2.fill": "surface",
    "group-header-band.fill": "surface",
    "snapshot.stroke": "category:ghost",
    "snapshot.fill": "surface",
    "progress-fill.fill": "accent",
    "progress-fill.stroke": "surface",
    "as-of.stroke": "accent",
    "milestone.fill": "text",
    "gate.fill": "text",
    "gate.stroke": "text",
    "annotation-kind-accent.fill": "accent",
    "slot-heading.fill": "textMuted",
})
b.pop("colorScales", None)
b["contrastPolicy"] = {}
yaml.safe_dump(doc, open(path, "w"), sort_keys=False, allow_unicode=True, width=120)
