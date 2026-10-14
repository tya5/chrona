"""Manual: run when changing Layout allocation; validate every viewport outcome."""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Any, Callable, Iterable, TypeVar

import yaml

from chrona.presentation.model.closure import resolve_render_context
from chrona.resources import safe_load
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.storage.snapshot_paths import snapshot_directory
from chrona.usecases.materialize import _OverlayBuilder, copy_context_closure
from chrona.usecases.render_review import RenderRequest, render_review
from chrona.usecases.failure_report import report_failure


ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = ((1600, 900), (800, 450), (600, 340))
_Input = TypeVar("_Input")
_Output = TypeVar("_Output")


class CliRenderFailure(RuntimeError):
    def __init__(self, outcome: dict[str, Any]):
        super().__init__(json.dumps(outcome, sort_keys=True))
        self.outcome = outcome


def _load_expectations() -> dict[str, dict[str, Any]]:
    records = safe_load((ROOT / "tools/draft_viewport_expected_refusals.yaml").read_bytes())
    expectations: dict[str, dict[str, Any]] = {}
    for record in records:
        assert record["successor"] == "https://github.com/tya5/chrona/issues/1490"
        for identifier in record["cases"]:
            assert identifier not in expectations, f"duplicate expected refusal: {identifier}"
            expectations[identifier] = record["outcome"]
    return expectations


def _failure_outcome(error: Exception) -> dict[str, Any]:
    if isinstance(error, CliRenderFailure):
        return error.outcome
    report = report_failure(error)
    return {**report.payload(), "exitCode": report.exit_code}


def _outcome_mismatch(identifier: str, outcome: dict[str, Any] | None,
                      expectations: dict[str, dict[str, Any]]) -> str | None:
    expected = expectations.get(identifier)
    if outcome == expected:
        return None
    return (f"{identifier}: expected {json.dumps(expected, sort_keys=True)}, "
            f"observed {json.dumps(outcome, sort_keys=True)}")


def _content_identity(payload: bytes) -> str:
    return "sha256:" + sha256(payload).hexdigest()


def _derive_viewport_context(context: dict[str, Any], original_reference: dict[str, Any],
                             context_path: Path, viewport: tuple[int, int],
                             overlay_builder: _OverlayBuilder) -> tuple[dict[str, Any], bytes]:
    """Stage one immutable Context derivative, retaining every authored input reference."""
    width, height = viewport
    derived = deepcopy(context)
    context_id = f"{context['id']}-viewport-{width}x{height}"
    derived["id"] = context_id
    derived["body"]["environment"]["viewport"] = {
        "inlineSize": width,
        "blockSize": height,
    }
    payload = yaml.safe_dump(derived, sort_keys=False, allow_unicode=True).encode("utf-8")
    address = (Path("contexts") / "_viewport_matrix" /
               f"{context_path.stem}-{width}x{height}.yaml").as_posix()
    reference = {
        **original_reference,
        "id": context_id,
        "address": address,
        "contentIdentity": _content_identity(payload),
    }
    overlay_builder.add_reference(reference, payload)
    return reference, payload


def _render_api(reference: dict[str, Any], overlay: Any, decoded_catalogs: dict[str, Any],
                snapshot: Path) -> Any:
    closure = resolve_render_context(reference, overlay, decoded_resources=decoded_catalogs)
    return render_review(RenderRequest(
        closure, snapshot, ReferenceScheduler(), require_all_inputs_read=True,
        asset_resolver=overlay,
    ))


