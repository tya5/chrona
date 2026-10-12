"""Batch actual public materializers without policy or normalization overrides."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from chrona.presentation.layout.routing import route_quality_metrics
from chrona.presentation.model.info_diagnostics import RelationResolutionStage
from chrona.resources import safe_load
from chrona.usecases.materialize import MaterializationError, materialize
from tools.derived_evidence import manifest_targets


def routes(scene):
    return {item['id']: item for surface in scene['surfaces'] for item in surface['primitives']
            if item.get('sourceKind') == 'relation' and item['kind'] == 'Path'}


def route_delta(before, after):
    left, right = routes(before), routes(after)
    keys = left.keys() | right.keys()
    geometry = ('points', 'pathCommands', 'markerStart', 'markerEnd')
    changed = sum(key not in left or key not in right or
                  any(left[key].get(field) != right[key].get(field) for field in geometry)
                  for key in keys)
    def metrics(values):
        measured = [route_quality_metrics(tuple(tuple(point) for point in item['points']))
                    for item in values.values()]
        return sum(item[0] for item in measured), sum(item[2] for item in measured)
    old_length, old_bends = metrics(left)
    new_length, new_bends = metrics(right)
    return {'routesChanged': changed, 'routesAdded': len(right.keys() - left.keys()),
            'routesRemoved': len(left.keys() - right.keys()),
            'bendsDelta': new_bends - old_bends, 'lengthDelta': new_length - old_length}


def resolution_counts(scene):
    """Count final instances, not halo primitives, fragments or search passes."""
    receipts = [json.loads(value.split(':', 1)[1]) for value in scene.get('diagnostics', ())
                if value.startswith('I_LAYOUT_RELATION_RESOLUTION:')]
    summaries = [json.loads(value.split(':', 1)[1]) for value in scene.get('diagnostics', ())
                 if value.startswith('I_LAYOUT_RELATION_RESOLUTION_SUMMARY:')]
    result = []
    for surface in scene['surfaces']:
        surface_id = surface['id']
        facts = [item for item in receipts if item['surfaceId'] == surface_id]
        identifiers = {item['id'] for item in surface['primitives']
                       if item.get('sourceKind') == 'relation' and item['kind'] == 'Path'}
        counts = {stage.value: 0 for stage in RelationResolutionStage}
        covered = set()
        seen = set()
        for fact in facts:
            stage = RelationResolutionStage(fact['stage'])
            relation_id = fact['relationId']
            if stage is RelationResolutionStage.NORMAL or relation_id in seen:
                raise ValueError('invalid or duplicate completed recovery receipt')
            seen.add(relation_id)
            paths = ({relation_id + ':stub-source', relation_id + ':stub-target'}
                     if stage is RelationResolutionStage.STUB else {relation_id})
            if not paths <= identifiers:
                raise ValueError('recovery receipt has no complete projected relation')
            covered.update(paths)
            counts[stage.value] += 1
        actual = {stage: count for stage, count in counts.items() if count}
        reported = [item for item in summaries if item['surfaceId'] == surface_id]
        expected = [{'surfaceId': surface_id, 'count': len(facts), 'stages': actual}] if facts else []
        if reported != expected:
            raise ValueError('completed recovery summary disagrees with instance receipts')
        counts['normal'] = len(identifiers - covered)
        result.append({'surfaceId': surface_id, 'relationInstances': sum(counts.values()),
                       'stages': counts})
    if any(item['surfaceId'] not in {s['id'] for s in scene['surfaces']} for item in (*receipts, *summaries)):
        raise ValueError('recovery receipt has no projected surface')
    return result


def characterize(task):
    manifest_path, slide_id, root = task
    manifest = safe_load(manifest_path.read_bytes())
    slide = next(item for item in manifest['slides'] if item['id'] == slide_id)
    output = root / manifest_path.parent.name / slide_id
    mismatch = False
    try:
        materialize(manifest_path, slide_id, output, write=False)
    except MaterializationError as error:
        if error.code != 'E_MATERIALIZER_MISMATCH':
            raise
        # Record a real mismatch for inspection; never normalize it away.
        mismatch = True
    svg = (output / 'review.svg').read_bytes()
    scene_bytes = (output / 'review.scene.json').read_bytes()
    ET.fromstring(svg)
    scene = json.loads(scene_bytes)
    expected_svg = (manifest_path.parent / slide['expectedSvg']).read_bytes()
    expected_bytes = (manifest_path.parent / slide['expectedScene']).read_bytes()
    baseline = json.loads(expected_bytes)
    return {'slide': manifest_path.parent.name + '/' + slide_id,
            'sceneIdentical': scene_bytes == expected_bytes, 'svgIdentical': svg == expected_svg,
            'sceneSha256': sha256(scene_bytes).hexdigest(), 'svgSha256': sha256(svg).hexdigest(),
            'expectedMismatch': mismatch, **route_delta(baseline, scene),
            'resolutionCounts': resolution_counts(scene),
            'newDiagnostics': sorted(set(scene['diagnostics']) - set(baseline['diagnostics'])),
            'removedDiagnostics': sorted(set(baseline['diagnostics']) - set(scene['diagnostics']))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    root = args.output_dir.resolve()
    if root.exists() and any(root.iterdir()):
        parser.error('output directory must be empty')
    root.mkdir(parents=True, exist_ok=True)
    tasks = [(manifest, slide, root) for manifest, slide in manifest_targets()]
    results = []
    with ProcessPoolExecutor(max_workers=args.jobs) as executor:
        for result in executor.map(characterize, tasks):
            results.append(result)
            print(result['slide'], 'changed', result['routesChanged'], flush=True)
    (root / 'materializer-evidence.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    print('Byte-identical:', sum(item['sceneIdentical'] and item['svgIdentical'] for item in results),
          '/', len(results), flush=True)
    return int(any(not item['sceneIdentical'] or not item['svgIdentical'] for item in results))


if __name__ == '__main__':
    raise SystemExit(main())
