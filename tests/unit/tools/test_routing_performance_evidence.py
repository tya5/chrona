import json

import pytest

from chrona.usecases.materialize import MaterializationError
from tools import routing_performance_evidence as evidence
from tools.routing_performance_evidence import route_delta


def scene(*paths):
    return {'surfaces': [{'id': 'surface', 'primitives': [
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


def test_resolution_counts_ignore_halos_and_count_paired_stubs_once():
    value = scene(('normal', [(0, 0), (3, 0)]),
                  ('relation:opaque-a', [(0, 0), (1, 0)]), ('relation:opaque-b', [(2, 0), (3, 0)]))
    value['surfaces'][0]['id'] = 'surface'
    value['surfaces'][0]['primitives'].append({
        'id': 'normal:halo', 'kind': 'Path', 'sourceKind': 'decoration', 'points': [(0, 0), (3, 0)]})
    value['diagnostics'] = [
        'I_LAYOUT_RELATION_RESOLUTION:' + json.dumps({
            'surfaceId': 'surface', 'relationId': 'r', 'stage': 'stub', 'critical': True,
            'fragmentIds': ['relation:opaque-a', 'relation:opaque-b']}),
        'I_LAYOUT_RELATION_RESOLUTION_SUMMARY:' + json.dumps({
            'surfaceId': 'surface', 'count': 1, 'stages': {'stub': 1}})]
    result, = evidence.resolution_counts(value)
    assert result['relationInstances'] == 2
    assert result['stages']['normal'] == result['stages']['stub'] == 1
    value['surfaces'][0]['primitives'].pop(2)
    with pytest.raises(ValueError, match='no complete projected relation'):
        evidence.resolution_counts(value)


def test_resolution_summary_cannot_inflate_the_completed_count():
    value = scene(('r', [(0, 0), (3, 0)]))
    value['surfaces'][0]['id'] = 'surface'
    value['diagnostics'] = ['I_LAYOUT_RELATION_RESOLUTION_SUMMARY:' + json.dumps({
        'surfaceId': 'surface', 'count': 1, 'stages': {'overlap': 1}})]
    with pytest.raises(ValueError, match='summary disagrees'):
        evidence.resolution_counts(value)


def test_stub_receipts_without_explicit_fragment_ids_are_rejected():
    value = scene(('r:stub-source', [(0, 0), (1, 0)]), ('r:stub-target', [(2, 0), (3, 0)]))
    value['surfaces'][0]['id'] = 'surface'
    value['diagnostics'] = [
        'I_LAYOUT_RELATION_RESOLUTION:' + json.dumps({
            'surfaceId': 'surface', 'relationId': 'r', 'stage': 'stub', 'critical': True}),
        'I_LAYOUT_RELATION_RESOLUTION_SUMMARY:' + json.dumps({
            'surfaceId': 'surface', 'count': 1, 'stages': {'stub': 1}})]
    with pytest.raises(ValueError, match='explicit fragment identity'):
        evidence.resolution_counts(value)


def test_characterization_uses_real_materializer_and_records_only_evidence_mismatch(tmp_path, monkeypatch):
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
    def materializer(manifest_path, slide_id, output, *, write):
        assert not write and manifest_path == manifest and slide_id == 'synthetic'
        output.mkdir(parents=True)
        (output / 'review.svg').write_bytes(svg)
        (output / 'review.scene.json').write_bytes(serialized)
        raise MaterializationError('E_MATERIALIZER_MISMATCH')
    monkeypatch.setattr(evidence, 'materialize', materializer)
    result = evidence.characterize((manifest, 'synthetic', tmp_path / 'output'))
    assert result['sceneIdentical'] and result['svgIdentical'] and result['expectedMismatch']
    def broken(*args, **kwargs):
        raise MaterializationError('E_CONTENT_IDENTITY')
    monkeypatch.setattr(evidence, 'materialize', broken)
    with pytest.raises(MaterializationError, match='E_CONTENT_IDENTITY'):
        evidence.characterize((manifest, 'synthetic', tmp_path / 'broken'))
