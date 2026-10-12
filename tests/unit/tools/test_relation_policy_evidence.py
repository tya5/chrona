import json

import pytest

from chrona.usecases.materialize import MaterializationError
from tools import relation_policy_evidence as evidence
from tools.relation_policy_evidence import route_delta


def scene(*paths):
    return {'surfaces': [{'primitives': [
        {'id': identifier, 'kind': 'Path', 'sourceKind': 'relation', 'points': points}
        for identifier, points in paths]}]}


def test_route_deltas_include_changed_added_removed_and_signed_metrics():
    before = scene(('same', [(0, 0), (3, 0)]), ('removed', [(0, 0), (2, 0)]),
                   ('changed', [(0, 0), (0, 4), (3, 4)]))
    after = scene(('same', [(0, 0), (3, 0)]), ('added', [(0, 0), (1, 0)]),
                  ('changed', [(0, 0), (3, 0)]))
    assert route_delta(before, after) == {'routesChanged': 3, 'routesAdded': 1,
        'routesRemoved': 1, 'bendsDelta': -1, 'lengthDelta': -5}


def test_unchanged_routes_have_zero_delta():
    value = scene(('relation:synthetic', [(0, 0), (3, 0)]))
    assert not any(route_delta(value, value).values())


@pytest.mark.parametrize('policy', ('default', 'best', 'first-fit'))
def test_characterization_pins_only_normalization_and_accepts_only_evidence_mismatch(tmp_path, monkeypatch, policy):
    project = tmp_path / 'synthetic'
    project.mkdir()
    manifest = project / 'manifest.yaml'
    manifest.write_text('slides:\n  - id: synthetic\n    expectedSvg: before.svg\n    expectedScene: before.scene.json\n')
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"/>'
    value = scene(('relation:synthetic', [(0, 0), (3, 0)]))
    value['diagnostics'] = []
    serialized = json.dumps(value).encode()
    (project / 'before.svg').write_bytes(svg)
    (project / 'before.scene.json').write_bytes(serialized)
    monkeypatch.setattr(evidence.engine, 'LayoutManifest', lambda **kwargs: kwargs)
    original = evidence.engine.LayoutManifest
    def materializer(manifest_path, slide_id, output, *, write):
        assert not write and manifest_path == manifest and slide_id == 'synthetic'
        selected = 'ignored' if policy == 'default' else policy
        assert evidence.engine.LayoutManifest(relation_search='ignored') == {'relation_search': selected}
        output.mkdir(parents=True)
        (output / 'review.svg').write_bytes(svg)
        (output / 'review.scene.json').write_bytes(serialized)
        raise MaterializationError('E_MATERIALIZER_MISMATCH')
    monkeypatch.setattr(evidence, 'materialize', materializer)
    result = evidence.characterize((manifest, 'synthetic', policy, tmp_path / 'output'))
    assert result['sceneIdentical'] and result['svgIdentical'] and result['expectedMismatch']
    assert evidence.engine.LayoutManifest is original
    def broken(*args, **kwargs):
        raise MaterializationError('E_CONTENT_IDENTITY')
    monkeypatch.setattr(evidence, 'materialize', broken)
    with pytest.raises(MaterializationError, match='E_CONTENT_IDENTITY'):
        evidence.characterize((manifest, 'synthetic', policy, tmp_path / 'broken'))
