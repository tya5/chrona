#!/usr/bin/env python3
"""Validate release-package shape and the current-profile blocked disposition."""
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent
DOCS = ROOT.parent
package = yaml.safe_load((ROOT / "current-profile-release-package-v0.2.yaml").read_text())
schema = yaml.safe_load((DOCS / "schemas" / "release-package-v0.2.schema.yaml").read_text())
acceptance = yaml.safe_load((ROOT / "current-profile-release-acceptance-v0.2.yaml").read_text())
errors = list(Draft202012Validator(schema).iter_errors(package))
if errors:
    raise SystemExit("Release package: FAIL: " + "; ".join(error.message for error in errors))
if package["releaseId"] != acceptance["releaseId"] or package["evaluationIdentity"] != acceptance["inputClosure"]["evaluationIdentity"]:
    raise SystemExit("Release package: FAIL: package must bind acceptance release and evaluation")
if package["output"]["target"] != acceptance["output"]["target"] or package["output"]["targetVersion"] != acceptance["output"]["targetVersion"]:
    raise SystemExit("Release package: FAIL: package target must bind acceptance target")
excluded = [entry["id"] for entry in acceptance["useCases"] if entry["disposition"] == "excluded"]
if excluded and (package["status"] != "blocked" or package["artifact"]["contentIdentity"] is not None):
    raise SystemExit("Release package: FAIL: exclusions require blocked, artifact-free package")
if package["status"] == "blocked" and package["artifact"]["contentIdentity"] is not None:
    raise SystemExit("Release package: FAIL: blocked package must not carry an artifact")
print("Release package: PASS (current package is not published)")
