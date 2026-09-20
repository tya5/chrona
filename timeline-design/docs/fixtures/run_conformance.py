#!/usr/bin/env python3
"""Run Core and Presentation conformance entry points."""
from pathlib import Path
import subprocess, sys
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent
COMMANDS = [
    [sys.executable, str(ROOT / "validate_conformance.py")],
    [sys.executable, str(ROOT / "revision-store" / "validate_conformance.py")],
    [sys.executable, str(ROOT / "presentation" / "validate_conformance.py")],
    [sys.executable, str(ROOT / "validate_presentation_setting_consumption.py")],
    [sys.executable, str(ROOT / "federation" / "validate_conformance.py")],
    [sys.executable, str(ROOT / "validate_implementation_delivery_profile.py")],
    [sys.executable, str(ROOT / "validate_traceability.py")],
    [sys.executable, str(ROOT / "validate_release_acceptance.py")],
    [sys.executable, str(ROOT / "validate_ai_command_proposal.py")],
    [sys.executable, str(ROOT / "validate_release_package.py")],
    [sys.executable, str(ROOT / "validate_design_recompletion.py")],
    [sys.executable, str(ROOT / "validate_datetime_project.py")],
    [sys.executable, str(ROOT / "validate_successor_release_acceptance.py")],
    [sys.executable, str(ROOT / "validate_review_svg_profile.py")],
]
for command in COMMANDS:
    result = subprocess.run(command, check=False)
    if result.returncode:
        raise SystemExit(result.returncode)
docs = ROOT.parent
profile_schema = yaml.safe_load((docs / "schemas" / "profile-v0.1.schema.yaml").read_text())
profile_fixture = yaml.safe_load((ROOT / "semiconductor-profile-v0.1.yaml").read_text())
profile_errors = list(Draft202012Validator(profile_schema).iter_errors(profile_fixture))
if profile_errors:
    print("Profile conformance: FAIL", file=sys.stderr)
    print("\n".join(error.message for error in profile_errors), file=sys.stderr)
    raise SystemExit(1)
print("Profile conformance: PASS")
print("Chrona conformance: PASS")
