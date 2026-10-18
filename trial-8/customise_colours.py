"""Declare risk colours in each copied preset (Scheme categories + Theme colorScales.series.slots)."""
from pathlib import Path
R = Path(__file__).resolve().parent
cols = {"executive-light": ("#A9CBEF", "#E3A33B", "#9B1C1C"),
        "target-b": ("#A9CBEF", "#E3A33B", "#9B1C1C"),
        "marquee": ("#5B6B7A", "#D9A93D", "#F25C5C")}
for d, (lo, me, hi) in cols.items():
    s = R / "looks" / d / "scheme.yaml"; t = s.read_text()
    if "risk-low" not in t:
        t = t.replace("  categories:\n", f"  categories:\n    risk-low: '{lo}'\n    risk-medium: '{me}'\n    risk-high: '{hi}'\n", 1)
        s.write_text(t)
    th = R / "looks" / d / "theme.yaml"; t = th.read_text()
    if "risk-low" not in t:
        block = "    series:\n      slots: {low: risk-low, medium: risk-medium, high: risk-high}\n"
        if "  colorScales:\n" in t:
            t = t.replace("  colorScales:\n", "  colorScales:\n" + block, 1)
        else:
            t = t.rstrip("\n") + "\n  colorScales:\n" + block
        th.write_text(t)
print("ok")
