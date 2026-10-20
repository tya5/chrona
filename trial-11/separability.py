"""Pairwise CIEDE2000 of the legend key inks under normal and simulated vision, using chrona's own
function (the same one W_LEGEND_COLOR_NOT_SEPARABLE uses), because that warning only compares keys
of an encoded colour scale and never compares the semantic keys of this design."""
import itertools, sys, yaml
from chrona.presentation.model.color_separability import delta_e_2000, MINIMUM_CATEGORY_DELTA_E

scheme = yaml.safe_load(open(sys.argv[1]))["body"]
def ink(ref):
    return scheme["categories"][ref.split(":", 1)[1]] if ref.startswith("category:") else scheme["colors"][ref]
theme = yaml.safe_load(open(sys.argv[2]))["body"]["colorBindings"]
keys = {  # legend key -> the binding whose ink the key shows
    "planned": "planned.fill", "actual": "actual.fill", "baseline": "snapshot.stroke",
    "milestone": "milestone.fill", "today": "as-of.stroke", "non-working": "calendar-exception.fill",
}
inks = {k: ink(theme[b]) for k, b in keys.items()}
print(inks)
worst = []
for (a, ca), (b, cb) in itertools.combinations(inks.items(), 2):
    row = {v: delta_e_2000(ca, cb, vision=v) for v in ("normal", "protanopia", "deuteranopia", "tritanopia")}
    low = min(row.values())
    flag = "LOW" if low < MINIMUM_CATEGORY_DELTA_E else ""
    print(f"{a:12} {b:12} " + " ".join(f"{v[:4]}={d:6.1f}" for v, d in row.items()), flag)
