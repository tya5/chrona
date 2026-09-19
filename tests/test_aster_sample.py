"""The complex sample exercises existing semantics rather than a custom renderer."""
from copy import deepcopy
from datetime import date
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import pytest
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from chrona.presentation_settings import resolve_presentation_settings
from chrona.review_svg import build_review_projection, render_table_timeline_svg
from chrona.scheduler import schedule

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT/'examples/aster-ssd'
CAPS = {'sourceMetadata', 'accessibleText', 'semanticRoles', 'marker', 'tableSemantics', 'hierarchicalAxis'}


def load(name):
    return yaml.safe_load((SAMPLE/name).read_text())


def test_program_semantics_and_work_calendars():
    project = load('project.yaml'); original = deepcopy(project)
    result = schedule(project)
    assert result.ok, result.diagnostics
    assert len(result.placements) == 24 and len(project['relations']) == 28
    p = result.placements
    assert p['boot']['end'] == date(2027, 2, 17)  # Excludes configured closure.
    assert p['ftl']['start'] < p['boot']['end']  # Start-to-start overlap.
    assert (p['endurance']['end'] - p['endurance']['start']).days == 42
    assert p['integration']['start'] == date(2027, 5, 31)  # Three-way convergence.
    assert p['pilot']['start'] == date(2027, 7, 12)  # Factory Saturday closure.
    assert p['yield']['start'].weekday() == 5  # Factory calendar works Saturdays.
    assert p['compliance']['end'] <= date(2027, 7, 2)
    assert project == original


def test_detail_views_partition_project_and_master_covers_everything():
    project = load('project.yaml')
    slides = load('manifest.yaml')['slides']
    ids = [i for slide in slides[1:4] for i in load(slide['view'])['body']['selection']['include']['ids']]
    assert len(ids) == len(set(ids)) == 24
    assert set(ids) == set(project['objects'])
    assert set(load(slides[4]['view'])['body']['selection']['include']['ids']) == set(ids)


def test_resources_match_existing_schemas():
    schemas = [yaml.safe_load(path.read_text()) for path in (ROOT/'timeline-design/docs/schemas').glob('*.schema.yaml')]
    registry = Registry().with_resources((s['$id'], Resource.from_contents(s)) for s in schemas)
    for filename, kind in [('actual.yaml', 'actual-set'), ('style.yaml', 'style'), ('theme.yaml', 'theme'), ('profile.yaml', 'layout-profile')]:
        schema = yaml.safe_load((ROOT/f'timeline-design/docs/schemas/{kind}-v0.1.schema.yaml').read_text())
        Draft202012Validator(schema, registry=registry).validate(load(filename))
    schema = yaml.safe_load((ROOT/'timeline-design/docs/schemas/view-v0.1.schema.yaml').read_text())
    for slide in load('manifest.yaml')['slides']:
        Draft202012Validator(schema, registry=registry).validate(load(slide['view']))
        resolve_presentation_settings(load(slide['settings']))


@pytest.mark.parametrize('index', range(5))
def test_each_slide_reproduces_and_preserves_facts(index):
    project, actual = load('project.yaml'), load('actual.yaml')
    before = deepcopy((project, actual))
    slide = load('manifest.yaml')['slides'][index]
    view, settings = load(slide['view']), resolve_presentation_settings(load(slide['settings']))
    theme, style, profile = load('theme.yaml'), load('style.yaml'), load('profile.yaml')
    projection = build_review_projection(project, schedule(project).placements, view, actual, style, theme)
    svg = render_table_timeline_svg(project['project']['title'], projection, project, view, theme, CAPS, profile, settings=settings)
    assert svg == (SAMPLE/slide['output']).read_text()
    assert (project, actual) == before
    assert len(projection.unmatched_actual_ids) == 2
    if index in (1, 4):
        nand = next(item for item in projection.items if item.object_id == 'nand')
        assert nand.finish_delta == 5 and nand.actual['finish'] == date(2027, 3, 8)
    elements = list(ET.fromstring(svg).iter())
    selected = {item.object_id for item in projection.items}
    expected = {edge['id'] for edge in project['relations'] if edge['from']['object'] in selected and edge['to']['object'] in selected}
    assert {e.get('data-source-ref') for e in elements if e.get('data-purpose') == 'routed-connector'} == expected
    bars = [e for e in elements if e.get('data-purpose') in ('planned', 'actual') and e.tag.endswith('rect')]
    for edge in (e for e in elements if e.get('data-purpose') == 'routed-connector'):
        coords = list(map(float, re.findall(r'-?\d+(?:\.\d+)?', edge.get('d'))))
        points = list(zip(coords[::2], coords[1::2]))
        for a, b in zip(points, points[1:]):
            assert a[0] == b[0] or a[1] == b[1]
            for bar in bars:
                x, y, w, h = (float(bar.get(key)) for key in ('x', 'y', 'width', 'height'))
                horizontal = a[1] == b[1] and y+.02 < a[1] < y+h-.02 and max(a[0], b[0]) > x+.02 and min(a[0], b[0]) < x+w-.02
                vertical = a[0] == b[0] and x+.02 < a[0] < x+w-.02 and max(a[1], b[1]) > y+.02 and min(a[1], b[1]) < y+h-.02
                assert not (horizontal or vertical), (edge.get('data-source-ref'), bar.get('data-source-ref'))
