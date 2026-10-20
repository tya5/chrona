import json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CH = str(ROOT / "venv/bin/chrona")
presets = sys.argv[2:] or [p["id"] for p in json.loads(subprocess.check_output([CH, "preset", "list"]))["presets"]]
out = ROOT / "out"
out.mkdir(exist_ok=True)


def run(pid):
    png = out / f"{pid}.png"
    scene = out / f"{pid}.scene.json"
    for f in (png, scene):
        f.unlink(missing_ok=True)
    cmd = [CH, "render", str(ROOT / "plan/project.yaml"), "--actual", str(ROOT / "plan/actual.yaml"),
           "--snapshot", str(ROOT / "plan/baseline.yaml"), "--forecast", "--preset", pid, "--locale", "en-US",
           "-o", str(png), "--emit-scene", str(scene)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode and "E_FORECAST_PRESENTATION_REQUIRED" in r.stdout:
        cmd.remove("--forecast")
        (out / f"{pid}.noforecast").write_text("forecast rejected: E_FORECAST_PRESENTATION_REQUIRED\n")
        r = subprocess.run(cmd, capture_output=True, text=True)
    (out / f"{pid}.json").write_text(r.stdout)
    (out / f"{pid}.stderr.txt").write_text(r.stderr)
    return pid, r.returncode


with ThreadPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 4) as ex:
    for pid, rc in ex.map(run, presets):
        print(pid, rc, flush=True)
