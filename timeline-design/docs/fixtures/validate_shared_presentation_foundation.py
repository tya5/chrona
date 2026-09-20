"""Design-fixture validation; no renderer behavior is asserted here."""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
schema = json.loads((ROOT / 'schemas/shared-presentation-foundation-v0.1.schema.json').read_text())
fixture = json.loads((ROOT / 'fixtures/shared-presentation-foundation-v0.1.json').read_text())
invalid = json.loads((ROOT / 'fixtures/shared-presentation-foundation-invalid-v0.1.json').read_text())

errors = sorted(Draft202012Validator(schema).iter_errors(fixture), key=lambda error: list(error.path))
if errors:
    raise SystemExit('invalid shared-presentation-foundation fixture: ' + '; '.join(error.message for error in errors))
if fixture['scale']['levels'][-1] not in {'week', 'day'}:
    raise SystemExit('fixture must exercise a fine axis level')
if fixture['annotations']['leader'] != 'orthogonal-or-none' or fixture['routing']['annotationLeader'] != 'presentation-orthogonal':
    raise SystemExit('annotation leader and routing ownership disagree')
if fixture['owners']['scene'] != 'derived' or fixture['owners']['geometry'] != 'layout':
    raise SystemExit('scene/layout ownership disagree')
if not list(Draft202012Validator(schema).iter_errors(invalid)):
    raise SystemExit('invalid fixture unexpectedly passed schema validation')
print('shared-presentation-foundation fixture valid')
