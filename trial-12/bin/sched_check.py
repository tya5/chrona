import json, os, subprocess
T = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for k in range(4):
    out = subprocess.run([f"{T}/venv/bin/chrona", "schedule", f"{T}/w{k}/project.yaml"], capture_output=True, text=True).stdout
    open(f"{T}/w{k}/schedule.json", "w").write(out)
    d = json.loads(out); p = d["placements"]
    print(f"w{k}", p["build-complete"], p["launch"], p.get("bui-pay-3"), p.get("bui-web-hotfix"),
          [w["message"] for w in d["warnings"]])
