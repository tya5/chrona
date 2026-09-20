"""Derived table/timeline geometry shared by every declarative review preset."""
from __future__ import annotations

from datetime import date, timedelta
from heapq import heappop, heappush
from html import escape
from itertools import groupby

from .layout import Rect


def route_orthogonal(start, end, obstacles):
    """Shortest orthogonal visibility-grid route, with a bend penalty.

    Ports must be outside inflated obstacles. Stable sorted coordinates and heap
    tie breaking make routes independent of hash randomization.
    """
    xs = sorted({start[0], end[0], *(v for box in obstacles for v in (box[0]-2, box[2]+2))})
    ys = sorted({start[1], end[1], *(v for box in obstacles for v in (box[1]-2, box[3]+2))})
    source = (xs.index(start[0]), ys.index(start[1]), -1)
    target = (xs.index(end[0]), ys.index(end[1]))

    def clear(a, b):
        for l, t, r, bottom in obstacles:
            if a[1] == b[1] and t < a[1] < bottom and max(a[0], b[0]) > l and min(a[0], b[0]) < r:
                return False
            if a[0] == b[0] and l < a[0] < r and max(a[1], b[1]) > t and min(a[1], b[1]) < bottom:
                return False
        return True

    costs, parents, queue = {source: 0}, {}, [(0, source)]
    finish = None
    while queue:
        cost, state = heappop(queue)
        if cost != costs[state]:
            continue
        i, j, direction = state
        if (i, j) == target:
            finish = state
            break
        for ni, nj, nd in ((i-1, j, 0), (i+1, j, 0), (i, j-1, 1), (i, j+1, 1)):
            if not (0 <= ni < len(xs) and 0 <= nj < len(ys)):
                continue
            a, b = (xs[i], ys[j]), (xs[ni], ys[nj])
            if not clear(a, b):
                continue
            newcost = cost + abs(a[0]-b[0]) + abs(a[1]-b[1]) + (12 if direction not in (-1, nd) else 0)
            new = (ni, nj, nd)
            if newcost < costs.get(new, float('inf')):
                costs[new], parents[new] = newcost, state
                heappush(queue, (newcost, new))
    if finish is None:
        raise ValueError('E_CONNECTOR_UNROUTABLE')
    path = []
    while True:
        path.append((xs[finish[0]], ys[finish[1]]))
        if finish == source:
            break
        finish = parents[finish]
    path.reverse()
    simplified = []
    for point in path:
        if len(simplified) >= 2:
            a, b = simplified[-2:]
            if a[0] == b[0] == point[0] or a[1] == b[1] == point[1]:
                simplified.pop()
        simplified.append(point)
    return simplified


