"""Generate the base plan (week 0) for trial 8 as a Python dict and write YAML.

The weekly revisions are applied by revise.py on top of this structure.
"""
import json, sys, copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent

TEAMS = {
    "platform": ["Aiko Sato", "Ben Ortiz"],
    "backend": ["Chen Wei", "Dana Kim"],
    "mobile": ["Eli Novak", "Fumi Ito"],
    "qa": ["Gita Rao", "Hugo Lind"],
}

# (id, title, team, amount_wd, predecessors, risk)
TASKS = [
    # platform
    ("plat-env", "Provision staging environments", "platform", 5, [], "low"),
    ("plat-ci", "CI pipeline hardening", "platform", 6, ["plat-env"], "medium"),
    ("plat-secrets", "Secrets rotation service", "platform", 4, ["plat-env"], "medium"),
    ("plat-obs", "Observability stack", "platform", 8, ["plat-ci"], "low"),
    ("plat-cdn", "CDN edge config", "platform", 3, ["plat-env"], "low"),
    ("plat-db", "Database cluster upgrade", "platform", 10, ["plat-secrets"], "high"),
    ("plat-queue", "Message queue rollout", "platform", 6, ["plat-db"], "medium"),
    ("plat-flags", "Feature flag service", "platform", 4, ["plat-ci"], "low"),
    ("plat-dr", "Disaster recovery drill", "platform", 3, ["plat-db"], "high"),
    ("plat-cost", "Cost guardrails", "platform", 4, ["plat-obs"], "low"),
    ("plat-perf", "Load test harness", "platform", 6, ["plat-obs", "plat-queue"], "medium"),
    ("plat-prod", "Production cutover prep", "platform", 5, ["plat-dr", "plat-perf"], "high"),
    ("plat-runbook", "Runbooks and on-call", "platform", 4, ["plat-prod"], "low"),
    ("plat-hyper", "Hypercare platform", "platform", 5, ["go-live"], "medium"),
    # backend
    ("be-api-spec", "Checkout API specification", "backend", 5, [], "medium"),
    ("be-auth", "Token auth service", "backend", 8, ["be-api-spec", "plat-secrets"], "high"),
    ("be-cart", "Cart service", "backend", 10, ["be-api-spec"], "medium"),
    ("be-pricing", "Pricing engine", "backend", 12, ["be-cart"], "high"),
    ("be-pay", "Payment gateway adapter", "backend", 10, ["be-auth"], "high"),
    ("be-tax", "Tax calculation", "backend", 6, ["be-pricing"], "medium"),
    ("be-inv", "Inventory reservation", "backend", 7, ["be-cart", "plat-queue"], "medium"),
    ("be-notif", "Order notifications", "backend", 5, ["be-inv"], "low"),
    ("be-refund", "Refund workflow", "backend", 6, ["be-pay"], "medium"),
    ("be-fraud", "Fraud scoring hook", "backend", 5, ["be-pay"], "high"),
    ("be-migr", "Legacy order migration", "backend", 8, ["plat-db"], "high"),
    ("be-api-freeze", "API freeze fixes", "backend", 4, ["api-freeze"], "low"),
    ("be-hyper", "Hypercare backend", "backend", 5, ["go-live"], "low"),
    ("be-docs", "API reference docs", "backend", 4, ["be-tax", "be-refund"], "low"),
    # mobile
    ("mob-design", "Checkout UX design", "mobile", 6, [], "medium"),
    ("mob-kit", "Design system components", "mobile", 8, ["mob-design"], "low"),
    ("mob-cart-ui", "Cart screen", "mobile", 6, ["mob-kit", "api-freeze"], "medium"),
    ("mob-pay-ui", "Payment sheet", "mobile", 8, ["mob-kit", "be-pay"], "high"),
    ("mob-addr", "Address and shipping form", "mobile", 5, ["mob-kit"], "low"),
    ("mob-push", "Push notification opt-in", "mobile", 4, ["be-notif"], "low"),
    ("mob-offline", "Offline cart cache", "mobile", 6, ["mob-cart-ui"], "medium"),
    ("mob-a11y", "Accessibility pass", "mobile", 4, ["mob-pay-ui", "mob-addr"], "medium"),
    ("mob-analytics", "Funnel analytics events", "mobile", 4, ["mob-cart-ui"], "low"),
    ("mob-ios", "iOS release build", "mobile", 3, ["code-freeze"], "medium"),
    ("mob-android", "Android release build", "mobile", 3, ["code-freeze"], "medium"),
    ("mob-store", "Store review submission", "mobile", 5, ["mob-ios", "mob-android"], "high"),
    ("mob-beta", "Beta cohort rollout", "mobile", 5, ["mob-store"], "medium"),
    ("mob-hyper", "Hypercare mobile", "mobile", 5, ["go-live"], "low"),
    # qa
    ("qa-plan", "Test strategy", "qa", 4, [], "low"),
    ("qa-auto", "Automation framework", "qa", 8, ["qa-plan", "plat-ci"], "medium"),
    ("qa-contract", "API contract tests", "qa", 6, ["qa-auto", "be-api-spec"], "low"),
    ("qa-pay", "Payment test matrix", "qa", 7, ["be-pay", "qa-auto"], "high"),
    ("qa-e2e", "End-to-end suite", "qa", 10, ["mob-cart-ui", "qa-auto"], "medium"),
    ("qa-perf", "Performance test run", "qa", 5, ["plat-perf"], "high"),
    ("qa-sec", "Security review", "qa", 6, ["be-auth", "be-pay"], "high"),
    ("qa-a11y", "Accessibility audit", "qa", 3, ["mob-a11y"], "low"),
    ("qa-regress", "Full regression", "qa", 8, ["code-freeze"], "medium"),
    ("qa-uat", "User acceptance testing", "qa", 6, ["qa-regress"], "medium"),
    ("qa-signoff", "Release sign-off", "qa", 2, ["qa-uat", "qa-perf", "qa-sec"], "high"),
    ("qa-hyper", "Hypercare triage", "qa", 5, ["go-live"], "low"),
]

