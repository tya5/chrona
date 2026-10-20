"""Render matrix runner: times every render, keeps stdout JSON, emits Scene, chains --previous-scene.

usage: render.py WEEKS SLIDES PRESETS LOCALES [--png] [--force]
  each arg comma-separated; 'all' for everything.
"""
import json, os, subprocess, sys, time

T = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CH = f"{T}/venv/bin/chrona"
SLIDES = ["exec", "focus", "network", "compare"]
PRESETS = ["default", "target-b", "mission-light", "yuya"]
LOCALES = ["en-US", "ja-JP"]
VIEW = {"exec": "exec-summary.yaml", "focus": "focus.yaml", "network": "network.yaml", "compare": "compare.yaml"}


def args_for(week, slide, preset, locale, fmt):
    out = f"{T}/out/w{week}/{slide}.{preset}.{locale}"
    a = [CH, "render", f"{T}/w{week}/project.yaml", "--view", f"{T}/views/{VIEW[slide]}",
         "--locale", locale, "--output", f"{out}.{fmt}"]
    if preset != "default":
        a += ["--preset", preset]
    if slide != "network":
        a += ["--actual", f"{T}/w{week}/actual.yaml"]
    if slide == "network":
        a += ["--layout", f"{T}/views/network-layout.yaml", "--viewport", "1600x900"]
    if slide == "compare":
        a += ["--snapshot", f"{T}/w0/project.yaml", "--forecast"]
    if slide == "focus":
        a += ["--snapshot", f"{T}/w0/project.yaml"]
    return out, a


def main():
    sel = [s.split(",") for s in sys.argv[1:5]]
    full = [list(range(4)), SLIDES, PRESETS, LOCALES]
    sel = [full[i] if s == ["all"] else ([int(x) for x in s] if i == 0 else s) for i, s in enumerate(sel)]
    fmt = "png" if "--png" in sys.argv else "svg"
    log = open(f"{T}/out/timings.tsv", "a")
    for week in sel[0]:
        os.makedirs(f"{T}/out/w{week}", exist_ok=True)
        for slide in sel[1]:
            for preset in sel[2]:
                for locale in sel[3]:
                    out, a = args_for(week, slide, preset, locale, fmt)
                    scene = f"{out}.scene.json"
                    if fmt == "svg" or not os.path.exists(scene):
                        if os.path.exists(scene):
                            os.remove(scene)
                        a += ["--emit-scene", scene]
                    prev = f"{T}/out/w{week-1}/{slide}.{preset}.{locale}.scene.json"
                    if week > 0 and os.path.exists(prev):
                        a += ["--previous-scene", prev]
                    t0 = time.time()
                    r = subprocess.run(a, capture_output=True, text=True)
                    dt = time.time() - t0
                    open(f"{out}.{fmt}.result.json", "w").write(r.stdout)
                    if r.stderr.strip():
                        open(f"{out}.{fmt}.stderr.txt", "w").write(r.stderr)
                    try:
                        d = json.loads(r.stdout)
                        status = d.get("status")
                        codes = sorted({x.get("code") for x in d.get("diagnostics", []) + d.get("warnings", [])})
                    except Exception:
                        status, codes = f"exit{r.returncode}", [r.stdout[:200] + r.stderr[-300:]]
                    line = f"w{week}\t{slide}\t{preset}\t{locale}\t{fmt}\t{dt:.1f}s\t{status}\t{' '.join(map(str, codes))}"
                    print(line, flush=True)
                    log.write(line + "\n"); log.flush()


main()
