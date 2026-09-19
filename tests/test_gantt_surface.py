from copy import deepcopy
from datetime import date
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import pytest
import yaml
from jsonschema import Draft202012Validator, RefResolver

from chrona.gantt_surface import route_orthogonal
from chrona.layout import resolve_layout_profile, solve_layout
from chrona.review_svg import build_review_projection, render_table_timeline_svg
from chrona.scheduler import schedule

ROOT = Path(__file__).resolve().parents[1]
CAPS = {'sourceMetadata', 'accessibleText', 'semanticRoles', 'marker', 'tableSemantics', 'hierarchicalAxis'}


def fixture():
    def read(name):
        return yaml.safe_load((ROOT/'examples'/name).read_text())
    return [read(name) for name in ('controller-z-silicon-bringup.yaml', 'controller-z-actual.yaml', 'controller-z-executive-view.yaml', 'controller-z-review-style.yaml', 'controller-z-executive-theme.yaml', 'controller-z-executive-layout.yaml')]


def render(resources):
    project, actual, view, style, theme, profile = resources
    result = schedule(project)
    assert result.ok
    projection = build_review_projection(project, result.placements, view, actual, style, theme)
    manifest = resolve_layout_profile(profile, {'title', 'table', 'timeline', 'legend'})
    slots = solve_layout(profile, manifest)
    svg = render_table_timeline_svg(project['project']['title'], projection, project, view, theme, CAPS, profile, slots)
    return svg, projection, slots


def elements(svg, purpose):
    return [e for e in ET.fromstring(svg).iter() if e.get('data-purpose') == purpose]


def test_surface_is_deterministic_and_does_not_change_inputs():
    resources = fixture(); original = deepcopy(resources)
    svg, projection, slots = render(resources)
    assert render(resources)[0] == svg and resources == original
    assert projection.window == (date(2026, 2, 1), date(2026, 7, 1))
    assert ET.fromstring(svg).get('width') == '1600'
    assert ET.fromstring(svg).get('height') == '900'
    assert [e.text for e in elements(svg, 'axis-band')] == ['Feb 2026', 'Mar 2026', 'Apr 2026', 'May 2026', 'Jun 2026']
    assert 'Feb 2026 – Jun 2026' in svg
    assert [e.text for e in elements(svg, 'variance')] == ['+4d', '+4d']
    assert len(elements(svg, 'routed-connector')) == 7


def test_grid_and_routes_stay_inside_chart_not_table_or_footer():
    svg, _, slots = render(fixture())
    timeline = slots['timeline']
    for purpose in ('axis-major', 'routed-connector'):
        for e in elements(svg, purpose):
            if purpose == 'axis-major':
                x, y, bottom = map(float, re.findall(r'-?\d+(?:\.\d+)?', e.get('d')))
                assert timeline.x <= x <= timeline.x+timeline.width
                assert bottom == timeline.y+timeline.height
            else:
                numbers = list(map(float, re.findall(r'-?\d+(?:\.\d+)?', e.get('d'))))
                for x, y in zip(numbers[::2], numbers[1::2]):
                    assert timeline.x <= x <= timeline.x+timeline.width
                    assert timeline.y <= y <= timeline.y+timeline.height


def test_point_connector_terminates_at_diamond_and_respects_start_endpoint():
    svg, _, slots = render(fixture())
    paths = {e.get('data-source-ref'): e for e in elements(svg, 'routed-connector')}
    assert paths['bringup-to-performance'].get('data-from-endpoint') == 'start'
    assert paths['bringup-to-dvt'].get('data-from-endpoint') == 'end'
    start_x = float(re.findall(r'-?\d+(?:\.\d+)?', paths['bringup-to-performance'].get('d'))[0])
    end_x = float(re.findall(r'-?\d+(?:\.\d+)?', paths['bringup-to-dvt'].get('d'))[0])
    assert end_x > start_x
    point = next(e for e in elements(svg, 'planned') if e.get('data-source-ref') == 'evb-arrival')
    point_x = float(re.findall(r'-?\d+(?:\.\d+)?', point.get('d'))[0])
    endpoint = list(map(float, re.findall(r'-?\d+(?:\.\d+)?', paths['firmware-to-evb'].get('d'))))[-2]
    assert endpoint == pytest.approx(point_x-9, abs=.02)
    assert endpoint > slots['timeline'].x+100