def render_gantt(title, projection, project, view, theme, profile, slots, settings=None, *, presentation_scene=None):
    from .review_svg import _theme_color, _theme_font, _table_value, _display_value
    from .presentation_paint import resolve_facet_paint
    from .presentation_labels import LabelRect, place_label

    surface = profile.get('surface', {})
    metrics = None
    if settings is not None:
        from .font_metrics import resolve_font_metrics
        from .presentation_layout import solve_presentation_layout
        metrics = resolve_font_metrics(settings['theme']['fontFamily'], settings['context']['fontMetrics'])
        font = escape(settings['theme']['fontFamily'], quote=True)
        viewport = settings['context']['viewport']; width, height = viewport['width'], viewport['height']
        derived = solve_presentation_layout(settings)
        slots = {key: Rect(int(value.x), int(value.y), int(value.width), int(value.height)) for key, value in derived.items()}
        surface = {
            'groupMode': settings['layout']['group']['mode'], 'groupLabel': settings['detail']['groupLabel'],
            'groupFraction': settings['layout']['group']['fraction'], 'groupGap': settings['layout']['group']['gap'],
            'axisLevels': settings['layout']['axis']['levels'], 'fontSize': settings['theme']['typography']['body']['size'],
            'titleSize': settings['theme']['typography']['heading']['size'], 'groupFontSize': settings['theme']['typography']['group']['size'],
            'barHeight': settings['theme']['bar']['plannedHeight'], 'barGap': settings['layout']['bars']['gap'],
            'showVariance': settings['layout']['variance']['visible'],
        }
    else:
        font = escape(_theme_font(theme), quote=True)
    if settings is not None:
        paints, strokes = settings['theme']['paints'], settings['theme']['strokes']
        palette = {
            'text': paints['text']['color'], 'text-muted': paints['textMuted']['color'],
            'axis-major': strokes['axisMajor']['color'], 'background': paints['background']['color'],
            'planned': paints['planned']['color'], 'actual': paints['actual']['color'],
            'variance-behind': paints['varianceBehind']['color'], 'routed-connector': strokes['dependency']['color'],
            'milestone': paints['milestone']['color'], 'table-header': paints['tableHeader']['color'],
            'group-band': paints['groupBand']['color'], 'row-shade': paints['rowShade']['color'],
        }
        def color(role, default):
            group_paint = settings['theme']['groupPaints'].get(role.removeprefix('group:'), paints['groupBand'])
            return escape(palette.get(role, group_paint['color']), quote=True)
    else:
        color = lambda role, default: escape(_theme_color(theme, role, default), quote=True)
    ink, muted = color('text', '#102644'), color('text-muted', '#637187')
    grid, background = color('axis-major', '#DDE4EC'), color('background', '#FFFFFF')
    planned, actual = color('planned', '#3885E5'), color('actual', '#249B78')
    variance, connector = color('variance-behind', '#CA8517'), color('routed-connector', '#8795AA')
    point_color = color('milestone', '#102B50')
    if settings is None:
        width, height = {'16:9': (1600, 900), '4:3': (1200, 900), 'free': (1400, 900)}[profile.get('canvas', {}).get('aspectRatio', '16:9')]
    if slots is None:
        slots = {'title': Rect(24, 24, width-48, 96), 'table': Rect(24, 120, 460, 650), 'timeline': Rect(484, 120, width-508, 650)}
    table, timeline = slots['table'], slots['timeline']
    axis_slot = slots.get('timelineAxis', timeline)
    header = slots.get('title', Rect(24, 24, width-48, 96))
    if table.y != timeline.y or table.height != timeline.height:
        raise ValueError('E_GANTT_ROW_ALIGNMENT')
    mode = surface.get('groupMode', 'header')
    group_width = table.width * surface.get('groupFraction', .38) if mode == 'merged' else 0
    group_gap = surface.get('groupGap', 6)
    fs, gs, ts = surface.get('fontSize', 18), surface.get('groupFontSize', 24), surface.get('titleSize', 36)
    bh, bg = surface.get('barHeight', 16), surface.get('barGap', 4)
    levels = surface.get('axisLevels', ['quarter', 'month'])
    axis_h = sum(settings['layout']['axis']['bandHeights']) if settings else 48 + (24 if 'quarter' in levels else 0)
    top, bottom = table.y + axis_h, table.y + table.height
    left, right = timeline.x, timeline.x + timeline.width
    groups = [(gid, list(items)) for gid, items in groupby(projection.items, lambda item: item.group_id)]
    extra = len(groups)*32 if mode == 'header' else 0
    rh = (bottom-top-group_gap*max(0, len(groups)-1)-extra)/max(1, len(projection.items))
    if rh < max(fs*2.8, 2*bh+bg+16):
        raise ValueError('E_LAYOUT_REQUIRED_OVERFLOW:rows')
    columns = view['body'].get('tableColumns', [{'id': 'Activity', 'source': 'title', 'missing': 'em-dash'}])
    cw = (table.width-group_width)/len(columns)
    start, end = presentation_scene.window if presentation_scene is not None else projection.window
    days = max(1, (end-start).days)
    # Padding protects endpoint symbols; one continuous scale is shared by all marks.
    sx = lambda d: left+20+(d-start).days/days*(timeline.width-40)
    axis_sx = lambda d: axis_slot.x+20+(d-start).days/days*(axis_slot.width-40)
    f = lambda n: f'{n:.2f}'.rstrip('0').rstrip('.')
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
             f'<title id="title">{escape(title)}</title>',
             f'<desc id="desc">Plan and Actual comparison. {len(projection.items)} rows; {len(projection.unmatched_actual_ids)} unmatched observations. Actual is not a forecast.</desc>',
             f'<defs><marker id="dependency-arrow" markerWidth="{settings["theme"]["arrow"]["width"] if settings else 6}" markerHeight="{settings["theme"]["arrow"]["height"] if settings else 6}" refX="{settings["theme"]["arrow"]["width"]-settings["theme"]["arrow"]["tipInset"] if settings else 5.5}" refY="{(settings["theme"]["arrow"]["height"] if settings else 6)/2}" orient="auto"><path d="M0 0L{settings["theme"]["arrow"]["width"] if settings else 6} {(settings["theme"]["arrow"]["height"] if settings else 6)/2}L0 {settings["theme"]["arrow"]["height"] if settings else 6}Z" fill="{connector}"/></marker></defs>',
             f'<rect width="{width}" height="{height}" fill="{background}"/>']
    if presentation_scene is not None:
        scale_id = settings['layout']['slots'].get('timelineAxis', {}).get('scaleId', '') if settings else ''
        parts.append(f'<metadata data-presentation-scene="v0.1" data-axis-count="{len(presentation_scene.axes)}" data-tick-count="{len(presentation_scene.ticks)}" data-mark-count="{len(presentation_scene.marks)}" data-axis-scale-id="{escape(scale_id)}"/>')

    def rect(x, y, w, h, fill, purpose, ref='', more=''):
        return f'<rect data-purpose="{purpose}" data-source-ref="{escape(ref)}" x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="{fill}" {more}/>'

    def text(x, y, value, size=fs, weight=400, fill=ink, purpose='label', ref='', anchor='start'):
        role = {'table-cell': 'body', 'group-header': 'group', 'table-header': 'tableHeader', 'axis-band': 'month', 'axis-quarter': 'quarter', 'legend-label': 'legend', 'data-coverage': 'coverage', 'missing-actual': 'missingActual'}.get(purpose, purpose)
        typography = settings['theme']['typography'].get(role, {}) if settings else {}
        size, weight = typography.get('size', size), typography.get('weight', weight)
        return f'<text data-purpose="{purpose}" data-source-ref="{escape(ref)}" x="{f(x)}" y="{f(y)}" font-family="{font}" font-size="{size}" font-weight="{weight}" letter-spacing="{typography.get("letterSpacing", 0)}" fill="{fill}" text-anchor="{anchor}">{escape(str(value))}</text>'

    def wrapped(x, cy, value, available, size=fs, weight=400, purpose='table-cell', ref=''):
        # Deliberately conservative: preserve full text instead of silent truncation.
        lines, line = [], ''
        for word in str(value).split():
            candidate = f'{line} {word}'.strip()
            too_wide = (metrics.width(candidate, size) > available) if metrics else (len(candidate) > max(1, int(available/(size*.58))))
            if too_wide and not line:
                raise ValueError('E_LAYOUT_REQUIRED_OVERFLOW:text')
            if too_wide and line:
                lines.append(line); line = ''
            line = f'{line} {word}'.strip()
        lines.append(line)
        if len(lines) > 3 or len(lines)*size*1.2 > rh-12:
            raise ValueError('E_LAYOUT_REQUIRED_OVERFLOW:text')
        return ''.join(text(x, cy-(len(lines)-1)*size*.6+i*size*1.2+size*.34, line, size, weight, purpose=purpose, ref=ref).replace('<text ', f'<text data-box-x="{f(x)}" data-box-width="{f(available)}" ') for i, line in enumerate(lines))

    last_visible = end-timedelta(days=1) if end.day == 1 and end>start else end
    values = dict(title=title, windowStart=f'{start:%b %Y}', windowLastVisible=f'{last_visible:%b %Y}', selectedCount=len(projection.items), unmatchedCount=len(projection.unmatched_actual_ids), missingCount=sum(1 for item in projection.items if not item.actual))
    visible_title = settings['detail']['title'].format_map(values) if settings else title
    if (metrics.width(visible_title, ts) if metrics else len(visible_title)*ts*.58) > header.width:
        raise ValueError('E_LAYOUT_REQUIRED_OVERFLOW:title')
    parts.append(text(header.x, header.y+ts, visible_title, ts, 700, purpose='heading', ref='project'))
    if not settings or settings['layout']['title']['showSubtitle']:
        subtitle = settings['detail']['subtitle'].format_map(values) if settings else f'{start:%b %Y} – {last_visible:%b %Y}  /  Planned and observed delivery'
        offset = settings['layout']['title']['subtitleGap'] + settings['theme']['typography']['subtitle']['size'] if settings else 30
        parts.append(text(header.x, header.y+ts+offset, subtitle, 19, fill=muted, purpose='subtitle', ref='view:window'))
    parts.append(rect(table.x, table.y, right-table.x, axis_h, color('table-header', '#F1F6FC'), 'table-header'))
    if mode == 'merged':
        parts.append(text(table.x+12, top-17, surface.get('groupLabel', 'Group'), fs, 700, purpose='table-header'))
    for i, col in enumerate(columns):
        parts.append(text(table.x+group_width+i*cw+12, top-17, col['id'], fs, 700, purpose='table-header'))

    foreground, obstacles, anchors = [], [], {}
    scene_marks = {}
    lane_stacks = {lane.object_id: lane.stack for lane in presentation_scene.lanes} if presentation_scene is not None else {}
    if presentation_scene is not None:
        for mark in presentation_scene.marks:
            scene_marks.setdefault(mark.source_id, {})[mark.facet] = mark
    y = top
    for group_index, (gid, items) in enumerate(groups):
        group_top = y
        if mode == 'header':
            parts.append(text(table.x+12, y+23, items[0].group_label, gs, 700, purpose='group-header', ref=gid)); y += 32
        group_h = rh*len(items)
        fill = color(f'group:{gid}', color('group-band', '#EEF3F8'))
        if mode != 'none':
            opacity = settings['theme']['groupPaints'].get(gid, settings['theme']['paints']['groupBand'])['opacity'] if settings else 1
            parts.append(rect(table.x, y, right-table.x, group_h, fill, 'group-surface', gid, f'opacity="{opacity}"'))
        if mode == 'merged':
            foreground.append(wrapped(table.x+12, y+group_h/2, items[0].group_label, group_width-24, gs, 700, 'group-header', gid))
        for i, item in enumerate(items):
            cy = y+rh/2
            if i%2 == 1:
                parts.append(rect(table.x+group_width, y, right-table.x-group_width, rh, color('row-shade', '#FFFFFF'), 'row-shade', item.object_id, f'opacity="{settings["theme"]["paints"]["rowShade"]["opacity"] if settings else .34}"'))
            parts.append(f'<path data-purpose="table-row" d="M{f(table.x+group_width)} {f(y+rh)}H{f(right)}" stroke="{color("row-shade", "#FFFFFF")}"/>')
            for ci, col in enumerate(columns):
                value = _display_value(_table_value(item, project, col['source']), col['missing'])
                foreground.append(wrapped(table.x+group_width+ci*cw+12, cy, value, cw-24, ref=item.object_id))
            py = cy-bg/2-bh
            if item.source_type == 'span':
                planned_mark = scene_marks.get(item.object_id, {}).get('baseline') or scene_marks.get(item.object_id, {}).get('planned')
                mark_start, mark_end = (planned_mark.start, planned_mark.end) if planned_mark else (item.planned['start'], item.planned['end'])
                x1, x2 = sx(mark_start), sx(mark_end)
                if x1 < left or x2 > right:
                    raise ValueError('E_LAYOUT_REQUIRED_OVERFLOW:window')
                planned_fill = escape(resolve_facet_paint(settings['theme'], item.group_id, planned_mark.facet)['color'], quote=True) if settings else planned
                foreground.append(rect(x1, py, max(settings['theme']['bar']['minWidth'] if settings else 1,x2-x1), bh, planned_fill, 'planned', item.object_id, f'data-stack="{lane_stacks.get(item.object_id, 0)}" rx="{settings["theme"]["bar"]["radius"] if settings else 2}"'))
                obstacles.append((x1-4, py-4, x2+4, py+bh+4))
                anchors[item.object_id] = {'start': (x1, py+bh/2, -1), 'end': (x2, py+bh/2, 1)}
                actual_mark = scene_marks.get(item.object_id, {}).get('actual')
                if actual_mark is None and presentation_scene is None and item.actual and 'finish' in item.actual:
                    from types import SimpleNamespace
                    actual_mark = SimpleNamespace(start=item.actual.get('start', item.planned['start']), end=item.actual['finish'])
                if actual_mark is not None:
                    a1, a2 = sx(actual_mark.start), sx(actual_mark.end)
                    if a1 < left or a2 > right:
                        raise ValueError('E_LAYOUT_REQUIRED_OVERFLOW:actual')
                    actual_y = py if settings and settings['layout']['bars']['comparisonMode'] == 'overlaid' else cy+bg/2
                    actual_fill = escape(resolve_facet_paint(settings['theme'], item.group_id, 'actual')['color'], quote=True) if settings else actual
                    foreground.append(rect(a1, actual_y, max(settings['theme']['bar']['minWidth'] if settings else 1,a2-a1), bh, actual_fill, 'actual', item.object_id, f'data-stack="{lane_stacks.get(item.object_id, 0)}" rx="{settings["theme"]["bar"]["radius"] if settings else 2}"'))
                    obstacles.append((a1-4, actual_y-4, a2+4, actual_y+bh+4))
                    actual_rule = next((rule for rule in settings['detail']['labelRules']
                                        if rule['source'] == 'actual-date' and rule['facet'] == 'actual' and rule['endpoint'] == 'finish'), None) if settings else None
                    if actual_rule is not None:
                        actual_label = actual_mark.end.isoformat()
                        actual_placement = place_label(LabelRect(a2, actual_y, 1, bh),
                                                       (metrics.width(actual_label, 12) if metrics else 60, 15),
                                                       settings['layout']['labelPlacement']['candidateSides'],
                                                       bounds=LabelRect(left, top, timeline.width, bottom-top),
                                                       obstacles=[LabelRect(*box[:2], box[2]-box[0], box[3]-box[1]) for box in obstacles],
                                                       gap=settings['layout']['missingActual']['gap'],
                                                       required=actual_rule['required'],
                                                       overflow=settings['layout']['labelPlacement']['overflow'])
                        if actual_placement is not None:
                            foreground.append(text(actual_placement.bounds.x, actual_placement.bounds.y+actual_placement.bounds.height*.8,
                                                   actual_label, 12, fill=muted, purpose='actual-date', ref=item.object_id))
                            obstacles.append((actual_placement.bounds.x, actual_placement.bounds.y,
                                              actual_placement.bounds.right, actual_placement.bounds.bottom))
                    delta_mark = scene_marks.get(item.object_id, {}).get('finish-delta')
                    if delta_mark is None and presentation_scene is None and item.finish_delta is not None:
                        from types import SimpleNamespace
                        delta_mark = SimpleNamespace(variance_days=item.finish_delta)
                    if surface.get('showVariance', True) and delta_mark is not None:
                        vx = max(x2, a2)+12
                        label = f'{delta_mark.variance_days:+d}d'
                        rule = next((rule for rule in settings['detail']['labelRules']
                                     if rule['source'] == 'comparison-delta' and rule['facet'] == 'variance' and rule['endpoint'] == 'finish'), None) if settings else None
                        label_width = metrics.width(label, 17) if metrics else 51
                        placement = place_label(LabelRect(max(x2, a2), py, 3, 2*bh+bg), (label_width, 21),
                                                settings['layout']['labelPlacement']['candidateSides'] if settings else ('end',),
                                                bounds=LabelRect(left, top, timeline.width, bottom-top),
                                                obstacles=[LabelRect(*box[:2], box[2]-box[0], box[3]-box[1]) for box in obstacles],
                                                gap=settings['layout']['variance']['labelGap'] if settings else 7,
                                                required=rule['required'] if rule else True,
                                                overflow=settings['layout']['labelPlacement']['overflow'] if settings else 'diagnose')
                        if placement is None:
                            continue
                        vx = placement.bounds.x - 10
                        variance_fill = escape(resolve_facet_paint(settings['theme'], item.group_id, 'variance')['color'], quote=True) if settings else variance
                        foreground.append(rect(vx, py, 3, 2*bh+bg, variance_fill, 'variance-marker', item.object_id))
                        foreground.append(text(placement.bounds.x, placement.bounds.y+placement.bounds.height*.8, label, 17, 700, variance_fill, 'variance', item.object_id))
                        obstacles.append((placement.bounds.x, placement.bounds.y, placement.bounds.right, placement.bounds.bottom))
                elif not item.actual:
                    foreground.append(text(x1, cy+bh+bg/2, 'Actual not reported', 12, fill=muted, purpose='missing-actual', ref=item.object_id))
                    obstacles.append((x1-4, cy+2, x1+112, cy+bh+bg/2+4))
            else:
                x = sx(item.planned['at']); radius = 9
                if x-radius < left or x+radius > right:
                    raise ValueError('E_LAYOUT_REQUIRED_OVERFLOW:point')
                foreground.append(f'<path data-purpose="planned" data-source-ref="{escape(item.object_id)}" d="M{f(x)} {f(cy-radius)}l{radius} {radius}l-{radius} {radius}l-{radius} -{radius}Z" fill="{point_color}"/>')
                anchors[item.object_id] = {'at': (x, cy, 0)}
                obstacles.append((x-radius-4, cy-radius-4, x+radius+4, cy+radius+4))
            y += rh
        y += group_gap

    # Scene intervals are already clipped to the View window; adapter only maps them to x/y.
    if presentation_scene is not None:
        for interval in presentation_scene.axes:
            x1, x2 = axis_sx(interval.start), axis_sx(interval.end)
            if interval.level == 'month':
                parts.append(text((x1+x2)/2, top-17, f'{interval.start:%b %Y}', fs, 700, purpose='axis-band', anchor='middle'))
            elif interval.level == 'quarter':
                parts.append(text((x1+x2)/2, table.y+20, f'Q{(interval.start.month-1)//3+1} {interval.start.year}', 13, 700, purpose='axis-quarter', anchor='middle'))
        for tick in presentation_scene.ticks:
            parts.append(f'<path data-purpose="axis-major" data-scale-id="{escape(scale_id)}" d="M{f(sx(tick.start))} {f(table.y)}V{f(bottom)}" stroke="{grid}" stroke-dasharray="3 4"/>')
    else:
        cursor = date(start.year, start.month, 1)
        while cursor < end:
            next_month = date(cursor.year+1, 1, 1) if cursor.month == 12 else date(cursor.year, cursor.month+1, 1)
            x1, x2 = max(left, sx(cursor)), min(right, sx(next_month))
            if 'month' in levels:
                parts.append(text((x1+x2)/2, top-17, f'{cursor:%b %Y}', fs, 700, purpose='axis-band', anchor='middle'))
            parts.append(f'<path data-purpose="axis-major" d="M{f(x1)} {f(table.y)}V{f(bottom)}" stroke="{grid}" stroke-dasharray="3 4"/>')
            cursor = next_month
        if 'quarter' in levels:
            cursor = date(start.year, ((start.month-1)//3)*3+1, 1)
            while cursor < end:
                nq = date(cursor.year+1, 1, 1) if cursor.month == 10 else date(cursor.year, cursor.month+3, 1)
                parts.append(text((sx(max(start,cursor))+sx(min(end,nq)))/2, table.y+20, f'Q{(cursor.month-1)//3+1} {cursor.year}', 13, 700, purpose='axis-quarter', anchor='middle'))
                cursor = nq
    parts.append(f'<rect data-purpose="table-frame" x="{table.x}" y="{table.y}" width="{f(right-table.x)}" height="{table.height}" fill="none" stroke="{grid}"/>')

    if profile.get('constraints', {}).get('connectors') == 'obstacle-aware' and view['body'].get('visibility', {}).get('relations', 'semantic') != 'none':
        for relation in project.get('relations', []):
            if relation.get('type', 'dependency') != 'dependency': continue
            a, b = relation['from'], relation['to']
            if a['object'] not in anchors or b['object'] not in anchors: continue
            aa, bb = anchors[a['object']], anchors[b['object']]
            ak, bk = a.get('endpoint', 'end' if 'end' in aa else 'at'), b.get('endpoint', 'start' if 'start' in bb else 'at')
            if ak not in aa or bk not in bb: raise ValueError('E_CONNECTOR_ENDPOINT')
            ax, ay, ad = aa[ak]; bx, by, bd = bb[bk]
            if ad == 0: ax += 9; ad = 1
            if bd == 0: bx -= 9; bd = -1
            port_a, port_b = (ax+ad*8, ay), (bx+bd*8, by)
            points = [(ax, ay), *route_orthogonal(port_a, port_b, obstacles), (bx, by)]
            path = 'M'+'L'.join(f'{f(x)} {f(y)}' for x,y in points)
            parts.append(f'<path data-purpose="routed-connector" data-source-ref="{escape(str(relation.get("id", "relation")))}" data-from-endpoint="{ak}" data-to-endpoint="{bk}" d="{path}" fill="none" stroke="{connector}" stroke-width="{settings["theme"]["strokes"]["dependency"]["width"] if settings else 1.4}" marker-end="url(#dependency-arrow)"/>')
    parts.extend(foreground)
    notes = slots.get('notes')
    if notes:
        ny = notes.y+20
        for annotation_id, annotation in project.get('annotations', {}).items():
            value = str(annotation.get('text', ''))
            if ny > notes.y+notes.height or len(value)*fs*.58 > notes.width:
                raise ValueError('E_LAYOUT_REQUIRED_OVERFLOW:notes')
            parts.append(text(notes.x, ny, value, purpose='presentation-annotation', ref=annotation_id))
            ny += fs*1.4
    legend = slots.get('legend')
    if legend and settings:
        spec = settings['layout']['legend']
        typography = settings['theme']['typography']['legend']
        size = typography['size']; line_height = size * typography['lineHeight']
        x0 = legend.x + spec['padding']['left']; xlimit = legend.x + legend.width - spec['padding']['right']
        lx, ly = x0, legend.y + spec['padding']['top'] + size
        sw, sh = spec['swatchWidth'], spec['swatchHeight']
        symbols = {'planned': (planned, 'bar'), 'actual': (actual, 'bar'), 'variance': (variance, 'variance'), 'milestone': (point_color, 'point'), 'dependency': (connector, 'line')}
        for entry in settings['detail']['legend']:
            label = entry['label']; paint, kind = symbols[entry['role']]
            item_width = sw + spec['labelGap'] + metrics.width(label, size, typography['letterSpacing'])
            if lx + item_width > xlimit and lx > x0 and spec['wrap']:
                lx, ly = x0, ly + line_height + spec['rowGap']
            if lx + item_width > xlimit:
                raise ValueError('E_LAYOUT_REQUIRED_OVERFLOW:legend')
            cy = ly-size/3
            if kind == 'bar': parts.append(rect(lx, cy-sh/2, sw, sh, paint, 'legend-swatch'))
            elif kind == 'variance': parts.append(rect(lx+sw/2, cy-sh/2, settings['theme']['varianceMarkerWidth'], sh, paint, 'legend-swatch'))
            elif kind == 'point':
                radius = settings['theme']['point']['size']/2
                parts.append(f'<path d="M{f(lx+sw/2)} {f(cy-radius)}l{radius} {radius}l-{radius} {radius}l-{radius} -{radius}Z" fill="{paint}"/>')
            else: parts.append(f'<path d="M{f(lx)} {f(cy)}h{sw}" stroke="{paint}" marker-end="url(#dependency-arrow)"/>')
            parts.append(text(lx+sw+spec['labelGap'], ly, label, purpose='legend-label', fill=muted))
            lx += item_width + spec['itemGap']
        coverage = settings['detail']['coverage'].format_map(values)
        cs = settings['theme']['typography']['coverage']
        ly += spec['coverageGap'] + cs['size']
        if ly > legend.y+legend.height-spec['padding']['bottom'] or metrics.width(coverage, cs['size'], cs['letterSpacing']) > xlimit-x0:
            raise ValueError('E_LAYOUT_REQUIRED_OVERFLOW:legend')
        parts.append(text(x0, ly, coverage, fill=muted, purpose='data-coverage'))
    elif legend:
        lx, ly = legend.x, legend.y+34
        for label, paint, kind, step in [('Planned', planned, 'bar', 150), ('Actual', actual, 'bar', 145), ('Finish variance', variance, 'variance', 220), ('Milestone', point_color, 'point', 175), ('Dependency', connector, 'line', 180)]:
            if kind == 'bar': parts.append(rect(lx, ly-11, 38, 12, paint, 'legend-swatch'))
            elif kind == 'variance': parts.append(rect(lx+8, ly-16, 3, 22, paint, 'legend-swatch'))
            elif kind == 'point': parts.append(f'<path d="M{lx+12} {ly-15}l9 9l-9 9l-9 -9Z" fill="{paint}"/>')
            else: parts.append(f'<path d="M{lx} {ly-5}h36" stroke="{paint}" marker-end="url(#dependency-arrow)"/>')
            parts.append(text(lx+48, ly, label, 16, fill=muted, purpose='legend-label')); lx += step
        missing = sum(1 for item in projection.items if not item.actual)
        parts.append(text(legend.x, ly+34, f'Actual unavailable: {missing}/{len(projection.items)} items  ·  Unmatched observations: {len(projection.unmatched_actual_ids)}  ·  Variance in calendar days', 14, fill=muted, purpose='data-coverage'))
    return '\n'.join(parts+['</svg>'])+'\n'
