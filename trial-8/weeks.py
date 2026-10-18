"""Build weeks w1..w5: project.yaml, actual.yaml (cumulative, appended), baseline.yaml (= w1 plan)."""
import copy, hashlib, json, shutil, subprocess, sys
from datetime import date, timedelta
from pathlib import Path

R = Path(__file__).resolve().parent
C = str(R / ".venv/bin/chrona")
sys.path.insert(0, str(R))
from gen_plan import base_plan, rel

AS_OF = {1: "2026-11-16", 2: "2026-11-23", 3: "2026-11-30", 4: "2026-12-07", 5: "2026-12-14"}


def h(s, n):
    return int(hashlib.sha256(s.encode()).hexdigest(), 16) % n


def plan_for(week):
    p = base_plan()
    o, rels = p["objects"], p["relations"]
    # tighter promises so deadlines matter
    o["api-freeze"]["deadline"] = "2026-11-27"
    o["go-live"]["deadline"] = "2027-01-29"
    if week >= 2:  # one task slips two weeks (8wd -> 18wd)
        o["plat-obs"]["schedule"]["amount"] = "18wd"
    if week >= 3:  # two added, one removed
        o["be-ratelimit"] = {"type": "work", "title": "Rate limiting", "calendar": "office",
                             "fields": {"team": "backend", "risk": "medium", "owner": "Dana Kim"},
                             "schedule": {"mode": "scheduled", "amount": "4wd"}}
        rels.append(rel("be-auth", "be-ratelimit"))
        rels.append(rel("be-ratelimit", "code-freeze"))
        o["mob-deeplink"] = {"type": "work", "title": "Deep link handling", "calendar": "office",
                             "fields": {"team": "mobile", "risk": "low", "owner": "Fumi Ito"},
                             "schedule": {"mode": "scheduled", "amount": "3wd"}}
        rels.append(rel("mob-kit", "mob-deeplink"))
        rels.append(rel("mob-deeplink", "code-freeze"))
        del o["plat-cost"]
        rels[:] = [r for r in rels if "plat-cost" not in (r["from"]["object"], r["to"]["object"])]
    if week >= 4:  # dependency changed, milestone moved
        rels[:] = [r for r in rels if r["id"] != "mob-cart-ui--qa-e2e"]
        rels.append(rel("mob-offline", "qa-e2e"))
        o["steerco"]["schedule"]["at"] = "2027-01-13"
    return p


def schedule(path):
    r = subprocess.run([C, "schedule", str(path)], capture_output=True, text=True)
    d = json.loads(r.stdout)
    assert d["status"] == "ok", d
    return d


def d2(s):
    return date.fromisoformat(s)


def main():
    obs = []          # cumulative observation list
    last = {}         # object -> last actual dict
    seq = {}
    for w in range(1, 6):
        wd = R / f"w{w}"
        wd.mkdir(exist_ok=True)
        shutil.copy(R / "profile.yaml", wd / "profile.yaml")
        plan = plan_for(w)
        (wd / "project.yaml").write_text(json.dumps(plan, indent=1))
        sch = schedule(wd / "project.yaml")
        (wd / "schedule.json").write_text(json.dumps(sch, indent=1))
        asof = d2(AS_OF[w])
        for oid, pl in sch["placements"].items():
            if oid not in plan["objects"]:
                continue
            prev = last.get(oid)
            if "at" in pl:
                if d2(pl["at"]) <= asof and prev is None:
                    new = {"at": pl["at"]}
                else:
                    continue
            else:
                s, e = d2(pl["start"]), d2(pl["end"])
                if s >= asof:
                    continue
                if prev and "finish" in prev:
                    continue
                st = prev["start"] if prev else (s + timedelta(days=h(oid + "s", 2))).isoformat()
                if d2(st) >= asof:
                    continue
                fin = e + timedelta(days=h(oid + "f", 4) - 1)
                if fin <= asof:
                    new = {"start": st, "finish": max(fin, d2(st) + timedelta(days=1)).isoformat(), "progress": 1}
                else:
                    frac = (asof - d2(st)).days / max(1, (e - d2(st)).days)
                    new = {"start": st, "openUntil": "asOf", "progress": round(min(0.95, max(0.05, frac * 0.9)), 2)}
            if new != prev:
                seq[oid] = seq.get(oid, 0) + 1
                obs.append({"id": f"{oid}-{seq[oid]}", "sequence": seq[oid], "projectObjectId": oid, "actual": new})
                last[oid] = new
        actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "checkout-observed",
                  "body": {"asOf": AS_OF[w], "observations": [x for x in obs if x["projectObjectId"] in plan["objects"]]}}
        (wd / "actual.yaml").write_text(json.dumps(actual, indent=1))
        shutil.copy(R / "w1" / "project.yaml", wd / "baseline.yaml")
        r = subprocess.run([C, "validate", str(wd / "actual.yaml")], capture_output=True, text=True)
        print(w, AS_OF[w], len(plan["objects"]), "objs", len(actual["body"]["observations"]), "obs", r.stdout.strip()[:200],
              "warn", [x["code"] for x in sch["warnings"]], "go-live", sch["placements"]["go-live"])


main()
