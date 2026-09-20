"""Explicit, all-or-nothing v0.1 Date-only to v0.2 DateTime migration."""
from __future__ import annotations
from copy import deepcopy
from datetime import date
from typing import Any
from chrona.core.validation import validate_project

class MigrationError(ValueError):
    def __init__(self, diagnostic: str): super().__init__(diagnostic); self.diagnostic=diagnostic

def migrate_v1_to_v2(project: dict[str, Any], source_revision: str, zone_policy: dict[str, str]) -> dict[str, Any]:
    if project.get("version") != "timeline/v0.1": raise MigrationError("E_MIGRATION_SOURCE")
    if validate_project(project): raise MigrationError("E_MIGRATION_SOURCE")
    if set(project) - {"version","project","objects","relations"}: raise MigrationError("E_MIGRATION_UNSUPPORTED")
    if zone_policy.get("localTime") in {"00:00","00:00:00"} or not {"zone","localTime","disambiguation"} <= set(zone_policy): raise MigrationError("E_MIGRATION_POLICY")
    def dt(value):
        try: return {"local": f"{date.fromisoformat(str(value)).isoformat()}T{zone_policy['localTime']}", "zone":zone_policy["zone"], "disambiguation":zone_policy["disambiguation"]}
        except Exception as exc: raise MigrationError("E_MIGRATION_DATE") from exc
    objects={}
    for key,item in project.get("objects",{}).items():
        if set(item)-{"type","title","schedule"}: raise MigrationError("E_MIGRATION_UNSUPPORTED")
        raw=item["schedule"]; mode=raw.get("mode")
        if mode=="fixed": schedule={"mode":"fixed", **({"at":dt(raw["at"])} if "at" in raw else {"start":dt(raw["start"]),"end":dt(raw["end"])})}
        elif mode=="scheduled":
            if set(raw)-{"mode","amount","anchor"} or "anchor" not in raw or raw["amount"][-2:]=="wd" or not raw["amount"].endswith(("d","w")): raise MigrationError("E_MIGRATION_UNSUPPORTED")
            a,n=raw["amount"][:-1],raw["amount"][-1]; schedule={"mode":"scheduled","amount":{"kind":"calendarPeriod","value":f"{a}{n}"},"anchor":{k:dt(v) for k,v in raw["anchor"].items()}}
        else: raise MigrationError("E_MIGRATION_UNSUPPORTED")
        objects[key]={k:v for k,v in item.items() if k in {"type","title"}}|{"schedule":schedule}
    relations=[]
    for rel in project.get("relations",[]):
        lag=rel.get("lag","0d")
        if not isinstance(lag,str) or lag.endswith("wd") or not lag.endswith(("d","w")): raise MigrationError("E_MIGRATION_UNSUPPORTED")
        relations.append({"type":"dependency","from":deepcopy(rel["from"]),"to":deepcopy(rel["to"]),"lag":{"kind":"calendarPeriod","value":lag}})
    return {"version":"timeline/v0.2","temporalProfile":"datetime-v0.2","project":deepcopy(project["project"]),"migration":{"sourceRevision":source_revision,"sourceFormat":"timeline/v0.1","zonePolicy":deepcopy(zone_policy)},"objects":objects,"relations":relations}

def downgrade_v2_to_v1(project: dict[str, Any]) -> None:
    if project.get("version")=="timeline/v0.2": raise MigrationError("E_MIGRATION_DOWNGRADE")
