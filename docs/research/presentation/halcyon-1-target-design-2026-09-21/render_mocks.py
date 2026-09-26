"""Draw the HALCYON-1 target slides: three layout proposals x three views.

Hand-drawn reference renderings (not Chrona output) for issues #41 / #42.
Usage: python render_mocks.py <output-dir>   -> <output-dir>/<proposal>/<view>.svg
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

# ---------------------------------------------------------------- data (examples/halcyon-1)
ASOF = date(2027, 8, 20)
GROUPS = [("bus", "Spacecraft bus"), ("payload", "Imaging payload"), ("ait", "Assembly, integration and test"),
          ("ground", "Ground segment"), ("launch", "Launch and range"), ("ops", "Mission operations")]
D = lambda s: date.fromisoformat(s)
# id: (group, title, team, phase, plan, actual, baseline)  plan/actual/baseline = (start, end) or ("at",) for gates
ITEMS = {
    "pdr": ("bus", "Preliminary design review", "Programme", "Design", ("2027-03-05",), None, None),
    "structure": ("bus", "Primary structure fabrication", "Spacecraft bus", "Build", ("2027-03-08", "2027-04-06"), ("2027-03-08", "2027-04-06"), None),
    "avionics": ("bus", "Avionics integration", "Spacecraft bus", "Build", ("2027-04-06", "2027-04-27"), ("2027-04-07", "2027-04-30"), ("2027-04-06", "2027-04-23")),
    "eps": ("bus", "Power system qualification", "Spacecraft bus", "Qualify", ("2027-03-22", "2027-04-08"), ("2027-03-22", "2027-04-05"), None),
    "bus-test": ("bus", "Bus functional test", "Spacecraft bus", "Qualify", ("2027-04-29", "2027-05-13"), ("2027-05-17", "2027-05-28"), ("2027-04-26", "2027-05-07")),
    "cdr": ("bus", "Critical design review", "Programme", "Design", ("2027-05-07",), None, None),
    "optics": ("payload", "Imager optics alignment", "Imaging payload", "Build", ("2027-03-08", "2027-04-01"), ("2027-03-08", "2027-04-02"), None),
    "detector": ("payload", "Detector calibration", "Imaging payload", "Qualify", ("2027-04-05", "2027-04-19"), ("2027-04-12", "2027-04-21"), None),
    "payload-tvac": ("payload", "Payload thermal-vacuum", "Imaging payload", "Qualify", ("2027-04-19", "2027-04-27"), ("2027-04-22", "2027-05-07"), None),
    "payload-delivery": ("payload", "Payload delivered", "Imaging payload", "Qualify", ("2027-07-02",), None, ("2027-06-25",)),
    "integration": ("ait", "Spacecraft integration", "AIT", "Integrate", ("2027-07-06", "2027-07-27"), ("2027-07-06", "2027-07-27"), ("2027-06-28", "2027-07-19")),
    "vibration": ("ait", "Vibration and shock", "AIT", "Verify", ("2027-07-28", "2027-08-04"), ("2027-07-28", "2027-08-04"), ("2027-07-20", "2027-07-27")),
    "tvac": ("ait", "System thermal-vacuum", "AIT", "Verify", ("2027-08-06", "2027-08-20"), None, ("2027-07-29", "2027-08-12")),
    "emc": ("ait", "EMC and RF compatibility", "AIT", "Verify", ("2027-08-23", "2027-08-30"), None, ("2027-08-16", "2027-08-23")),
    "psr": ("ait", "Pre-ship review", "Programme", "Verify", ("2027-09-10",), None, ("2027-09-03",)),
    "mcs": ("ground", "Mission control software", "Ground segment", "Build", ("2027-03-08", "2027-05-11"), ("2027-03-08", "2027-05-14"), None),
    "station": ("ground", "Ground station upgrade", "Ground segment", "Build", ("2027-04-19", "2027-06-01"), ("2027-04-19", "2027-05-21"), None),
    "comms-test": ("ground", "End-to-end link test", "Ground segment", "Verify", ("2027-06-01", "2027-06-08"), ("2027-05-24", "2027-05-28"), None),
    "launch-contract": ("launch", "Launch services confirmed", "Launch and range", "Design", ("2027-04-16",), None, None),
    "shipment": ("launch", "Ship to range", "Launch and range", "Campaign", ("2027-09-14", "2027-09-20"), None, None),
    "campaign": ("launch", "Launch campaign", "Launch and range", "Campaign", ("2027-09-21", "2027-10-08"), None, None),
    "frr": ("launch", "Flight readiness review", "Programme", "Campaign", ("2027-10-15",), None, None),
    "launch": ("launch", "Launch window opens", "Launch and range", "Campaign", ("2027-10-22",), None, None),
    "rehearsals": ("ops", "Operations rehearsals", "Mission operations", "Verify", ("2027-08-30", "2027-09-14"), None, None),
    "leop": ("ops", "LEOP and commissioning", "Mission operations", "Operate", ("2027-10-22", "2027-11-12"), None, None),
    "first-light": ("ops", "First light", "Mission operations", "Operate", ("2027-11-19",), None, None),
}
DEPS = [("pdr", "structure"), ("structure", "avionics"), ("eps", "bus-test"), ("avionics", "bus-test"), ("avionics", "cdr"),
        ("optics", "detector"), ("detector", "payload-tvac"), ("payload-tvac", "payload-delivery"), ("bus-test", "integration"),
        ("payload-delivery", "integration"), ("integration", "vibration"), ("vibration", "tvac"), ("tvac", "emc"), ("emc", "psr"),
        ("mcs", "comms-test"), ("station", "comms-test"), ("comms-test", "rehearsals"), ("psr", "shipment"), ("shipment", "campaign"),
        ("campaign", "frr"), ("frr", "launch"), ("launch", "leop"), ("leop", "first-light"), ("rehearsals", "launch")]
CALLOUTS = [("payload-tvac", "risk", "Payload TVAC ran 7 days late; margin is now zero."),
            ("station", "note", "Ground station done early; link test can move up."),
            ("launch", "note", "Launch window 22 Oct - 5 Nov; missing it means Q1.")]
HOLIDAYS = [D(s) for s in ("2027-04-02", "2027-05-31", "2027-07-05", "2027-09-06", "2027-10-09", "2027-10-16")]
WINDOW = (D("2027-10-22"), D("2027-11-05"))

VIEWS = {
    "01-mission-brief": dict(title="Mission brief", subtitle="Gates and the spans that feed them - plan, observed and finish variance",
                             ids=["pdr", "structure", "avionics", "bus-test", "cdr", "optics", "payload-tvac", "payload-delivery",
                                  "integration", "tvac", "psr", "campaign", "frr", "launch", "leop", "first-light"],
                             window=(D("2027-03-01"), D("2027-12-01")), grouped=False, columns=["title", "team"]),
    "02-programme-board": dict(title="Programme board", subtitle="Every work package by owning team - baseline, current plan and observed",
                               ids=list(ITEMS), window=(D("2027-03-01"), D("2027-12-01")), grouped=True, columns=["title", "phase"]),
    "03-launch-campaign": dict(title="Launch campaign", subtitle="Integration to first light, July - November 2027",
                               ids=["integration", "vibration", "tvac", "emc", "psr", "rehearsals", "shipment", "campaign", "frr", "launch", "leop", "first-light"],
                               window=(D("2027-07-01"), D("2027-12-01")), grouped=False, columns=["title", "phase", "team"]),
}

SCHEMES = {
    "mission-light": dict(surface="#FFFFFF", raised="#EEF2F7", text="#101828", muted="#5B6B7F", accent="#1D5FD1", accentSoft="#9DB8EA",
                          positive="#0E8A6C", negative="#C0392B", warning="#C77A12", neutral="#C6CFDA", line="#D5DCE6",
                          category=["#E8EFFA", "#E4F4EE", "#FBF0E1", "#F1E9F8", "#FDEBEA", "#EAF3F4"],
                          closed="rgba(16,24,40,0.045)", holiday="rgba(199,122,18,0.16)", window="rgba(29,95,209,0.09)"),
    "control-room-dark": dict(surface="#0B1220", raised="#16213A", text="#EAF0FA", muted="#8EA0BA", accent="#5FA8FF", accentSoft="#35598F",
                              positive="#35D0A0", negative="#FF6B6B", warning="#FFC857", neutral="#2E3F5E", line="#1F2D47",
                              category=["#142642", "#12302B", "#2C2138", "#33261A", "#3A1F2A", "#12303A"],
                              closed="rgba(255,255,255,0.035)", holiday="rgba(255,200,87,0.18)", window="rgba(95,168,255,0.14)"),
    "print-mono": dict(surface="#FFFFFF", raised="#F1F1F1", text="#111111", muted="#555555", accent="#1F1F1F", accentSoft="#8C8C8C",
                       positive="#555555", negative="#B00020", warning="#7A5A00", neutral="#BDBDBD", line="#CFCFCF",
                       category=["#F4F4F4", "#E9E9E9", "#DEDEDE", "#D3D3D3", "#F4F4F4", "#E9E9E9"],
                       closed="rgba(0,0,0,0.05)", holiday="rgba(0,0,0,0.14)", window="rgba(0,0,0,0.07)"),
}
SANS = "Nimbus Sans, Helvetica Neue, Helvetica, Arial, sans-serif"


# ---------------------------------------------------------------- helpers
class Svg:
    def __init__(self, w, h):
        self.w, self.h, self.parts = w, h, []

    def add(self, s): self.parts.append(s)

    def rect(self, x, y, w, h, fill, **kw): self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"{attrs(kw)}/>')

    def line(self, x1, y1, x2, y2, stroke, **kw): self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}"{attrs(kw)}/>')

    def path(self, d, **kw): self.add(f'<path d="{d}"{attrs(kw)}/>')

    def text(self, x, y, s, size, fill, weight=400, anchor="start", **kw):
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{SANS}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{attrs(kw)}>{escape(s)}</text>')

    def diamond(self, cx, cy, r, fill, **kw): self.path(f"M{cx:.1f},{cy - r:.1f} L{cx + r:.1f},{cy:.1f} L{cx:.1f},{cy + r:.1f} L{cx - r:.1f},{cy:.1f} Z", fill=fill, **kw)

    def render(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}">'
                + "".join(self.parts) + "</svg>")


def attrs(kw):
    return "".join(f' {k.replace("_", "-")}="{v}"' for k, v in kw.items())


def tw(s, size):  # rough Helvetica width
    return len(s) * size * 0.54


def delta(item):
    plan, actual = item[4], item[5]
    if len(plan) == 1 or not actual: return None
    return (D(actual[1]) - D(plan[1])).days


def defs(svg, sc, mono=False):
    hatch = sc["accent"]
    svg.add(f'<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            f'<line x1="0" y1="0" x2="0" y2="6" stroke="{hatch}" stroke-width="2"/></pattern>'
            f'<marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
            f'<path d="M0,0 L8,4 L0,8 z" fill="{sc["muted"]}"/></marker></defs>')


class Scale:
    def __init__(self, window, x0, x1):
        self.w0, self.w1, self.x0, self.x1 = window[0], window[1], x0, x1
        self.days = (self.w1 - self.w0).days
        self.dw = (x1 - x0) / self.days

    def x(self, d): return self.x0 + (d - self.w0).days * self.dw

    def xe(self, d): return self.x(d) + self.dw


def months(window):
    d = date(window[0].year, window[0].month, 1)
    out = []
    while d < window[1]:
        n = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
        out.append((d, min(n, window[1]))); d = n
    return out


def quarters(window):
    out, d = [], window[0]
    while d < window[1]:
        q = (d.month - 1) // 3
        qs = date(d.year, q * 3 + 1, 1)
        qe = date(d.year + (q == 3), (q + 1) % 4 * 3 + 1, 1)
        out.append((max(qs, window[0]), min(qe, window[1]), f"Q{q + 1} {d.year}")); d = qe
    return out


def calendar_bg(svg, sc, S, top, bot, weekends=True):
    if weekends:
        d = S.w0
        while d < S.w1:
            if d.weekday() >= 5: svg.rect(S.x(d), top, S.dw, bot - top, sc["closed"])
            d += timedelta(days=1)
    for h in HOLIDAYS:
        if S.w0 <= h < S.w1: svg.rect(S.x(h), top, S.dw, bot - top, sc["holiday"])
    if S.w0 <= WINDOW[0] < S.w1:
        svg.rect(S.x(WINDOW[0]), top, S.xe(WINDOW[1]) - S.x(WINDOW[0]), bot - top, sc["window"])


def rows_for(view):
    """[(kind, key, y-index)] with group headers when grouped."""
    out = []
    if view["grouped"]:
        for gid, gtitle in GROUPS:
            members = [i for i in view["ids"] if ITEMS[i][0] == gid]
            if not members: continue
            out.append(("head", gid, gtitle))
            out.extend(("item", i, None) for i in members)
    else:
        ids = sorted(view["ids"], key=lambda i: (D(ITEMS[i][4][0]), i))
        out.extend(("item", i, None) for i in ids)
    return out


def draw_marks(svg, sc, S, y, h, item, style="fill", anchors=None, key=None, mono=False):
    """Baseline ghost + plan + actual on one track. Returns anchor (x_right, y, x_left)."""
    plan, actual, base = item[4], item[5], item[6]
    cy = y + h / 2
    if len(plan) == 1:
        x = S.x(D(plan[0])) + S.dw / 2
        r = min(7, h * 0.36)
        if base: svg.diamond(S.x(D(base[0])) + S.dw / 2, cy, r - 0.5, "none", stroke=sc["accentSoft"], stroke_width=1.5)
        svg.diamond(x, cy, r, sc["text"], stroke=sc["surface"], stroke_width=1.5)
        a = (x + r, cy, x - r)
    else:
        ps, pe = D(plan[0]), D(plan[1])
        bar = min(8, h * 0.4)
        if base and (base[0], base[1]) != (plan[0], plan[1]):
            svg.rect(S.x(D(base[0])), cy - bar * 0.85, S.xe(D(base[1])) - S.x(D(base[0])), bar * 1.7, "none",
                     rx=2, stroke=sc["accentSoft"], stroke_width=1.5, stroke_dasharray="3 2")
        missing = actual is None and ps <= ASOF
        if style == "outline":
            svg.rect(S.x(ps), cy - bar * 0.7, S.xe(pe) - S.x(ps), bar * 1.4, "url(#hatch)" if missing else "none",
                     rx=1.5, stroke=sc["accent"], stroke_width=1.2)
        else:
            svg.rect(S.x(ps), cy - bar * 0.7, S.xe(pe) - S.x(ps), bar, "url(#hatch)" if missing else sc["accent"], rx=1.5,
                     **({"stroke": sc["accent"], "stroke_width": 1} if missing else {}))
        if actual:
            a0, a1 = D(actual[0]), D(actual[1])
            svg.rect(S.x(a0), cy + bar * 0.4, S.xe(a1) - S.x(a0), max(3, bar * 0.42), sc["text"], rx=1)
        a = (S.xe(pe), cy, S.x(ps))
    if anchors is not None and key: anchors[key] = a
    return a


def draw_deps(svg, sc, anchors, rowh, ids):
    for a, b in DEPS:
        if a not in anchors or b not in anchors or a not in ids or b not in ids: continue
        A, B = anchors[a], anchors[b]
        if B[2] - 6 >= A[0] + 4:
            d = f"M{A[0]:.1f},{A[1]:.1f} H{B[2] - 6:.1f} V{B[1]:.1f} H{B[2] - 1:.1f}"
        else:
            step = rowh / 2 if B[1] > A[1] else -rowh / 2
            d = f"M{A[0]:.1f},{A[1]:.1f} H{A[0] + 6:.1f} V{B[1] - step:.1f} H{B[2] - 6:.1f} V{B[1]:.1f} H{B[2] - 1:.1f}"
        svg.path(d, fill="none", stroke=sc["muted"], stroke_width=1, opacity=0.8, marker_end="url(#arrow)")


def asof_line(svg, sc, S, top, bot, label=True):
    x = S.x(ASOF)
    svg.line(x, top, x, bot, sc["warning"], stroke_width=1.5, stroke_dasharray="4 3")
    if label:
        svg.rect(x - 34, bot + 4, 68, 16, sc["warning"], rx=3)
        svg.text(x, bot + 16, "as of 20 Aug", 10.5, sc["surface"], 600, "middle")


def circled(svg, sc, cx, cy, n, risk):
    col = sc["negative"] if risk else sc["text"]
    svg.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6.5" fill="none" stroke="{col}" stroke-width="1"/>')
    svg.text(cx, cy + 3, str(n), 8.5, col, 600, "middle")


def wrap(s, n):
    words, lines, cur = s.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > n and cur: lines.append(cur); cur = w
        else: cur = (cur + " " + w).strip()
    if cur: lines.append(cur)
    return lines


def legend(svg, sc, x, y, entries, size=12):
    for kind, label in entries:
        if kind == "baseline": svg.rect(x, y - 6, 22, 12, "none", rx=2, stroke=sc["accentSoft"], stroke_width=1.5, stroke_dasharray="3 2")
        elif kind == "plan": svg.rect(x, y - 4, 22, 7, sc["accent"], rx=1.5)
        elif kind == "plan-outline": svg.rect(x, y - 4, 22, 8, "none", rx=1.5, stroke=sc["accent"], stroke_width=1.2)
        elif kind == "actual": svg.rect(x, y - 2, 22, 3, sc["text"], rx=1)
        elif kind == "missing": svg.rect(x, y - 4, 22, 7, "url(#hatch)", rx=1.5, stroke=sc["accent"], stroke_width=1)
        elif kind == "gate": svg.diamond(x + 11, y, 6, sc["text"])
        elif kind == "closed": svg.rect(x, y - 6, 22, 12, sc["closed"], stroke=sc["line"])
        elif kind == "holiday": svg.rect(x, y - 6, 22, 12, sc["holiday"])
        elif kind == "dep": svg.path(f"M{x},{y} H{x + 20}", stroke=sc["muted"], stroke_width=1, marker_end="url(#arrow)")
        svg.text(x + 28, y + 4, label, size, sc["muted"])
        x += 28 + tw(label, size) + 26
    return x


# ---------------------------------------------------------------- proposal A: board
def board(view_id, view):
    sc = SCHEMES["mission-light"]; W, H = 1600, 900
    svg = Svg(W, H); defs(svg, sc)
    svg.rect(0, 0, W, H, sc["surface"])
    M = dict(top=64, left=36, right=36)
    rows = rows_for(view)
    n_items = sum(r[0] == "item" for r in rows); n_heads = sum(r[0] == "head" for r in rows)
    axisH, headH = 42, 24
    avail = H - M["top"] - axisH - 6 - 76
    rowh = max(18, min(32 if n_items <= 16 else 26, (avail - n_heads * headH) / max(1, n_items)))
    cols = view["columns"]; colw = {"title": 250, "team": 130, "phase": 80}
    tableW = sum(colw[c] for c in cols) + 52
    rail = 250 if any(c[0] in view["ids"] for c in CALLOUTS) else 0
    x0 = M["left"] + tableW + 12; x1 = W - M["right"] - rail - (16 if rail else 0)
    S = Scale(view["window"], x0, x1)
    svg.text(M["left"], 34, f"HALCYON-1 · {view['title']}", 22, sc["text"], 600)
    svg.text(M["left"], 52, f"{view['subtitle']} · as of 20 Aug 2027 · calendar: engineering (range for launch campaign)", 12.5, sc["muted"])
    svg.text(W - M["right"], 34, "target mock · not renderer output", 11.5, sc["muted"], anchor="end", letter_spacing=".06em")
    # rows
    y = M["top"] + axisH + 6; ys = []
    for r in rows:
        h = headH if r[0] == "head" else rowh
        ys.append((r, y, h)); y += h
    plotTop, plotBot = M["top"] + axisH, y
    calendar_bg(svg, sc, S, plotTop, plotBot)
    # axis
    for a, b, l in quarters(view["window"]):
        svg.rect(S.x(a), M["top"], S.x(b) - S.x(a), 18, sc["raised"], stroke=sc["surface"])
        svg.text((S.x(a) + S.x(b)) / 2, M["top"] + 13, l, 11.5, sc["text"], 600, "middle", letter_spacing=".05em")
    for a, b in months(view["window"]):
        svg.line(S.x(a), M["top"] + 18, S.x(a), plotBot, sc["line"])
        svg.text((S.x(a) + S.x(b)) / 2, M["top"] + 34, a.strftime("%b"), 12, sc["muted"], anchor="middle")
    svg.line(S.x(view["window"][1]), M["top"] + 18, S.x(view["window"][1]), plotBot, sc["line"])
    svg.line(x0, plotTop, x1, plotTop, sc["line"])
    # table headers
    cx = M["left"] + 16
    for c in cols:
        svg.text(cx if c == "title" else cx, M["top"] + 34, {"title": "Work package", "team": "Team", "phase": "Phase"}[c], 11, sc["muted"], letter_spacing=".05em")
        cx += colw[c]
    svg.text(M["left"] + tableW - 4, M["top"] + 34, "Δ finish", 11, sc["muted"], anchor="end", letter_spacing=".05em")
    anchors = {}
    for (r, y, h) in ys:
        if r[0] == "head":
            gi = [g[0] for g in GROUPS].index(r[1])
            svg.rect(M["left"], y + 2, x1 - M["left"], h - 2, sc["category"][gi])
            svg.text(M["left"] + 8, y + 17, r[2], 12, sc["text"], 600, letter_spacing=".02em")
            if S.w0 <= WINDOW[0] < S.w1 and gi == 0:
                svg.text(S.x(WINDOW[0]) + 4, y + 17, "launch window", 10.5, sc["accent"], letter_spacing=".04em")
            continue
        item = ITEMS[r[1]]; cx = M["left"] + 16; ty = y + h / 2 + 4.5
        for c in cols:
            svg.text(cx, ty, {"title": item[1], "team": item[2], "phase": item[3]}[c], 12.5 if c == "title" else 11.5, sc["text"] if c == "title" else sc["muted"])
            cx += colw[c]
        d = delta(item)
        if d is not None:
            svg.text(M["left"] + tableW - 4, ty, f"{d:+d}d", 12, sc["negative"] if d > 0 else sc["positive"] if d < 0 else sc["muted"], 600, "end")
        elif item[5] is None and len(item[4]) == 2 and D(item[4][0]) <= ASOF:
            svg.text(M["left"] + tableW - 4, ty, "—", 12, sc["muted"], anchor="end")
        svg.line(M["left"], y + h, x1, y + h, sc["line"], stroke_width=0.5, opacity=0.7)
        draw_marks(svg, sc, S, y, h, item, anchors=anchors, key=r[1])
    if not view["grouped"] and S.w0 <= WINDOW[0] < S.w1:
        svg.text(S.x(WINDOW[0]) + 4, plotTop + 13, "launch window", 10.5, sc["accent"], letter_spacing=".04em")
    draw_deps(svg, sc, anchors, rowh, set(view["ids"]))
    asof_line(svg, sc, S, plotTop, plotBot)
    # callout rail
    if rail:
        rx0 = x1 + 16; svg.text(rx0, M["top"] + 13, "NOTES", 11, sc["muted"], 600, letter_spacing=".1em")
        last = M["top"] + 24
        for cid, kind, text in CALLOUTS:
            if cid not in anchors: continue
            A = anchors[cid]; boxH = 46; by = max(A[1] - boxH / 2, last + 8); last = by + boxH
            col = sc["negative"] if kind == "risk" else sc["accent"]
            svg.rect(rx0, by, rail, boxH, sc["raised"], rx=3); svg.rect(rx0, by, 3, boxH, col)
            svg.text(rx0 + 12, by + 15, f"{kind.upper()} · {cid}", 10.5, col, 600, letter_spacing=".06em")
            for i, l in enumerate(wrap(text, 40)[:2]): svg.text(rx0 + 12, by + 29 + i * 13, l, 11.5, sc["text"])
            svg.path(f"M{A[0] + 8:.1f},{A[1]:.1f} H{x1 + 6} V{by + boxH / 2:.1f} H{rx0}", fill="none", stroke=col, stroke_width=1, stroke_dasharray="2 2")
            svg.add(f'<circle cx="{A[0] + 8:.1f}" cy="{A[1]:.1f}" r="2.5" fill="{col}"/>')
    legend(svg, sc, M["left"], H - 26, [("baseline", "baseline"), ("plan", "current plan"), ("actual", "actual"), ("missing", "in progress, not yet observed"),
                                          ("gate", "gate"), ("closed", "non-working day"), ("holiday", "calendar exception"), ("dep", "dependency")])
    return svg.render()


# ---------------------------------------------------------------- proposal B: sidebar (dark wallboard, labels on the plot)
def sidebar(view_id, view):
    sc = SCHEMES["control-room-dark"]; W, H = 1920, 1080
    svg = Svg(W, H); defs(svg, sc)
    svg.rect(0, 0, W, H, sc["surface"])
    side, pad = 400, 40
    svg.rect(0, 0, side, H, sc["raised"])
    # sidebar: title, key figures, notes
    svg.text(pad, 78, "HALCYON-1", 13, sc["accent"], 600, letter_spacing=".18em")
    ty = 118
    for l in wrap(view["title"], 14): svg.text(pad, ty, l, 40, sc["text"], 600); ty += 44
    ty += 6
    for l in wrap(view["subtitle"], 36): svg.text(pad, ty, l, 15, sc["muted"]); ty += 21
    ty += 24
    ids = set(view["ids"]); slips = sum(1 for i in ids if (delta(ITEMS[i]) or 0) > 0); ahead = sum(1 for i in ids if (delta(ITEMS[i]) or 0) < 0)
    figs = [("as of", "20 Aug 2027"), ("launch window", "22 Oct 2027"), ("behind / ahead", f"{slips} / {ahead}")]
    for label, val in figs:
        svg.text(pad, ty, label.upper(), 10.5, sc["muted"], 600, letter_spacing=".12em"); svg.text(pad, ty + 24, val, 22, sc["text"], 600); ty += 54
    ty += 14
    notes = [c for c in CALLOUTS if c[0] in ids]
    if notes:
        svg.text(pad, ty, "NOTES", 10.5, sc["muted"], 600, letter_spacing=".12em"); ty += 14
        for n, (cid, kind, text) in enumerate(notes, 1):
            col = sc["negative"] if kind == "risk" else sc["accent"]
            svg.add(f'<circle cx="{pad + 9}" cy="{ty + 9}" r="9" fill="{col}"/>'); svg.text(pad + 9, ty + 13, str(n), 11, sc["surface"], 700, "middle")
            for i, l in enumerate(wrap(text, 40)[:3]): svg.text(pad + 28, ty + 13 + i * 17, l, 13.5, sc["text"])
            ty += 17 * min(3, len(wrap(text, 40))) + 16
    svg.text(pad, H - 36, "target mock · not renderer output", 11.5, sc["muted"], letter_spacing=".06em")
    # plot
    x0, x1 = side + 60, W - 60; top = 96
    rows = rows_for(view); n_items = sum(r[0] == "item" for r in rows); n_heads = sum(r[0] == "head" for r in rows)
    headH = 30; avail = H - top - 60 - 40
    rowh = max(20, min(30, (avail - n_heads * headH) / max(1, n_items)))
    S = Scale(view["window"], x0, x1)
    y = top + 44; ys = []
    for r in rows:
        h = headH if r[0] == "head" else rowh; ys.append((r, y, h)); y += h
    plotTop, plotBot = top + 40, y
    calendar_bg(svg, sc, S, plotTop, plotBot)
    for a, b in months(view["window"]):
        svg.line(S.x(a), top, S.x(a), plotBot, sc["line"])
        svg.text(S.x(a) + 6, top + 14, a.strftime("%B %Y").upper() if a.month in (1, 3, 7, 10) or a == view["window"][0] else a.strftime("%b").upper(), 11, sc["muted"], 600, letter_spacing=".1em")
        d = a + timedelta(days=(7 - a.weekday()) % 7)
        while d < b:
            svg.line(S.x(d), top + 24, S.x(d), top + 30, sc["neutral"]); d += timedelta(days=7)
    svg.line(x0, plotTop, x1, plotTop, sc["neutral"])
    if S.w0 <= WINDOW[0] < S.w1: svg.text(S.x(WINDOW[0]) + 4, plotTop + 14, "LAUNCH WINDOW", 10, sc["accent"], 600, letter_spacing=".1em")
    anchors = {}; noteidx = {c[0]: n for n, c in enumerate(notes, 1)}
    for (r, y, h) in ys:
        if r[0] == "head":
            svg.line(x0, y + h - 6, x1, y + h - 6, sc["neutral"], stroke_width=1)
            svg.text(x0, y + h - 11, r[2].upper(), 11, sc["muted"], 600, letter_spacing=".14em"); continue
        item = ITEMS[r[1]]; a = draw_marks(svg, sc, S, y, h, item, anchors=anchors, key=r[1])
        label = item[1]; d = delta(item)
        if d is not None and d != 0: label += f"  {d:+d}d"
        lw = tw(label, 12.5)
        lx, anc = (a[2] - 10, "end") if a[2] - 10 - lw > x0 else (a[0] + 10, "start")
        svg.text(lx, y + h / 2 + 4.5, label, 12.5, sc["text"], anchor=anc)
        if d is not None and d != 0:
            col = sc["negative"] if d > 0 else sc["positive"]
            dx = lx - tw(f"{d:+d}d", 12.5) if anc == "end" else lx + lw - tw(f"{d:+d}d", 12.5)
            svg.rect(dx - 2, y + h / 2 - 7, tw(f"{d:+d}d", 12.5) + 4, 15, sc["surface"], rx=2)
            svg.text(dx, y + h / 2 + 4.5, f"{d:+d}d", 12.5, col, 600)
        if r[1] in noteidx:
            col = sc["negative"] if [c for c in notes if c[0] == r[1]][0][1] == "risk" else sc["accent"]
            nx = a[0] + 8 if anc == "end" else lx + lw + 12
            svg.add(f'<circle cx="{nx + 8:.1f}" cy="{y + h / 2:.1f}" r="8" fill="{col}"/>'); svg.text(nx + 8, y + h / 2 + 3.5, str(noteidx[r[1]]), 10, sc["surface"], 700, "middle")
    draw_deps(svg, sc, anchors, rowh, set(view["ids"]))
    asof_line(svg, sc, S, plotTop, plotBot)
    legend(svg, sc, x0, H - 36, [("baseline", "baseline"), ("plan", "current plan"), ("actual", "actual"), ("missing", "in progress, not yet observed"),
                                  ("gate", "gate"), ("holiday", "calendar exception"), ("dep", "dependency")], size=12)
    return svg.render()


# ---------------------------------------------------------------- proposal C: dossier (print, portrait, mono)
def dossier(view_id, view):
    sc = SCHEMES["print-mono"]; W, H = 1200, 1120
    svg = Svg(W, H); defs(svg, sc)
    svg.rect(0, 0, W, H, sc["surface"])
    M = 56
    svg.text(M, 64, "HALCYON-1", 12, sc["muted"], 600, letter_spacing=".2em")
    svg.text(M, 100, view["title"], 30, sc["text"], 600)
    svg.text(W - M, 64, "Programme review · as of 20 Aug 2027", 12, sc["muted"], anchor="end")
    svg.text(W - M, 100, "target mock · not renderer output", 11, sc["muted"], anchor="end", letter_spacing=".06em")
    svg.line(M, 116, W - M, 116, sc["text"], stroke_width=1.5)
    for i, l in enumerate(wrap(view["subtitle"], 110)): svg.text(M, 140 + i * 17, l, 13, sc["muted"])
    top = 176
    rows = rows_for(view); n_items = sum(r[0] == "item" for r in rows); n_heads = sum(r[0] == "head" for r in rows)
    notes = [c for c in CALLOUTS if c[0] in view["ids"]]
    footH = 40 + 20 * len(notes) + 44
    headH = 26; avail = H - top - 36 - footH
    rowh = max(18, min(30 if n_items <= 16 else 24, (avail - n_heads * headH) / max(1, n_items)))
    cols = [("#", 28), ("Activity", 210), ("Plan", 116), ("Actual", 116), ("Δ", 40)]
    tableW = sum(w for _, w in cols)
    x0, x1 = M + tableW + 20, W - M
    S = Scale(view["window"], x0, x1)
    # header row
    cx = M
    for name, w in cols:
        svg.text(cx + (w - 4 if name == "Δ" else 0), top + 24, name.upper(), 10, sc["muted"], 600, "end" if name == "Δ" else "start", letter_spacing=".1em"); cx += w
    for a, b in months(view["window"]):
        svg.line(S.x(a), top + 8, S.x(a), top + 36, sc["line"])
        svg.text((S.x(a) + S.x(b)) / 2, top + 24, a.strftime("%b %Y") if S.days < 200 else a.strftime("%b"), 10.5, sc["text"], 600, "middle", letter_spacing=".06em")
    svg.line(M, top + 36, W - M, top + 36, sc["text"], stroke_width=1)
    y = top + 40; ys = []
    for r in rows:
        h = headH if r[0] == "head" else rowh; ys.append((r, y, h)); y += h
    plotTop, plotBot = top + 36, y
    calendar_bg(svg, sc, S, plotTop, plotBot, weekends=S.days < 200)
    for a, b in months(view["window"]):
        svg.line(S.x(a), plotTop, S.x(a), plotBot, sc["line"])
        if S.days < 200:
            d = a + timedelta(days=(7 - a.weekday()) % 7)
            while d < b: svg.line(S.x(d), plotTop, S.x(d), plotBot, sc["line"], stroke_width=0.5, stroke_dasharray="1 3"); d += timedelta(days=7)
    anchors = {}; noteidx = {c[0]: n for n, c in enumerate(notes, 1)}; k = 0
    for (r, y, h) in ys:
        if r[0] == "head":
            gi = [g[0] for g in GROUPS].index(r[1])
            svg.rect(M, y + 3, W - 2 * M, h - 4, sc["category"][gi % 4])
            svg.text(M + 6, y + h / 2 + 4, r[2].upper(), 10.5, sc["text"], 600, letter_spacing=".12em"); continue
        k += 1; item = ITEMS[r[1]]; ty = y + h / 2 + 4; cx = M
        plan, actual = item[4], item[5]
        ptxt = D(plan[0]).strftime("%d %b") if len(plan) == 1 else f"{D(plan[0]).strftime('%d %b')} – {D(plan[1]).strftime('%d %b')}"
        atxt = "" if not actual else f"{D(actual[0]).strftime('%d %b')} – {D(actual[1]).strftime('%d %b')}"
        if not actual and len(plan) == 2 and D(plan[0]) <= ASOF: atxt = "in progress"
        d = delta(item); dtxt = "" if d is None else f"{d:+d}"
        cells = [(str(k), sc["muted"]), (item[1], sc["text"]), (ptxt, sc["text"]), (atxt, sc["muted"] if atxt == "in progress" else sc["text"]),
                 (dtxt, sc["negative"] if (d or 0) > 0 else sc["text"])]
        for (name, w), (val, col) in zip(cols, cells):
            svg.text(cx + (w - 4 if name == "Δ" else 0), ty, val, 11.5 if name != "Activity" else 12, col, 600 if name == "Δ" and (d or 0) > 0 else 400, "end" if name == "Δ" else "start",
                     **({"font_style": "italic"} if val == "in progress" else {}))
            cx += w
        if r[1] in noteidx: circled(svg, sc, M + 28 + tw(item[1], 12) + 14, ty - 4, noteidx[r[1]], [c for c in notes if c[0] == r[1]][0][1] == "risk")
        svg.line(M, y + h, W - M, y + h, sc["line"], stroke_width=0.5)
        draw_marks(svg, sc, S, y, h, item, style="outline", anchors=anchors, key=r[1])
    draw_deps(svg, sc, anchors, rowh, set(view["ids"]))
    asof_line(svg, sc, S, plotTop, plotBot, label=False)
    svg.text(S.x(ASOF), plotTop - 2, "as of", 9.5, sc["warning"], 600, "middle")
    svg.line(M, plotBot, W - M, plotBot, sc["text"], stroke_width=1)
    # footnotes
    fy = plotBot + 30
    if notes:
        svg.text(M, fy, "NOTES", 10, sc["muted"], 600, letter_spacing=".14em"); fy += 18
        for n, (cid, kind, text) in enumerate(notes, 1):
            circled(svg, sc, M + 7, fy - 4, n, kind == "risk"); svg.text(M + 22, fy, f"{ITEMS[cid][1]} — {text}", 11.5, sc["text"]); fy += 20
    legend(svg, sc, M, H - 34, [("baseline", "baseline"), ("plan-outline", "current plan"), ("actual", "actual"), ("missing", "in progress"),
                                ("gate", "gate"), ("holiday", "calendar exception"), ("dep", "dependency")], size=11)
    return svg.render()


PROPOSALS = {"board": board, "sidebar": sidebar, "dossier": dossier}


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    for pname, fn in PROPOSALS.items():
        (out / pname).mkdir(parents=True, exist_ok=True)
        for vid, view in VIEWS.items():
            (out / pname / f"{vid}.svg").write_text(fn(vid, view))
            print(pname, vid)


if __name__ == "__main__":
    main()
