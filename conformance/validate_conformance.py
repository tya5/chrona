#!/usr/bin/env python3
"""Reference evaluator for Core v0.1 Date temporal conformance fixtures."""
from datetime import date, timedelta
import calendar, re, yaml
from pathlib import Path

def parse_date(v):
    if isinstance(v, date): return v
    return date.fromisoformat(str(v))

def clamp_month(d, months):
    total = d.year * 12 + (d.month - 1) + months
    y, m0 = divmod(total, 12)
    m = m0 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, day)

def apply_calendar_period(d, amount, direction=1):
    parts = re.findall(r'(-?\d+)(mo|y|w|d)', amount)
    out = d
    for n,u in parts:
        n=int(n)*direction
        if u=="y": out=clamp_month(out,n*12)
        elif u=="mo": out=clamp_month(out,n)
        elif u=="w": out += timedelta(days=7*n)
        elif u=="d": out += timedelta(days=n)
    return out

def is_working(d, cal):
    exceptions={parse_date(x["date"]):x["working"] for x in cal.get("exceptions",[])}
    if d in exceptions: return exceptions[d]
    names=["mon","tue","wed","thu","fri","sat","sun"]
    return names[d.weekday()] in cal["working_days"]

def apply_work(d, n, cal):
    if n==0: return d
    step=1 if n>0 else -1
    left=abs(n); out=d
    while left:
        out += timedelta(days=step)
        if is_working(out,cal): left-=1
    return out

def main():
    path=Path(__file__).with_name("conformance-v0.1.yaml")
    data=yaml.safe_load(path.read_text(encoding="utf-8"))
    failures=[]
    for case in data["temporal"]["calendar_period"]:
        if "input" not in case: continue
        i=case["input"]; d=parse_date(i["date"])
        direction=-1 if i["op"]=="retreat" else 1
        got=apply_calendar_period(d,str(i["amount"]),direction)
        if got != parse_date(case["expected"]):
            failures.append((case["name"],str(got),str(case["expected"])))
    wp=data["temporal"]["work_period"]; cal=wp["calendar"]
    for case in wp["cases"]:
        if "input" not in case: continue
        i=case["input"]; n=int(str(i["amount"]).replace("wd",""))
        if i["op"]=="retreat": n=-abs(n)
        got=apply_work(parse_date(i["date"]),n,cal)
        if got != parse_date(case["expected"]):
            failures.append((case["name"],str(got),str(case["expected"])))
    if failures:
        for x in failures: print("FAIL",x)
        raise SystemExit(1)
    print("PASS temporal reference fixtures")

if __name__=="__main__":
    main()
