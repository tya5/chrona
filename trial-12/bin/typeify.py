"""Turn the imported (untyped) Project into the typed Atlas plan: the hand edit a user would do."""
import sys, yaml

src, dst = sys.argv[1], sys.argv[2]
p = yaml.safe_load(open(src))
p["extensions"] = [{"packageId": "atlas-delivery", "path": "atlas-profile.yaml",
                    "revision": "git:0123456789abcdef0123456789abcdef01234567"}]
p["entities"] = {
    "del-api": {"type": "atlas.deliverable", "title": "Public API v2"},
    "del-app": {"type": "atlas.deliverable", "title": "Mobile app 3.0"},
    "del-portal": {"type": "atlas.deliverable", "title": "Partner portal"},
    "del-runbook": {"type": "atlas.deliverable", "title": "Operations runbook"},
    "del-report": {"type": "atlas.deliverable", "title": "Launch readiness report"},
}
for oid, o in p["objects"].items():
    if o["type"] == "task":
        o["type"] = "atlas.work"
        f = o["fields"]
        f["external"] = f["external"] == "true"
# keep key order readable
order = ["version", "project", "extensions", "calendars", "entities", "objects", "relations", "fieldRoles"]
out = {k: p[k] for k in order if k in p}
out.update({k: v for k, v in p.items() if k not in out})
yaml.safe_dump(out, open(dst, "w"), sort_keys=False, allow_unicode=True, width=200)
