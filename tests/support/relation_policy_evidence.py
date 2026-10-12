"""Disposable public-materializer policy characterization; never edits examples.

The normalization override isolates routing behavior with unchanged resource
bytes/identities. This is NOT evidence of authored best declarations or their
provenance migration; those must be reviewed separately on the publication PR.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET

from chrona.presentation.layout import engine
from chrona.presentation.layout.routing import route_quality_metrics
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


def characterize(task):
    manifest_path, slide_id, policy, root = task
    manifest = safe_load(manifest_path.read_bytes())
    slide = next(item for item in manifest['slides'] if item['id'] == slide_id)
    original = engine.LayoutManifest
    def selected(*args, **kwargs):
        kwargs['relation_search'] = policy
        return original(*args, **kwargs)
    output = root / policy / manifest_path.parent.name / slide_id
    mismatch = False
    with patch.object(engine, 'LayoutManifest', side_effect=selected):
        try:
            materialize(manifest_path, slide_id, output, write=False)
        except MaterializationError as error:
            if error.code != 'E_MATERIALIZER_MISMATCH':
                raise
            # The real materializer has already serialized both artifacts.
            # Only comparison with committed evidence is intentionally changed.
            mismatch = True
    svg = (output / 'review.svg').read_bytes()
    scene_bytes = (output / 'review.scene.json').read_bytes()
    ET.fromstring(svg)
    scene = json.loads(scene_bytes)
    expected_svg = (manifest_path.parent / slide['expectedSvg']).read_bytes()
    expected_bytes = (manifest_path.parent / slide['expectedScene']).read_bytes()
    baseline = json.loads(expected_bytes)
    return {'slide': manifest_path.parent.name + '/' + slide_id, 'policy': policy,
            'sceneIdentical': scene_bytes == expected_bytes, 'svgIdentical': svg == expected_svg,
            'sceneSha256': sha256(scene_bytes).hexdigest(), 'svgSha256': sha256(svg).hexdigest(),
            'expectedMismatch': mismatch, **route_delta(baseline, scene),
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
    tasks = [(manifest, slide, policy, root) for policy in ('best', 'first-fit')
             for manifest, slide in manifest_targets()]
    results = []
    with ProcessPoolExecutor(max_workers=args.jobs) as executor:
        for result in executor.map(characterize, tasks):
            results.append(result)
            print(result['policy'], result['slide'], 'changed', result['routesChanged'], flush=True)
    (root / 'policy-evidence.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    best = [item for item in results if item['policy'] == 'best']
    print('Best byte-identical:', sum(item['sceneIdentical'] and item['svgIdentical'] for item in best),
          '/', len(best), flush=True)


if __name__ == '__main__':
    main()
