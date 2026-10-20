"""Run chrona render and summarise result. usage: r.py out args..."""
import json, subprocess, sys, os
here = os.path.dirname(os.path.abspath(__file__))
args = [os.path.join(here, "venv/bin/chrona")] + sys.argv[1:]
p = subprocess.run(args, capture_output=True, text=True, cwd=here)
try:
    d = json.loads(p.stdout)
except Exception:
    print("RC", p.returncode, p.stdout[-3000:], p.stderr[-3000:])
    sys.exit()
print("RC", p.returncode, "status", d.get("status"))
for x in d.get("diagnostics", []):
    print("DIAG", x.get("code"), (x.get("message") or "")[:400])
for w in d.get("warnings", []):
    if w.get("severity") != "info":
        print("WARN", w.get("code"), (w.get("message") or "")[:250])
