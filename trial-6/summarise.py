"""Print a one-line summary of a chrona JSON result: status, non-info warning codes, diagnostics."""
import json
import sys

path, rc, name = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    d = json.load(open(path))
except Exception as exc:  # noqa: BLE001
    print(name, rc, "unparseable", exc, open(path).read()[:300])
    raise SystemExit
warn = {}
for w in d.get("warnings", []):
    if w.get("severity") != "info":
        warn[w["code"]] = warn.get(w["code"], 0) + w.get("count", 1)
diag = [(x.get("code"), x.get("message", "")[:160]) for x in d.get("diagnostics", [])]
print(name, rc, d.get("status"), warn, diag)
