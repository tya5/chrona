"""In-chart pair ΔE2000 and L* under each simulation (colours read from emitted Scenes)."""
import itertools, json, collections
from cvd import de2000, rgb_to_lab, simulate_rgb, hex01

V = ("normal", "deutan", "protan", "tritan")


def row(name, a, b):
    out = []
    for v in V:
        la, lb = (rgb_to_lab(simulate_rgb(hex01(x), v)) for x in (a, b))
        out.append(f"{v[:3]} {de2000(la, lb):5.1f} (L {la[0]:.0f}/{lb[0]:.0f})")
    print(f"{name:55s} {a} vs {b}: " + " | ".join(out))


def owners(pid):
    s = json.load(open(f"out/{pid}.scene.json"))
    c = collections.OrderedDict()
    for q in s["surfaces"][0]["primitives"]:
        if q.get("visualRole") == "planned" and q.get("purpose") == "planned":
            f = (q.get("paint") or {}).get("fill")
            if f: c[f] = c.get(f, 0) + 1
    return [k for k, n in c.items() if n == 8]


for pid in ("mission-light", "control-room-dark", "print-mono"):
    cols = owners(pid)
    print(pid, "owner fills", cols)
    worst = {}
    for v in V:
        worst[v] = min(de2000(*(rgb_to_lab(simulate_rgb(hex01(x), v)) for x in (a, b))) for a, b in itertools.combinations(cols, 2))
    print("   worst owner pair ΔE", {k: round(x, 1) for k, x in worst.items()})

pairs = [
    ("mission-light critical vs normal dependency", "#C0392B", "#5B6B7F"),
    ("control-room-dark critical vs normal dependency", "#FF6B6B", "#8EA0BA"),
    ("executive-light actual gate vs forecast gate", "#269D79", "#3986E6"),
    ("technical-print Behind vs Actual", "#B3241C", "#0D0D0D"),
    ("yuya actual vs forecast (gate dots, bar)", "#B22D1B", "#2F6F5E"),
    ("yuya actual vs progress", "#B22D1B", "#D6A444"),
    ("titlecard actual vs forecast", "#54E06A", "#FF7A1A"),
    ("titlecard progress vs forecast", "#FF4A3D", "#FF7A1A"),
    ("titlecard actual vs progress", "#54E06A", "#FF4A3D"),
    ("marquee forecast vs progress", "#A3202A", "#FF6B6B"),
    ("marquee forecast vs baseline outline", "#A3202A", "#D9A93D"),
    ("sunday actual line vs holiday column", "#D13A26", "#F7C948"),
    ("sunday actual vs forecast", "#D13A26", "#7EC8E3"),
    ("target-b progress vs calendar exception", "#C77A12", "#F8E4C9"),
    ("wallboard Aiko vs Ben", "#2A9D43", "#D2691E"),
    ("wallboard Dana vs Forecast/Milestone blue", "#8957E5", "#2F81F7"),
    ("wallboard Chen vs Eli", "#D1478C", "#1B9AAA"),
    ("wallboard Ben vs Chen", "#D2691E", "#D1478C"),
    ("wallboard Aiko vs Eli", "#2A9D43", "#1B9AAA"),
    ("delta text red vs neutral (target-b)", "#C62828", "#5B6B7F"),
]
for p in pairs:
    row(*p)