def test_route_avoids_obstacle_interior_and_is_orthogonal():
    obstacle = (40, -10, 60, 10)
    route = route_orthogonal((0, 0), (100, 0), [obstacle])
    assert route == route_orthogonal((0, 0), (100, 0), [obstacle])
    assert route[0] == (0, 0) and route[-1] == (100, 0)
    for a, b in zip(route, route[1:]):
        assert a[0] == b[0] or a[1] == b[1]
        assert not (a[1] == b[1] and -10 < a[1] < 10 and max(a[0], b[0]) > 40 and min(a[0], b[0]) < 60)


def test_group_color_is_stable_under_group_reordering():
    resources = fixture()
    first = render(resources)[0]
    resources[2]['body']['grouping']['order'].reverse()
    second = render(resources)[0]
    colors = lambda svg: {e.get('data-source-ref'): e.get('fill') for e in elements(svg, 'group-surface')}
    assert colors(first) == colors(second)
    assert first != second


def test_all_sample_connectors_avoid_plan_and_actual_bar_interiors():
    svg = render(fixture())[0]
    bars = [e for e in elements(svg, 'planned')+elements(svg, 'actual') if e.tag.endswith('rect')]
    for path in elements(svg, 'routed-connector'):
        numbers = list(map(float, re.findall(r'-?\d+(?:\.\d+)?', path.get('d'))))
        points = list(zip(numbers[::2], numbers[1::2]))
        for a, b in zip(points, points[1:]):
            assert a[0] == b[0] or a[1] == b[1]
            for bar in bars:
                x, y, w, h = (float(bar.get(attr)) for attr in ('x', 'y', 'width', 'height'))
                # Tolerance for SVG's two-decimal serialization at shape boundaries.
                horizontal_hit = a[1] == b[1] and y+.02 < a[1] < y+h-.02 and max(a[0], b[0]) > x+.02 and min(a[0], b[0]) < x+w-.02
                vertical_hit = a[0] == b[0] and x+.02 < a[0] < x+w-.02 and max(a[1], b[1]) > y+.02 and min(a[1], b[1]) < y+h-.02
                assert not (horizontal_hit or vertical_hit), (path.get('data-source-ref'), bar.get('data-source-ref'))


def test_density_does_not_enable_owner_column():
    resources = fixture(); resources[-1]['surface']['groupMode'] = 'none'
    svg, _, _ = render(resources)
    assert not elements(svg, 'group-header')
    assert [e.text for e in elements(svg, 'table-header') if e.tag.endswith('text')] == ['Workstream']


def test_semantic_visibility_disables_relations():
    resources = fixture(); resources[2]['body']['visibility']['relations'] = 'none'
    assert not elements(render(resources)[0], 'routed-connector')


def test_unknown_surface_fields_and_invalid_sizes_rejected():
    resources = fixture()
    for key, value in [('arbitraryCode', 'x'), ('fontSize', 90), ('axisLevels', ['year'])]:
        profile = deepcopy(resources[-1]); profile['surface'][key] = value
        with pytest.raises(ValueError, match='E_LAYOUT_PROFILE_SCHEMA'):
            resolve_layout_profile(profile, {'title', 'table', 'timeline', 'legend'})


def test_required_overflow_diagnoses_instead_of_silent_overlap():
    resources = fixture(); resources[-1]['surface']['fontSize'] = 28
    resources[-1]['surface']['groupFraction'] = .6
    with pytest.raises(ValueError, match='E_LAYOUT_REQUIRED_OVERFLOW'):
        render(resources)


def test_selected_comparison_window_includes_actual():
    project, actual, view, style, theme, _ = fixture()
    view['body']['window'] = {'mode': 'selected-comparison', 'marginDays': 0}
    actual['body']['observations'][0]['actual']['finish'] = date(2026, 8, 5)
    projection = build_review_projection(project, schedule(project).placements, view, actual, style, theme)
    assert projection.window[1] == date(2026, 8, 5)


def test_executive_resources_match_owning_schemas():
    store = {}
    for path in (ROOT/'timeline-design/docs/schemas').glob('*.schema.yaml'):
        schema = yaml.safe_load(path.read_text()); store[schema['$id']] = schema
    resources = fixture()
    for name, value in [('view', resources[2]), ('theme', resources[4]), ('layout-profile', resources[5])]:
        schema = yaml.safe_load((ROOT/f'timeline-design/docs/schemas/{name}-v0.1.schema.yaml').read_text())
        validator = Draft202012Validator(schema, resolver=RefResolver.from_schema(schema, store=store))
        assert not list(validator.iter_errors(value))
