"""M14 typed review projection; rendering remains a separate adapter."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from html import escape
from typing import Any


@dataclass(frozen=True)
class ReviewItem:
    object_id: str
    title: str
    source_type: str
    planned: dict[str, date]
    actual: dict[str, date | float] | None
    finish_delta: int | None
    roles: tuple[str, ...]
    group_id: str = ""
    group_label: str = ""
    fields: dict[str, Any] | None = None


@dataclass(frozen=True)
class ReviewProjection:
    items: tuple[ReviewItem, ...]
    window: tuple[date, date]
    unmatched_actual_ids: tuple[str, ...]
    diagnostics: tuple[str, ...]


def build_review_projection(project: dict[str, Any], placements: dict[str, dict[str, date]], view: dict[str, Any], actual_set: dict[str, Any] | None, style: dict[str, Any], theme: dict[str, Any]) -> ReviewProjection:
    """Derive review facts without modifying Project, schedule, or Actual inputs."""
    body = view["body"]
    comparison = body["comparison"]
    if comparison["actual"] == "required" and actual_set is None:
        raise ValueError("E_ACTUAL_REQUIRED")
    if not theme.get("body", {}).get("roles"):
        raise ValueError("E_THEME_ROLES")
    observations = (actual_set or {}).get("body", actual_set or {}).get("observations", [])
    latest: dict[str, dict[str, Any]] = {}
    unmatched: list[str] = []
    for observation in observations:
        object_id = observation.get("projectObjectId")
        if object_id not in placements:
            unmatched.append(observation["id"])
            continue
        if object_id not in latest or observation["sequence"] > latest[object_id]["sequence"]:
            latest[object_id] = observation
    include = body["selection"]["include"]
    ids = set(include.get("ids", placements))
    allowed_types = set(include.get("types", ("span", "point")))
    rows: list[ReviewItem] = []
    for object_id, planned in placements.items():
        source_type = "point" if "at" in planned else "span"
        if object_id not in ids or source_type not in allowed_types:
            continue
        raw_actual = latest.get(object_id, {}).get("actual")
        actual = {key: _date_or_number(value) for key, value in raw_actual.items()} if raw_actual else None
        finish_delta = None
        if actual and "finish" in actual and "end" in planned:
            finish_delta = (actual["finish"] - planned["end"]).days  # type: ignore[operator]
        roles = _roles(style, source_type, actual, finish_delta)
        grouping=body.get("grouping",{"by":"none","missing":"ungrouped"}); group_id=_group_id(project,object_id,source_type,grouping); group_label=str(project.get("entities",{}).get(group_id,{}).get("title",group_id))
        rows.append(ReviewItem(object_id, str(project["objects"][object_id].get("title", object_id)), source_type, planned, actual, finish_delta, roles, group_id, group_label, dict(project["objects"][object_id].get("fields", {}))))
    key = body["ordering"]["by"]
    rows.sort(key=lambda item: (item.group_id, item.planned.get("start", item.planned.get("at")), item.object_id) if key == "plannedStart" else (item.group_id,item.object_id))
    dates = [value for item in rows for value in item.planned.values()]
    margin = body["window"].get("marginDays", 0)
    start, end = min(dates), max(dates)
    return ReviewProjection(tuple(rows), (date.fromordinal(start.toordinal() - margin), date.fromordinal(end.toordinal() + margin)), tuple(sorted(unmatched)), tuple("E_ACTUAL_UNMATCHED" for _ in unmatched))

def _group_id(project:dict[str,Any], object_id:str, source_type:str, grouping:dict[str,Any])->str:
    if grouping["by"]=="none": return ""
    if grouping["by"]=="objectType": return source_type
    return str(project["objects"][object_id].get("fields",{}).get(grouping["field"],grouping["missing"]))


def _date_or_number(value: Any) -> date | float:
    if isinstance(value, date):
        return value
    return date.fromisoformat(value) if isinstance(value, str) else float(value)


def _roles(style: dict[str, Any], source_type: str, actual: dict[str, Any] | None, finish_delta: int | None) -> tuple[str, ...]:
    facets = {"planned"}
    if actual: facets.add("actual")
    if finish_delta is not None: facets.add("finishDelta")
    if not actual: facets.add("missingActual")
    roles: list[str] = []
    for rule in style.get("body", {}).get("rules", []):
        when = rule["when"]
        category = "behind" if (finish_delta or 0) > 0 else "on-track"
        if when.get("facet") in facets and ("sourceType" not in when or when["sourceType"] == source_type) and ("comparisonCategory" not in when or when["comparisonCategory"] == category):
            roles.extend(rule["addRoles"])
    return tuple(dict.fromkeys(roles))


def render_review_svg(title: str, projection: ReviewProjection, theme: dict[str, Any], capabilities: set[str], profile:dict[str,Any]|None=None) -> str:
    """Render the completed review projection with source metadata and text alternatives."""
    required = {"sourceMetadata", "accessibleText", "semanticRoles", "marker"}
    if not required.issubset(capabilities):
        raise ValueError("E_OUTPUT_CAPABILITY_MISSING")
    start, end = projection.window
    left, top, day, row = 220, 96, 12, 56
    group_profile=(profile or {}).get("groupPresentation",{"mode":"none","gapRows":0}); extra=sum(1+group_profile["gapRows"] for a,b in zip(projection.items,projection.items[1:]) if a.group_id!=b.group_id); width, height = max(960, left + (end - start).days * day + 80), top + (len(projection.items)+extra) * row + 100
    colors = _theme_colors(theme)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img" aria-labelledby="title desc">',f'<title id="title">{escape(title)} review</title>',f'<desc id="desc">Planned and Actual engineering timeline review; {len(projection.unmatched_actual_ids)} unmatched Actual observations.</desc>', '<defs><pattern id="missing" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="#6b7280" stroke-width="2"/></pattern></defs>',f'<rect width="{width}" height="{height}" fill="{colors["background"]}"/>',f'<text x="24" y="34" font-family="system-ui" font-size="20" font-weight="700">{escape(title)} — Plan / Actual Review</text>']
    cursor = start
    while cursor <= end:
        x=left+(cursor-start).days*day
        if cursor.day <= 7: parts += [f'<line x1="{x}" y1="60" x2="{x}" y2="{height-30}" stroke="#ddd"/>',f'<text x="{x+3}" y="55" font-family="system-ui" font-size="11">{cursor:%Y-%m}</text>']
        cursor=date.fromordinal(cursor.toordinal()+7)
    y=top-row
    previous=None
    for item in projection.items:
        if item.group_id!=previous:
            if previous is not None: y+=row*(1+group_profile["gapRows"]); parts.append(f'<line data-purpose="group-separator" x1="24" y1="{y-row//2}" x2="{width-24}" y2="{y-row//2}" stroke="#9ca3af"/>')
            if group_profile["mode"] in {"header-and-separator","band"}: parts.append(f'<text data-purpose="group-header" x="24" y="{y+row//2}" font-family="system-ui" font-size="14" font-weight="700">{escape(item.group_label)}</text>')
            y+=row; previous=item.group_id
        y+=row; parts.append(f'<text x="24" y="{y+5}" font-family="system-ui" font-size="13">{escape(item.title)}</text>')
        attrs=f'data-scene-id="item:{item.object_id}:planned" data-source-ref="{item.object_id}" data-purpose="planned"'
        if item.source_type=="point":
            x=left+(item.planned["at"]-start).days*day; parts.append(f'<path {attrs} d="M{x} {y-8} L{x+8} {y} L{x} {y+8} L{x-8} {y}Z" fill="{colors["planned"]}"/>')
        else:
            x=left+(item.planned["start"]-start).days*day; w=max(4,(item.planned["end"]-item.planned["start"]).days*day); parts.append(f'<rect {attrs} x="{x}" y="{y-12}" width="{w}" height="12" rx="2" fill="{colors["planned"]}"/>')
        if item.actual:
            if "finish" in item.actual and item.source_type=="span":
                ax=left+((item.actual.get("start",item.planned["start"])-start).days)*day; aw=max(4,(item.actual["finish"]-item.actual.get("start",item.planned["start"])).days*day); parts.append(f'<rect data-scene-id="item:{item.object_id}:actual" data-source-ref="{item.object_id}" data-purpose="actual" x="{ax}" y="{y+4}" width="{aw}" height="9" rx="2" fill="{colors["actual"]}"/>')
            if item.finish_delta is not None: parts.append(f'<text data-scene-id="item:{item.object_id}:variance" data-source-ref="{item.object_id}" data-purpose="variance" x="{left+(item.planned.get("end",item.planned.get("at"))-start).days*day+5}" y="{y+14}" font-family="system-ui" font-size="11" fill="{colors["behind"]}">{item.finish_delta:+d}d</text>')
        else: parts.append(f'<rect data-scene-id="item:{item.object_id}:missing" data-source-ref="{item.object_id}" data-purpose="actual" x="{left+(item.planned.get("start",item.planned.get("at"))-start).days*day}" y="{y+4}" width="18" height="9" fill="url(#missing)"/><text x="{left+(item.planned.get("start",item.planned.get("at"))-start).days*day+22}" y="{y+13}" font-family="system-ui" font-size="10">actual missing</text>')
    if projection.unmatched_actual_ids: parts.append(f'<text x="24" y="{height-24}" font-family="system-ui" font-size="11" fill="#b45309">Unmatched Actual: {escape(", ".join(projection.unmatched_actual_ids))}</text>')
    return "\n".join(parts+["</svg>"])+"\n"


def render_table_timeline_svg(title: str, projection: ReviewProjection, project: dict[str, Any], view: dict[str, Any], theme: dict[str, Any], capabilities: set[str], profile: dict[str, Any], slots: dict[str, Any] | None = None) -> str:
    """Generic M15/M16 adapter. All composition comes from supplied resources."""
    required={"sourceMetadata","accessibleText","semanticRoles","marker","tableSemantics","hierarchicalAxis"}
    if not required.issubset(capabilities): raise ValueError("E_OUTPUT_CAPABILITY_MISSING")
    start,end=projection.window; columns=view["body"].get("tableColumns", [{"id":"title","source":"title","missing":"em-dash"}])
    groups=profile.get("groups",{"mode":"header-and-separator","gapRows":1}); table=slots.get("table") if slots else None; timeline=slots.get("timeline") if slots else None; header=slots.get("title") if slots else None
    col_width=(table.width//max(1,len(columns))) if table else 150; left=timeline.x if timeline else 32+col_width*len(columns); top=(timeline.y+40) if timeline else 128; day=max(4,((timeline.width if timeline else 1200)-24)//max(1,(end-start).days)) ; row=36; width=(header.x+header.width if header else max(1080,left+(end-start).days*day+48)); colors=_theme_colors(theme)
    group_breaks=sum(1+groups["gapRows"] for a,b in zip(projection.items,projection.items[1:]) if a.group_id!=b.group_id)
    height=900 if slots else top+(len(projection.items)+group_breaks+4)*row+40
    title_x,title_y=(header.x,header.y+32) if header else (32,34); table_x=table.x if table else 32
    p=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img" aria-labelledby="title desc">',f'<title id="title">{escape(title)} table timeline</title>',f'<desc id="desc">Semantic table and hierarchical calendar with {len(projection.items)} selected rows.</desc>',f'<rect width="{width}" height="{height}" fill="{colors["background"]}"/>',f'<text x="{title_x}" y="{title_y}" font-family="system-ui" font-size="20" font-weight="700">{escape(title)}</text>']
    p.append(f'<rect data-purpose="table-header" x="{table_x-8}" y="{top-32}" width="{col_width*len(columns)}" height="24" fill="{_theme_color(theme,"table-header","#f3f4f6")}"/>')
    for n,col in enumerate(columns): p.append(f'<text data-purpose="table-header" x="{table_x+n*col_width}" y="{top-14}" font-family="system-ui" font-size="12" font-weight="700">{escape(str(col["id"]))}</text>')
    cursor=date(start.year,start.month,1)
    while cursor<=end:
        x=left+(cursor-start).days*day; p += [f'<line data-purpose="axis-major" x1="{x}" y1="70" x2="{x}" y2="{height-24}" stroke="#9ca3af"/>',f'<text data-purpose="axis-band" x="{x+3}" y="70" font-family="system-ui" font-size="11">{cursor:%b %Y}</text>']
        cursor=date(cursor.year+1,1,1) if cursor.month==12 else date(cursor.year,cursor.month+1,1)
    quarter=date(start.year,((start.month-1)//3)*3+1,1)
    while quarter<=end:
        x=left+(quarter-start).days*day; p.append(f'<text data-purpose="axis-quarter" x="{x+3}" y="52" font-family="system-ui" font-size="12" font-weight="700">Q{(quarter.month-1)//3+1} {quarter.year}</text>'); quarter=date(quarter.year+1,1,1) if quarter.month==10 else date(quarter.year,quarter.month+3,1)
    cursor=start
    while cursor<=end:
        x=left+(cursor-start).days*day; p.append(f'<line data-purpose="axis-minor" x1="{x}" y1="88" x2="{x}" y2="{height-24}" stroke="#e5e7eb"/>'); cursor=date.fromordinal(cursor.toordinal()+7)
    y=top; previous=None; positions: dict[str, tuple[int,int]]={}
    for item in projection.items:
        if item.group_id!=previous:
            if previous is not None: y+=row*(1+groups["gapRows"])
            if groups["mode"] in {"band","header-and-separator"}: p.append(f'<rect data-purpose="group-band" x="24" y="{y}" width="{width-48}" height="{row}" fill="{_theme_color(theme,"group-band","#f3f4f6")}"/>')
            if groups["mode"]=="header-and-separator": p.append(f'<text data-purpose="group-header" x="32" y="{y+22}" font-family="system-ui" font-size="13" font-weight="700">{escape(item.group_label)}</text>'); y+=row
            if previous is not None and groups["mode"] in {"separator","header-and-separator"}: p.append(f'<line data-purpose="group-separator" x1="24" y1="{y}" x2="{width-24}" y2="{y}" stroke="#9ca3af"/>')
            previous=item.group_id
        y+=row
        positions[item.object_id]=(left,y-6)
        p.append(f'<line data-purpose="table-row" x1="{table_x-8}" y1="{y+10}" x2="{left-12}" y2="{y+10}" stroke="#e5e7eb"/>')
        for n,col in enumerate(columns):
            value=_table_value(item,project,col["source"]); text=_display_value(value,col["missing"])
            p.append(f'<text data-scene-id="item:{item.object_id}:cell:{escape(str(col["id"]))}" data-source-ref="{item.object_id}" data-purpose="table-cell" x="{table_x+n*col_width}" y="{y}" font-family="system-ui" font-size="12">{escape(text)}</text>')
        if item.source_type=="span":
            x=left+(item.planned["start"]-start).days*day; w=max(3,(item.planned["end"]-item.planned["start"]).days*day); p.append(f'<rect data-scene-id="item:{item.object_id}:planned" data-source-ref="{item.object_id}" data-purpose="planned" x="{x}" y="{y-12}" width="{w}" height="12" rx="3" fill="{colors["planned"]}"/>')
        else:
            x=left+(item.planned["at"]-start).days*day; p.append(f'<path data-scene-id="item:{item.object_id}:planned" data-source-ref="{item.object_id}" data-purpose="planned" d="M{x} {y-12} L{x+6} {y-6} L{x} {y} L{x-6} {y-6}Z" fill="{colors["planned"]}"/>')
        if item.actual and item.source_type=="span" and "finish" in item.actual:
            ax=left+(item.actual.get("start",item.planned["start"])-start).days*day; aw=max(3,(item.actual["finish"]-item.actual.get("start",item.planned["start"])).days*day); p.append(f'<rect data-scene-id="item:{item.object_id}:actual" data-source-ref="{item.object_id}" data-purpose="actual" x="{ax}" y="{y+3}" width="{aw}" height="8" rx="2" fill="{colors["actual"]}"/>')
    if profile.get("constraints",{}).get("connectors")=="obstacle-aware":
        for relation in project.get("relations",[]):
            source=relation.get("from",{}).get("object"); target=relation.get("to",{}).get("object")
            if source in positions and target in positions:
                x1,y1=positions[source]; x2,y2=positions[target]; mid=(x1+x2)//2
                p.append(f'<path data-purpose="routed-connector" data-source-ref="{escape(str(relation.get("id","relation")))}" d="M{x1} {y1} C{mid} {y1} {mid} {y2} {x2} {y2}" fill="none" stroke="{_theme_color(theme,"routed-connector","#6b7280")}" stroke-width="1"/>')
    notes=slots.get("notes") if slots else None
    if notes:
        ny=notes.y+18
        for annotation in project.get("annotations",{}).values():
            p.append(f'<text data-purpose="presentation-annotation" x="{notes.x}" y="{ny}" font-family="system-ui" font-size="11">{escape(str(annotation.get("text","")))}</text>'); ny+=16
    return "\n".join(p+["</svg>"])+"\n"


def append_review_summary(svg: str, projection: ReviewProjection, profile: dict[str, Any], as_of: date) -> str:
    """Append only declared, read-only M16 metrics to an existing SVG composition."""
    total=len(projection.items); actual=sum(bool(item.actual) for item in projection.items)
    points=sorted(item.planned["at"] for item in projection.items if item.source_type=="point" and item.planned["at"]>=as_of)
    values={"selectedCount":str(total),"actualCoverage":f"{actual}/{total}" if total else "unknown","knownFinishVarianceCount":str(sum(item.finish_delta is not None for item in projection.items)),"missingActualCount":str(total-actual),"nextPlannedPoint":points[0].isoformat() if points else "unknown"}
    lines=[]; y=24
    for panel in profile["panels"]:
        text=" · ".join(f'{metric}: {values[metric]}' for metric in panel["metrics"])
        lines.append(f'<text data-purpose="summary-panel" data-source-ref="derived:{escape(panel["id"])}" x="32" y="{y}" font-family="system-ui" font-size="11">{escape(panel["id"])} — {escape(text)}</text>'); y+=18
    return svg.replace("</svg>", "\n".join(lines)+"\n</svg>")


def _table_value(item: ReviewItem, project: dict[str, Any], source: Any) -> Any:
    if isinstance(source,str): return {"id":item.object_id,"title":item.title,"objectType":item.source_type,"entity":item.group_label}.get(source)
    if "field" in source: return (item.fields or {}).get(source["field"])
    facet=source["comparisonFacet"]; return {"finishDelta":item.finish_delta,"missingActual":not bool(item.actual),"progress":(item.actual or {}).get("progress")}.get(facet)


def _display_value(value: Any, missing: str) -> str:
    if value is None: return {"blank":"","em-dash":"—","unknown":"unknown"}[missing]
    return f'{value:+d}d' if isinstance(value,int) and not isinstance(value,bool) else str(value)




def _theme_colors(theme: dict[str, Any]) -> dict[str,str]:
    values={key:str(value.get("value")) for key,value in theme.get("body",{}).get("values",{}).items()}
    roles=theme.get("body",{}).get("roles",{})
    def color(role:str, fallback:str)->str: return values.get(roles.get(role,{}).get("fill") or roles.get(role,{}).get("stroke"),fallback)
    return {"background":"#faf8f6","planned":color("planned","#2563eb"),"actual":color("actual","#16a34a"),"behind":color("variance-behind","#b45309")}


def _theme_color(theme: dict[str, Any], role: str, fallback: str) -> str:
    values={key:str(value.get("value")) for key,value in theme.get("body",{}).get("values",{}).items()}
    binding=theme.get("body",{}).get("roles",{}).get(role,{})
    return values.get(binding.get("fill") or binding.get("stroke"),fallback)
