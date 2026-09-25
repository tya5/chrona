#!/usr/bin/env python3
"""Run independent conformance checks and report every result deterministically."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Callable, Iterable
import json
import subprocess
import sys

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parent
REPOSITORY = ROOT.parent
OUTPUT_LIMIT = 12_000


@dataclass(frozen=True)
class CheckSpec:
    """One static conformance command and its explicit prerequisite ids."""

    check_id: str
    argv: tuple[str, ...]
    prerequisites: tuple[str, ...] = ()


@dataclass(frozen=True)
class CheckResult:
    """The bounded, reviewable outcome of one conformance check."""

    check_id: str
    argv: tuple[str, ...]
    status: str
    returncode: int | None
    elapsed_ms: int
    stdout: str = ""
    stderr: str = ""
    skip_reason: str | None = None


def configure_stdout(stream: object) -> None:
    """Use one portable transport for aggregate Unicode check output."""
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")


def _command(path: str, *args: str) -> tuple[str, ...]:
    return (sys.executable, str(REPOSITORY / path), *args)


CHECKS = (
    CheckSpec("schema-inventory", _command("tools/schema_inventory.py")),
    CheckSpec("schema-annotations", _command("tools/schema_annotations.py")),
    CheckSpec("schema-references", _command("tools/validate_schema_references.py")),
    CheckSpec("example-inventory", _command("tools/example_inventory.py")),
    CheckSpec("scene-perceptibility", _command("tools/check_scene_perceptibility.py")),
    CheckSpec("diagnostic-inventory", _command("tools/diagnostic_inventory.py", "--check")),
    CheckSpec("layout-float-accumulation", _command("tools/check_layout_float_accumulation.py")),
    CheckSpec("declared-value-inventory", _command("tools/declared_value_inventory.py", "--check")),
    CheckSpec("vocabulary-inventory", _command("tools/vocabulary_inventory.py", "--check")),
    CheckSpec("documented-commands", _command("tools/check_documented_commands.py", "--check", "--execute")),
    CheckSpec("core-conformance", _command("conformance/validate_conformance.py")),
    CheckSpec("revision-store-conformance", _command("conformance/revision-store/validate_conformance.py")),
    CheckSpec("implementation-delivery", _command("conformance/validate_implementation_delivery_profile.py")),
    CheckSpec("traceability", _command("conformance/validate_traceability.py")),
    CheckSpec("design-recompletion", _command("conformance/validate_design_recompletion.py")),
    CheckSpec("review-detail-profile", _command("conformance/validate_review_detail_profile.py")),
    CheckSpec("profile-conformance", (sys.executable, str(Path(__file__).resolve()), "--profile-only")),
    CheckSpec("module-reachability", _command("tools/check_module_reachability.py")),
    CheckSpec("scene-primitive-delivery", _command("tools/check_scene_primitive_delivery.py")),
    CheckSpec("view-dispatch-reachability", _command("tools/check_view_dispatch_reachability.py")),
    CheckSpec("semantic-registry-reachability", _command("tools/check_semantic_registry_reachability.py")),
    CheckSpec("import-direction", _command("tools/check_import_direction.py")),
    CheckSpec("text-encoding", _command("tools/check_text_encoding.py")),
    CheckSpec("presentation-coverage", _command("tools/presentation_coverage.py", "--check")),
    CheckSpec("semantic-realization-coverage", _command("tools/semantic_realization_coverage.py", "--check")),
)


def _bounded(value: str) -> str:
    if len(value) <= OUTPUT_LIMIT:
        return value
    marker = f"\n... output truncated after {OUTPUT_LIMIT} characters ...\n"
    retained = OUTPUT_LIMIT - len(marker)
    head = retained // 2
    tail = retained - head
    return value[:head] + marker + value[-tail:]


def _run_process(argv: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, check=False, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=REPOSITORY)


def run_checks(specs: Iterable[CheckSpec], *,
               run_process: Callable[[tuple[str, ...]], subprocess.CompletedProcess[str]] = _run_process,
               clock: Callable[[], float] = monotonic) -> tuple[CheckResult, ...]:
    """Run every independent static check and mark only declared dependencies skipped."""
    results: list[CheckResult] = []
    by_id: dict[str, CheckResult] = {}
    for spec in specs:
        failed = next((item for item in spec.prerequisites
                       if by_id.get(item) is None or by_id[item].status != "PASS"), None)
        if failed is not None:
            result = CheckResult(spec.check_id, spec.argv, "SKIP", None, 0,
                                 skip_reason=f"prerequisite={failed}")
        else:
            started = clock()
            completed = run_process(spec.argv)
            elapsed = max(0, round((clock() - started) * 1000))
            result = CheckResult(spec.check_id, spec.argv,
                                 "PASS" if completed.returncode == 0 else "FAIL",
                                 completed.returncode, elapsed,
                                 _bounded(completed.stdout), _bounded(completed.stderr))
        results.append(result)
        by_id[spec.check_id] = result
    return tuple(results)


def _render_argv(argv: tuple[str, ...]) -> str:
    return json.dumps(list(argv), ensure_ascii=False)


def render_results(results: Iterable[CheckResult]) -> str:
    """Render headers, captured reports, and a stable final summary."""
    rows = tuple(results)
    lines: list[str] = []
    for result in rows:
        lines.append(f"\n== {result.check_id} ==")
        lines.append("argv: " + _render_argv(result.argv))
        if result.status == "SKIP":
            lines.append("SKIP: " + str(result.skip_reason))
            continue
        if result.stdout:
            lines.extend(("stdout:", result.stdout.rstrip()))
        if result.stderr:
            lines.extend(("stderr:", result.stderr.rstrip()))
        lines.append(f"status: {result.status} ({result.elapsed_ms}ms, exit={result.returncode})")
    lines.extend(("", "Conformance summary", "CHECK | STATUS | ELAPSED | DETAIL", "--- | --- | ---: | ---"))
    for result in rows:
        detail = result.skip_reason or ("—" if result.status == "PASS" else f"exit={result.returncode}")
        lines.append(f"{result.check_id} | {result.status} | {result.elapsed_ms}ms | {detail}")
    return "\n".join(lines)


def _profile_conformance() -> int:
    profile_schema = yaml.safe_load((REPOSITORY / "schemas/profile-v0.3.schema.yaml").read_text(encoding="utf-8"))
    profile_fixture = yaml.safe_load((ROOT / "semiconductor-profile-v0.2.yaml").read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(profile_schema).iter_errors(profile_fixture))
    if errors:
        print("Profile conformance: FAIL", file=sys.stderr)
        print("\n".join(error.message for error in errors), file=sys.stderr)
        return 1
    print("Profile conformance: PASS")
    return 0


def main(argv: tuple[str, ...] = tuple(sys.argv[1:])) -> int:
    if argv == ("--profile-only",):
        return _profile_conformance()
    if argv:
        raise SystemExit("E_CONFORMANCE_ARGUMENT")
    configure_stdout(sys.stdout)
    results = run_checks(CHECKS)
    print(render_results(results))
    if any(result.status == "FAIL" for result in results):
        return 1
    print("Chrona conformance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
