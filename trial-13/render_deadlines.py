"""Second pass: each bundled preset copied locally with View visibility.deadlines {show: all} added."""
import json, subprocess, sys, shutil, re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CH = str(ROOT / "venv/bin/chrona")
presets = sys.argv[2:] or [p["id"] for p in json.loads(subprocess.check_output([CH, "preset", "list"]))["presets"]]
out = ROOT / "out_dl"
out.mkdir(exist_ok=True)
looks = ROOT / "looks"


def prep(pid):
    d = looks / pid
    if d.exists():
        shutil.rmtree(d)
    subprocess.run([CH, "preset", "copy", pid, "--output", str(d)], check=True, capture_output=True)
    v = d / "view.yaml"
    s = v.read_text()
    s2, n = re.subn(r"^body:\s*\n", lambda m: m.group(0) + "  deadlines: {show: all}\n", s, count=1, flags=re.M)
    assert n == 1, pid
    v.write_text(s2)
    return d / "preset.yaml"


def run(pid):
    preset = prep(pid)
    png = out / f"{pid}.png"
    scene = out / f"{pid}.scene.json"
    for f in (png, scene):
        f.unlink(missing_ok=True)
    cmd = [CH, "render", str(ROOT / "plan/project.yaml"), "--actual", str(ROOT / "plan/actual.yaml"),
           "--snapshot", str(ROOT / "plan/baseline.yaml"), "--forecast", "--preset", str(preset), "--locale", "en-US",
           "-o", str(png), "--emit-scene", str(scene)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode and "E_FORECAST_PRESENTATION_REQUIRED" in r.stdout:
        cmd.remove("--forecast")
        r = subprocess.run(cmd, capture_output=True, text=True)
    (out / f"{pid}.json").write_text(r.stdout)
    return pid, r.returncode


with ThreadPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 4) as ex:
    for pid, rc in ex.map(run, presets):
        print(pid, rc, flush=True)