def _render_cli(reference: dict[str, Any], payload: bytes, snapshot: Path,
                directory: Path, viewport: tuple[int, int]) -> tuple[bytes, int]:
    """Exercise the public saved-Context command against the same verified snapshot."""
    revision = reference["revision"]["token"]
    target = snapshot_directory(snapshot, revision) / reference["address"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    reference_path = directory / f"context-reference-{viewport[0]}x{viewport[1]}.yaml"
    reference_path.write_text(yaml.safe_dump(reference, sort_keys=False), encoding="utf-8")
    output = directory / f"render-{viewport[0]}x{viewport[1]}.svg"
    command = [
        sys.executable, "-m", "chrona", "render-review", "--context-reference", str(reference_path),
        "--snapshot-root", str(snapshot), "--store-identity", reference["store"]["identity"],
        "--reject-unused-closure-inputs",
        # Original resources can be unpinned. copy_context_closure has read and
        # staged their authored bytes; the newly-derived Context itself is pinned.
        "--allow-missing-content-identity", "--output", str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            raise RuntimeError(f"chrona render-review exit={result.returncode}: {result.stderr or result.stdout}")
        if result.stderr or not isinstance(payload, dict) or set(payload) != {"status", "diagnostics"}:
            raise RuntimeError(f"unexpected CLI failure output: {result.stderr or result.stdout}")
        raise CliRenderFailure({**payload, "exitCode": result.returncode})
    artifact = output.read_bytes()
    warning_count = (result.stdout + result.stderr).count("W_LAYOUT_")
    return artifact, warning_count


def _validate_artifact(artifact: bytes) -> tuple[float, float, float, float]:
    assert artifact.startswith(b"<svg "), "no SVG artifact"
    view_box = re.search(rb'viewBox="([^\"]+)"', artifact)
    assert view_box is not None, "SVG lacks completed viewBox"
    bounds = tuple(float(value) for value in view_box.group(1).split())
    assert len(bounds) == 4
    return bounds  # type: ignore[return-value]


def _ordered_map(worker: Callable[[_Input], _Output], tasks: Iterable[_Input],
                 jobs: int) -> tuple[_Output, ...]:
    """Run independent groups in parallel while preserving input order."""
    if jobs == 1:
        return tuple(map(worker, tasks))
    with ProcessPoolExecutor(max_workers=jobs) as executor:
        return tuple(executor.map(worker, tasks))


def _survey_context(task: tuple[Path, bool]) -> tuple[int, int, int, tuple[str, ...]]:
    """Survey all viewport cases for one Context using isolated temporary state."""
    context_path, use_cli = task
    expectations = _load_expectations()
    example = context_path.parent.parent
    context = safe_load(context_path.read_bytes())
    with TemporaryDirectory(prefix="chrona-1474-viewport-") as temporary:
        directory = Path(temporary)
        snapshot = directory / "snapshot"
        snapshot.mkdir()
        overlay_builder = _OverlayBuilder(directory / "overlay")
        decoded_catalogs: dict[str, Any] = {}
        try:
            original_reference, _revision = copy_context_closure(
                example, context_path, snapshot, decoded_catalogs=decoded_catalogs,
                overlay_builder=overlay_builder,
            )
        except Exception as error:
            failures = tuple(
                f"{example.name}/{context_path.stem}@{width}x{height}: "
                f"closure copy {type(error).__name__}: {error}"
                for width, height in VIEWPORTS
            )
            return 0, 0, 0, failures

        completed = 0
        warning_count = 0
        refused = 0
        failures: list[str] = []
        for viewport in VIEWPORTS:
            identifier = f"{example.name}/{context_path.stem}@{viewport[0]}x{viewport[1]}"
            try:
                reference, payload = _derive_viewport_context(
                    context, original_reference, context_path, viewport, overlay_builder,
                )
                overlay = overlay_builder.finish()
                if use_cli:
                    artifact, warnings = _render_cli(reference, payload, snapshot, directory, viewport)
                    _validate_artifact(artifact)
                    warning_count += warnings
                else:
                    rendered = _render_api(reference, overlay, decoded_catalogs, snapshot)
                    serialized_bounds = _validate_artifact(rendered.artifact.content)
                    assert all(abs(actual - serialized) < .0011 for actual, serialized in
                               zip(rendered.surface.canvas_bounds, serialized_bounds, strict=True)), (
                        "SVG viewBox differs from completed Layout canvas")
                    warning_count += len(rendered.surface.fit_warnings)
                completed += 1
                mismatch = _outcome_mismatch(identifier, None, expectations)
                if mismatch is not None:
                    failures.append(mismatch)
            except Exception as error:
                mismatch = _outcome_mismatch(identifier, _failure_outcome(error), expectations)
                if mismatch is None:
                    refused += 1
                else:
                    failures.append(mismatch)
        return completed, refused, warning_count, tuple(failures)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", action="store_true", help="exercise each saved-Context render-review exit code")
    parser.add_argument("--jobs", type=int, default=1, help="Context groups to render in parallel")
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    failures: list[str] = []
    completed = 0
    refused = 0
    warning_count = 0
    contexts = tuple(sorted(ROOT.glob("examples/*/contexts/*.yaml")))
    identifiers = {f"{path.parent.parent.name}/{path.stem}@{width}x{height}"
                   for path in contexts for width, height in VIEWPORTS}
    for missing in sorted(_load_expectations().keys() - identifiers):
        failures.append(f"{missing}: expected refusal case is missing")
    results = _ordered_map(_survey_context, ((path, args.cli) for path in contexts), args.jobs)
    for group_completed, group_refused, group_warnings, group_failures in results:
        completed += group_completed
        refused += group_refused
        warning_count += group_warnings
        failures.extend(group_failures)
    for failure in failures:
        print(failure)
    print(f"draft viewport matrix ({'CLI' if args.cli else 'API'}): {completed}/{len(identifiers)} rendered; "
          f"{refused} expected refusals; {warning_count} fit warnings; {len(failures)} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
