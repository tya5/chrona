"""Render every design every week. usage: render.py VARIANT [design ...]
VARIANT 'plain' = no hint; 'hint' = --previous-scene from previous week's hint render."""
import json, subprocess, sys, time
from pathlib import Path

R = Path(__file__).resolve().parent
C = str(R / ".venv/bin/chrona")
DESIGNS = {"executive-light": False, "target-b": True, "marquee": True}
variant = sys.argv[1]
designs = sys.argv[2:] or list(DESIGNS)
out = R / "out" / variant
out.mkdir(parents=True, exist_ok=True)
log = []
for d in designs:
    for w in range(1, 6):
        wd = R / f"w{w}"
        stem = out / f"{d}-w{w}"
        for suf in (".png", ".scene.json", ".svg"):
            p = Path(str(stem) + suf)
            if p.exists():
                p.unlink()
        args = [C, "render", str(wd / "project.yaml"), "--preset", str(R / "looks" / d / "preset.yaml"),
                "--actual", str(wd / "actual.yaml")]
        if DESIGNS[d] or w == 5:
            args += ["--snapshot", str(wd / "baseline.yaml")]
        if w == 5:
            args += ["--forecast"]
        if variant == "hint" and w > 1:
            args += ["--previous-scene", str(out / f"{d}-w{w-1}.scene.json")]
        args += ["--output", str(stem) + ".png", "--emit-scene", str(stem) + ".scene.json"]
        t = time.perf_counter()
        r = subprocess.run(args, capture_output=True, text=True)
        dt = time.perf_counter() - t
        try:
            res = json.loads(r.stdout)
        except Exception:
            res = {"status": "unparsable", "raw": r.stdout[-2000:]}
        rec = {"design": d, "week": w, "rc": r.returncode, "seconds": round(dt, 2), "status": res.get("status"),
               "warnings": res.get("warnings", []), "diagnostics": res.get("diagnostics", []),
               "stderr": r.stderr[-3000:]}
        # SVG too, for inspection (not timed in the table)
        if False:
            a2 = [x for x in args]
            i = a2.index("--output"); a2[i + 1] = str(stem) + ".svg"
            j = a2.index("--emit-scene"); del a2[j:j + 2]
            t2 = time.perf_counter(); subprocess.run(a2, capture_output=True, text=True); rec["svg_seconds"] = round(time.perf_counter() - t2, 2)
        log.append(rec)
        print(d, w, rec["rc"], rec["status"], rec["seconds"], [x.get("code") for x in rec["warnings"]],
              [x.get("code") + ":" + x.get("message", "")[:200] for x in rec["diagnostics"]], flush=True)
(out / f"log-{'-'.join(designs)}.json").write_text(json.dumps(log, indent=1))