# gates: (id, title, mode, at-or-preds, deadline)
GATES = [
    ("kickoff", "Kickoff", "fixed", "2026-11-02", None),
    ("api-freeze", "API freeze", "derived", ["be-cart", "be-auth"], "2027-01-08"),
    ("code-freeze", "Code freeze", "derived", ["mob-offline", "mob-a11y", "mob-analytics", "mob-push", "be-tax", "be-refund", "be-fraud", "be-inv"], "2027-02-12"),
    ("go-live", "Go-live", "derived", ["qa-signoff", "mob-beta", "plat-runbook", "be-migr"], "2027-03-19"),
    ("steerco", "Steering committee", "fixed", "2027-01-20", None),
]


def base_plan():
    objects = {}
    relations = []
    owner_idx = {t: 0 for t in TEAMS}
    for tid, title, team, amt, preds, risk in TASKS:
        owners = TEAMS[team]
        owner = owners[owner_idx[team] % 2]
        owner_idx[team] += 1
        objects[tid] = {
            "type": "work",
            "title": title,
            "calendar": "office",
            "fields": {"team": team, "risk": risk, "owner": owner},
            "schedule": {"mode": "scheduled", "amount": f"{amt}wd"},
        }
        if not preds:
            preds = ["kickoff"]
        for p in preds:
            relations.append(rel(p, tid))
    for gid, title, mode, val, deadline in GATES:
        o = {"type": "milestone-gate", "title": title, "fields": {"team": "platform" if gid in ("kickoff", "steerco") else "qa", "risk": "high", "owner": "PMO"}}
        if mode == "fixed":
            o["schedule"] = {"mode": "fixed-point", "at": val}
        else:
            o["schedule"] = {"mode": "scheduled-point"}
            for p in val:
                relations.append(rel(p, gid))
        if deadline:
            o["deadline"] = deadline
        objects[gid] = o
    # task deadlines
    objects["be-pay"]["deadline"] = "2026-12-23"
    objects["mob-store"]["deadline"] = "2027-03-01"
    return {
        "version": "timeline/v0.7",
        "project": {"id": "checkout-v2", "title": "Checkout v2 programme", "calendar": "office"},
        "extensions": [{"packageId": "trial8-delivery", "path": "profile.yaml",
                        "revision": "git:0123456789abcdef0123456789abcdef01234567"}],
        "calendars": {"office": {"working_days": ["mon", "tue", "wed", "thu", "fri"],
                                 "exceptions": [{"date": d, "working": False} for d in
                                                ["2026-12-24", "2026-12-25", "2026-12-31", "2027-01-01"]]}},
        "objects": objects,
        "relations": relations,
        "fieldRoles": {"responsible": "team"},
    }


def rel(p, t):
    pe = "at" if p in {g[0] for g in GATES} else "end"
    te = "at" if t in {g[0] for g in GATES} else "start"
    return {"id": f"{p}--{t}", "type": "dependency", "from": {"object": p, "endpoint": pe},
            "to": {"object": t, "endpoint": te}, "lag": "0d"}


if __name__ == "__main__":
    print(json.dumps(base_plan(), indent=1))
