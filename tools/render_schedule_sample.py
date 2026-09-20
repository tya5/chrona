"""Render a manifest of existing Chrona resources, without sample-specific layout."""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from chrona.presentation.model.settings import resolve_presentation_settings
from chrona.presentation.model.projection import build_review_projection
from chrona.presentation.review.svg import render_table_timeline_svg
from chrona.scheduling.scheduler import schedule

CAPABILITIES = {'sourceMetadata', 'accessibleText', 'semanticRoles', 'marker', 'tableSemantics', 'hierarchicalAxis'}


def render_manifest(path: Path, raster: bool = True):
    def load(name):
        return yaml.safe_load((path.parent / name).read_text())
    manifest = yaml.safe_load(path.read_text())
    project, actual = load(manifest['project']), load(manifest['actual'])
    style, theme, profile = (load(manifest[key]) for key in ('style', 'theme', 'profile'))
    original = deepcopy((project, actual))
    result = schedule(project)
    if not result.ok:
        raise ValueError(result.diagnostics)
    reports = []
    preview_images = []
    for slide in manifest['slides']:
        view = load(slide['view'])
        settings = resolve_presentation_settings(load(slide['settings']))
        projection = build_review_projection(project, result.placements, view, actual, style, theme)
        render = lambda: render_table_timeline_svg(project['project']['title'], projection, project, view, theme, CAPABILITIES, profile, settings=settings)
        svg = render()
        if svg != render():
            raise AssertionError('E_PRESENTATION_NONDETERMINISTIC')
        output = path.parent / slide['output']
        output.write_text(svg)
        viewport = settings['context']['viewport']
        if viewport['width'] * 9 == viewport['height'] * 16:
            encoded = base64.b64encode(svg.encode()).decode()
            preview_images.append('<section><img alt="Schedule slide" src="data:image/svg+xml;base64,' + encoded + '"></section>')
        if raster:
            env = dict(os.environ)
            env['NODE_PATH'] = env.get('CODEX_PRIMARY_RUNTIME_NODE_MODULES', env.get('NODE_PATH', ''))
            preview = path.parent / slide.get('preview', str(Path(slide['output']).with_suffix('.png')))
            subprocess.run(['node', str(ROOT/'tools/verify-gantt-svg.cjs'), str(output), str(preview)], check=True, env=env)
        selected = {item.object_id for item in projection.items}
        reports.append({'file': output.name, 'items': len(selected), 'visibleDependencies': sum(edge['from']['object'] in selected and edge['to']['object'] in selected for edge in project['relations']), 'observedItems': sum(bool(item.actual) for item in projection.items), 'unmatchedObservations': len(projection.unmatched_actual_ids)})
    if (project, actual) != original:
        raise AssertionError('E_INPUT_MUTATED')
    if manifest.get('gallery'):
        gallery = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Schedule slides</title><style>body{margin:0;background:#080f19}section{max-width:1600px;margin:24px auto}img{display:block;width:100%;height:auto}@page{size:landscape;margin:0}@media print{section{margin:0;break-after:page}body{background:white}}</style><body>' + ''.join(preview_images) + '</body></html>'
        (path.parent / manifest['gallery']).write_text(gallery)
    return reports


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--no-raster', action='store_true')
    args = parser.parse_args()
    print(json.dumps(render_manifest(args.manifest, not args.no_raster), indent=2))
