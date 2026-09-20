"""Regression coverage for declarative slide presentation, not sample dates."""
from copy import deepcopy

import pytest
import yaml

from test_gantt_surface import ROOT, CAPS, fixture, elements
from chrona.review_svg import build_review_projection, render_table_timeline_svg
from chrona.scheduler import schedule


def render(settings):
    project, actual, view, style, theme, profile = fixture()
    projection = build_review_projection(project, schedule(project).placements, view, actual, style, theme)
    return render_table_timeline_svg(project['project']['title'], projection, project, view, theme, CAPS, profile, settings=settings)


@pytest.fixture
def settings():
    return yaml.safe_load((ROOT/'examples/controller-z/variants/editorial/settings.yaml').read_text())


def test_group_paint_object_and_opacity(settings):
    settings['theme']['groupPaints']['fw-team'] = {'color': '#123456', 'opacity': .42}
    original = deepcopy(settings)
    svg = render(settings)
    group = next(e for e in elements(svg, 'group-surface') if e.get('data-source-ref') == 'fw-team')
    assert group.get('fill') == '#123456' and group.get('opacity') == '0.42'
    assert settings == original
    assert render(settings) == svg


def test_templates_escape_and_preserve_semantics(settings):
    before = render(settings)
    settings['detail']['title'] = 'Review <&> {title}'
    settings['theme']['typography']['heading']['size'] = 30
    settings['detail']['subtitle'] = '{windowStart} / {selectedCount} selected'
    settings['detail']['legend'][0]['label'] = 'Baseline <&>'
    settings['theme']['typography']['legend']['size'] = 18
    after = render(settings)
    assert elements(after, 'heading')[0].text.startswith('Review <&> Controller Z')
    assert elements(after, 'subtitle')[0].text == 'Feb 2026 / 8 selected'
    assert elements(after, 'legend-label')[0].text == 'Baseline <&>'
    assert elements(after, 'legend-label')[0].get('font-size') == '18'
    for purpose in ('planned', 'actual', 'variance', 'routed-connector'):
        assert [(e.attrib, e.text) for e in elements(before, purpose)] == [(e.attrib, e.text) for e in elements(after, purpose)]


def test_subtitle_visibility_and_legend_overflow(settings):
    settings['layout']['title']['showSubtitle'] = False
    assert not elements(render(settings), 'subtitle')
    settings['detail']['legend'][0]['label'] = 'Overflow ' * 200
    with pytest.raises(ValueError, match='E_LAYOUT_REQUIRED_OVERFLOW:legend'):
        render(settings)


def test_legend_spacing_is_measured(settings):
    original = elements(render(settings), 'legend-label')
    settings['detail']['legend'][0]['label'] = 'Approved baseline plan'
    changed = elements(render(settings), 'legend-label')
    assert float(changed[1].get('x')) > float(original[1].get('x'))
