import json, subprocess, sys
from pathlib import Path
R = Path(__file__).resolve().parent
C = str(R / ".venv/bin/chrona")
sys.path.insert(0, str(R))
from gen_plan import base_plan
w0 = R / "w0"; w0.mkdir(exist_ok=True)
(w0 / "project.yaml").write_text(json.dumps(base_plan(), indent=1))
print(subprocess.run([C, "validate", str(w0 / "project.yaml")], capture_output=True, text=True).stdout[:2000])
r = subprocess.run([C, "schedule", str(w0 / "project.yaml")], capture_output=True, text=True)
d = json.loads(r.stdout)
print(d["status"], json.dumps(d.get("diagnostics"))[:1500], json.dumps(d.get("warnings"))[:1500])
p = d.get("placements", {})
print(len(p), {k: p.get(k) for k in ["kickoff", "api-freeze", "code-freeze", "go-live", "steerco", "be-pay"]})
