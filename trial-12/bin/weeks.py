"""Build the weekly revisions (w1..w3) and cumulative Actual Sets (w0..w3).

w1 (as-of 2026-12-14): add bui-web-hotfix (compiled from w1/addition.chrona), deliverable added in YAML.
w2 (as-of 2026-12-21): remove lau-mob-3 (rewire lau-mob-2 -> lau-mob-4).
w3 (as-of 2026-12-28): slip dependency bui-pay-2 -> bui-pay-3 by +5wd.
"""
import copy, datetime as dt, hashlib, json, os, shutil, subprocess, sys, yaml

T = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CH = os.path.join(T, "venv/bin/chrona")
ASOF = {0: "2026-12-07", 1: "2026-12-14", 2: "2026-12-21", 3: "2026-12-28"}


def load(p):
    return yaml.safe_load(open(p))


def dump(d, p):
    yaml.safe_dump(d, open(p, "w"), sort_keys=False, allow_unicode=True, width=200)


def schedule(p):
    out = subprocess.run([CH, "schedule", p], capture_output=True, text=True)
    d = json.loads(out.stdout)
    assert d["status"] == "ok", out.stdout[:2000]
    return d["placements"]


def build_projects():
    base = load(f"{T}/w0/project.yaml")
    w1 = copy.deepcopy(base)
    add = load(f"{T}/w1/addition.yaml")["objects"]["bui-web-hotfix"]
    add["parent"] = "ws-build-web"
    add["fields"]["deliverable"] = "del-portal"
    w1["objects"]["bui-web-hotfix"] = add
    w1["relations"].append({"id": "bui-web-hotfix-build-complete", "type": "dependency",
                            "from": {"object": "bui-web-hotfix", "endpoint": "end"},
                            "to": {"object": "build-complete", "endpoint": "at"}, "lag": "0d"})
    w2 = copy.deepcopy(w1)
    del w2["objects"]["lau-mob-3"]
    w2["relations"] = [r for r in w2["relations"]
                       if r["from"]["object"] != "lau-mob-3" and r["to"]["object"] != "lau-mob-3"]
    w2["relations"].append({"id": "lau-mob-2-lau-mob-4", "type": "dependency",
                            "from": {"object": "lau-mob-2", "endpoint": "end"},
                            "to": {"object": "lau-mob-4", "endpoint": "start"}, "lag": "0d"})
    w3 = copy.deepcopy(w2)
    for r in w3["relations"]:
        if r["id"] == "bui-pay-2-bui-pay-3":
            r["lag"] = "5wd"
            break
    else:
        raise SystemExit("relation not found")
    for k, p in ((1, w1), (2, w2), (3, w3)):
        os.makedirs(f"{T}/w{k}", exist_ok=True)
        shutil.copy(f"{T}/w0/atlas-profile.yaml", f"{T}/w{k}/atlas-profile.yaml")
        dump(p, f"{T}/w{k}/project.yaml")


def slip(oid):
    return [0, 0, 0, 1, 2, 3][int(hashlib.sha1(oid.encode()).hexdigest(), 16) % 6]


def iso(d):
    return d.isoformat()


def build_actuals():
    prev_obs = []
    latest = {}
    for k in range(4):
        asof = dt.date.fromisoformat(ASOF[k])
        proj = load(f"{T}/w{k}/project.yaml")
        pl = schedule(f"{T}/w{k}/project.yaml")
        obs = list(prev_obs)
        for oid, o in proj["objects"].items():
            if o["type"] == "group" or oid not in pl:
                continue
            p = pl[oid]
            if "at" in p:
                at = dt.date.fromisoformat(p["at"])
                if at <= asof:
                    actual = {"at": iso(at)}
                else:
                    continue
            else:
                s = dt.date.fromisoformat(p["start"]); e = dt.date.fromisoformat(p["end"])
                if s > asof:
                    continue
                fin = e + dt.timedelta(days=slip(oid))
                if fin <= asof:
                    actual = {"start": iso(s), "finish": iso(fin), "progress": 1}
                else:
                    frac = round(min(0.95, (asof - s).days / max(1, (e - s).days)), 2)
                    actual = {"start": iso(s), "openUntil": "asOf", "progress": frac}
            if latest.get(oid, (None, None))[1] == actual:
                continue
            seq = latest.get(oid, (0, None))[0] + 1
            latest[oid] = (seq, actual)
            obs.append({"id": f"{oid}-{seq}", "sequence": seq, "projectObjectId": oid, "actual": actual})
        # drop observations of removed objects (a real office would keep them; chrona may warn)
        doc = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "atlas-observed",
               "body": {"asOf": ASOF[k], "observations": obs}}
        dump(doc, f"{T}/w{k}/actual.yaml")
        prev_obs = obs
        print(f"w{k}: {len(obs)} observations")


if __name__ == "__main__":
    build_projects()
    build_actuals()
