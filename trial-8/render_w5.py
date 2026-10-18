"""Week 5 re-render after E_FORECAST_BASELINE_UNAVAILABLE.
w5  = baseline vs current (--snapshot, no --forecast), all designs (exec draws no baseline)
w5f = forecast vs current plan (--forecast, no --snapshot)
usage: render_w5.py VARIANT"""
import json, subprocess, sys, time
from pathlib import Path
R = Path(__file__).resolve().parent
C = str(R / ".venv/bin/chrona")
variant = sys.argv[1]
out = R / "out" / variant
wd = R / "w5"
for d in ["executive-light", "target-b", "marquee"]:
    logf = out / f"log-{d}.json"
    if logf.exists():
        log = json.loads(logf.read_text())
    else:
        allf = json.loads((out / "log-executive-light-target-b-marquee.json").read_text())
        log = [x for x in allf if x["design"] == d]
    log = [x for x in log if x["week"] != 5]
    for tag, extra in (("w5", ["--snapshot", str(wd / "baseline.yaml")]), ("w5f", ["--forecast"])):
        stem = out / f"{d}-{tag}"
        for suf in (".png", ".scene.json"):
            p = Path(str(stem) + suf)
            if p.exists():
                p.unlink()
        args = [C, "render", str(wd / "project.yaml"), "--preset", str(R / "looks" / d / "preset.yaml"),
                "--actual", str(wd / "actual.yaml")] + extra
        if variant == "hint":
            args += ["--previous-scene", str(out / f"{d}-w4.scene.json")]
        args += ["--output", str(stem) + ".png", "--emit-scene", str(stem) + ".scene.json"]
        t = time.perf_counter(); r = subprocess.run(args, capture_output=True, text=True); dt = time.perf_counter() - t
        res = json.loads(r.stdout) if r.stdout.strip().startswith("{") else {"status": "unparsable"}
        rec = {"design": d, "week": 5 if tag == "w5" else "5f", "rc": r.returncode, "seconds": round(dt, 2), "status": res.get("status"),
               "warnings": res.get("warnings", []), "diagnostics": res.get("diagnostics", []), "stderr": r.stderr[-3000:]}
        log.append(rec)
        print(d, tag, r.returncode, res.get("status"), round(dt, 2), [x.get("code") for x in rec["warnings"]], rec["diagnostics"][:2], flush=True)
    logf.write_text(json.dumps(log, indent=1))
old = out / "log-executive-light-target-b-marquee.json"
if old.exists():
    old.rename(out / "log-all-original.json.bak")
