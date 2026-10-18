#!/usr/bin/env python3
"""One-off, scoped render-phase wall attribution probe for Chrona #1734.

The probe instruments only named Layout callables and candidate callbacks. It
does not change search inputs, ordering, limits, or selection. Run from a clean
Chrona checkout and its project environment with ``python /tmp/.../profile_render_phases.py
--output /tmp/profile.json -- <ordinary chrona CLI arguments>``. The recorded
``argv_paths_sha256`` covers only argv tokens resolving to files/directories;
implicit/default resources are not included. ``process_outcome`` reports only
process-level return/exit behavior. A normal CLI return does not establish
render success; inspect the raw CLI JSON report separately. ``--self-test``
never imports Chrona or renders.
"""
from __future__ import annotations

import argparse
import contextvars
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from types import ModuleType
from typing import Callable


class Frame:
    __slots__ = ("children",)

    def __init__(self) -> None:
        self.children = 0.0


class Ledger:
    def __init__(self, clock: Callable[[], float] = time.perf_counter) -> None:
        self.clock = clock
        self.context = contextvars.ContextVar("chrona_probe_context", default=("unclassified", "unspecified", None))
        self.values: dict[str, dict[str, float | int]] = {}

    def wrap(self, category: str, function: Callable, *,
             pass_value: Callable | None = None,
             stage_value: Callable | None = None,
             callbacks: tuple[str, ...] = ()) -> Callable:
        ledger = self

        def timed_call(callable_, args, kwargs, category_, pass_override=None, stage_override=None):
            old_pass, old_stage, parent = ledger.context.get()
            current_pass = pass_override if pass_override is not None else old_pass
            current_stage = stage_override if stage_override is not None else old_stage
            frame = Frame()
            token = ledger.context.set((current_pass, current_stage, frame))
            started = ledger.clock()
            try:
                return callable_(*args, **kwargs)
            finally:
                elapsed = max(0.0, ledger.clock() - started)
                exclusive = max(0.0, elapsed - frame.children)
                ledger.context.reset(token)
                if parent is not None:
                    parent.children += elapsed
                key = f"{current_pass}/{current_stage}/{category_}"
                record = ledger.values.setdefault(key, {"calls": 0, "exclusive_seconds": 0.0})
                record["calls"] = int(record["calls"]) + 1
                record["exclusive_seconds"] = float(record["exclusive_seconds"]) + exclusive

        def instrumented(*args, **kwargs):
            current_pass, current_stage, _ = ledger.context.get()
            if pass_value is not None:
                try:
                    current_pass = pass_value(args, kwargs)
                except Exception:
                    pass
            if stage_value is not None:
                try:
                    current_stage = stage_value(args, kwargs)
                except Exception:
                    pass
            callback_kwargs = dict(kwargs)
            for name in callbacks:
                callback = callback_kwargs.get(name)
                if callback is None:
                    continue

                def callback_wrapper(*cb_args, __callback=callback, __name=name, **cb_kwargs):
                    return timed_call(__callback, cb_args, cb_kwargs,
                                      f"candidate.{__name}")

                callback_kwargs[name] = callback_wrapper
            return timed_call(function, args, callback_kwargs, category,
                              current_pass, current_stage)

        instrumented.__name__ = getattr(function, "__name__", "instrumented")
        instrumented.__qualname__ = getattr(function, "__qualname__", instrumented.__name__)
        instrumented.__doc__ = getattr(function, "__doc__", None)
        instrumented.__wrapped__ = function
        return instrumented


def patch_aliases(original: Callable, replacement: Callable) -> int:
    """Replace only module globals that still reference this exact callable."""
    count = 0
    for module in tuple(sys.modules.values()):
        if not isinstance(module, ModuleType) or not module.__name__.startswith("chrona."):
            continue
        namespace = vars(module)
        for name, value in tuple(namespace.items()):
            if value is original:
                setattr(module, name, replacement)
                count += 1
    return count


def _stage_from_attempt(args, kwargs):
    domain = args[0] if args else kwargs.get("domain")
    stage = getattr(getattr(domain, "stage", None), "value", None)
    return str(stage or "unknown")


def install(ledger: Ledger) -> dict[str, int]:
    modules = {
        "route_search": importlib.import_module("chrona.presentation.layout.route_search"),
        "routing": importlib.import_module("chrona.presentation.layout.routing"),
        "resolution": importlib.import_module("chrona.presentation.layout.relation_resolution"),
        "surface_routes": importlib.import_module("chrona.presentation.layout.surface_routes"),
        "label_plan": importlib.import_module("chrona.presentation.layout.surface_route_label_plan"),
        "member_labels": importlib.import_module("chrona.presentation.layout.surface_member_labels"),
    }
    targets = (
        (modules["route_search"]._build_visibility_base, "graph.visibility_base", None, None, ()),
        (modules["route_search"]._build_sparse_graph, "graph.sparse_graph", None, None, ()),
        (modules["route_search"]._reverse_bounds, "graph.reverse_bounds", None, None, ()),
        (modules["routing"].select_relation_route, "routing.selection_other", None, None,
         ("prepare", "accept", "rank")),
        (modules["surface_routes"].compose_surface_routes, "routing.compose_surface_routes",
         lambda a, k: getattr((a[0] if a else k.get("context")), "progress_pass", "relations"), None, ()),
        (modules["label_plan"]._run_trial, "routing.label_trial_other",
         lambda a, k: str(k.get("progress_pass", "unspecified")), None, ()),
        (modules["member_labels"].place_member_labels, "labels.member", None, None, ()),
        (modules["surface_routes"].place_relation_labels, "labels.relation", None, None, ()),
    )
    # This seam was optional in earlier probe targets. Add it only when
    # present, so the ordinary seam guard still detects missing core targets.
    prepare_facts = getattr(modules["member_labels"], "_prepare_member_label_facts", None)
    if callable(prepare_facts):
        targets = (*targets, (prepare_facts, "labels.preparation", None, None, ()))
    counts: dict[str, int] = {}
    # Attribute only route_search's envelope conversion, before graph lookup.
    # Do not patch the shared helper globally: other geometry owners exist.
    envelope = modules["route_search"].obstacle_envelope
    modules["route_search"].obstacle_envelope = ledger.wrap("graph.envelope", envelope)
    counts["graph.envelope"] = 1
    # surface_member_labels imports this alias directly; patch only that caller
    # so unrelated paint/obstacle geometry work remains outside this category.
    span_footprint = modules["member_labels"].span_mark_footprint
    modules["member_labels"].span_mark_footprint = ledger.wrap("labels.span_paint", span_footprint)
    counts["labels.span_paint"] = 1
    originals = [(function, category, pass_value, stage_value, callbacks)
                 for function, category, pass_value, stage_value, callbacks in targets]
    for function, category, pass_value, stage_value, callbacks in originals:
        replacement = ledger.wrap(category, function, pass_value=pass_value,
                                  stage_value=stage_value, callbacks=callbacks)
        counts[category] = patch_aliases(function, replacement)
    # Stage attribution belongs to each actual resolution attempt, not the
    # whole relation loop. Its exclusive remainder is reported separately.
    resolution = modules["resolution"].search_relation_resolution
    staged = _wrap_resolution_attempts(ledger, resolution)
    counts["routing.resolution"] = patch_aliases(resolution, staged)
    return counts


def _wrap_resolution_attempts(ledger: Ledger, function: Callable) -> Callable:
    """Tag each callback with the domain's real stage; keep other time exclusive."""
    timed = ledger.wrap("routing.resolution", function)

    def wrapped(*args, **kwargs):
        options = dict(kwargs)
        attempt = options.get("attempt")
        if attempt is None:
            return timed(*args, **kwargs)

        def staged_attempt(domain):
            callback = ledger.wrap("routing.resolution_attempt_other", attempt,
                                   stage_value=lambda a, k: _stage_from_attempt(a, k))
            return callback(domain)

        options["attempt"] = staged_attempt
        return timed(*args, **options)

    wrapped.__name__ = getattr(function, "__name__", "search_relation_resolution")
    wrapped.__wrapped__ = function
    return wrapped


def _git_metadata(root: Path) -> dict[str, str | None]:
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=root, check=True,
                capture_output=True, text=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return None
    return {"source_root": str(root), "git_head": git("rev-parse", "HEAD"),
            "git_dirty": bool(git("status", "--porcelain")) if git("status", "--porcelain") is not None else None}


def _require_clean_checkout(metadata: dict[str, str | None]) -> None:
    if metadata["git_head"] is None or metadata["git_dirty"] is None:
        raise RuntimeError("profiling requires a Git checkout at the current working directory")
    if metadata["git_dirty"]:
        raise RuntimeError("profiling refuses a dirty checkout; commit or clean the source first")


def _argv_path_hash(argv: list[str], cwd: Path) -> str:
    digest = hashlib.sha256()
    paths: list[Path] = []
    for token in argv:
        candidate = Path(token)
        if not candidate.is_absolute():
            candidate = cwd / candidate
        if candidate.exists():
            paths.append(candidate)
    for path in sorted(set(paths), key=str):
        files = [path] if path.is_file() else sorted(item for item in path.rglob("*") if item.is_file())
        for file in files:
            digest.update(str(file.resolve()).encode())
            try:
                with file.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
            except OSError:
                digest.update(b"<unreadable>")
    return digest.hexdigest()


def _self_test() -> None:
    ticks = [0.0]
    ledger = Ledger(lambda: ticks[0])

    def inner():
        ticks[0] += 3
        return "inner-result"

    def outer():
        ticks[0] += 10
        assert patched_alias() == "inner-result"
        ticks[0] += 2
        return "outer-result"

    wrapped_inner = ledger.wrap("inner", inner)
    holder_a = ModuleType("chrona.fake_a")
    holder_b = ModuleType("chrona.fake_b")
    holder_a.operation = inner
    holder_b.operation = inner
    sys.modules[holder_a.__name__] = holder_a
    sys.modules[holder_b.__name__] = holder_b
    assert patch_aliases(inner, wrapped_inner) == 2

    def patched_alias():
        return holder_b.operation()

    wrapped_outer = ledger.wrap("outer", outer)
    assert wrapped_outer() == "outer-result"
    assert holder_a.operation() == "inner-result"
    inner_record = next(value for key, value in ledger.values.items() if key.endswith("/inner"))
    outer_record = next(value for key, value in ledger.values.items() if key.endswith("/outer"))
    assert inner_record == {"calls": 2, "exclusive_seconds": 6.0}, inner_record
    assert outer_record == {"calls": 1, "exclusive_seconds": 12.0}, outer_record

    error = RuntimeError("same exception")

    def fail():
        ticks[0] += 4
        raise error

    try:
        ledger.wrap("throws", fail)()
    except RuntimeError as caught:
        assert caught is error
    else:
        raise AssertionError("exception was swallowed")
    throw_record = next(value for key, value in ledger.values.items() if key.endswith("/throws"))
    assert throw_record == {"calls": 1, "exclusive_seconds": 4.0}, throw_record

    token = ledger.context.set(("outer-pass", "normal-stage", None))
    trial = ledger.wrap("trial", lambda: "trial-result",
                        pass_value=lambda args, kwargs: "route-label-recovery")
    assert trial() == "trial-result"
    ledger.context.reset(token)
    assert "route-label-recovery/normal-stage/trial" in ledger.values
    print("self-test: nested timing, alias patching, exception transparency, and pass/stage attribution passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("chrona_args", nargs=argparse.REMAINDER)
    options = parser.parse_args()
    if options.self_test:
        _self_test()
        return 0
    if options.output is None:
        parser.error("--output is required unless --self-test is used")
    argv = list(options.chrona_args)
    if argv[:1] == ["--"]:
        argv.pop(0)
    if not argv:
        parser.error("supply ordinary chrona CLI arguments after --")

    root = Path.cwd().resolve()
    metadata = _git_metadata(root)
    _require_clean_checkout(metadata)
    metadata.update({"python": sys.version, "platform": platform.platform(),
                     "argv": argv, "argv_paths_sha256": _argv_path_hash(argv, root),
                     "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    route_search = importlib.import_module("chrona.presentation.layout.route_search")
    module_path = Path(route_search.__file__).resolve()
    if not module_path.is_relative_to(root):
        raise RuntimeError(f"Chrona import is outside the current checkout: {module_path} (checkout {root})")
    ledger = Ledger()
    patch_counts = install(ledger)
    absent = [name for name, count in patch_counts.items() if count < 1]
    if absent:
        raise RuntimeError("probe seam aliases were not found: " + ", ".join(absent))

    cli = importlib.import_module("chrona.app.cli")
    sys.argv = ["chrona", *argv]
    started = time.perf_counter()
    process_outcome = "returned"
    return_code = 0
    try:
        cli.main()
    except SystemExit as error:
        return_code = int(error.code) if isinstance(error.code, int) else (0 if error.code is None else 1)
        process_outcome = "system-exit"
        raise
    except BaseException as error:
        process_outcome = f"exception:{type(error).__name__}"
        raise
    finally:
        wall = time.perf_counter() - started
        records = list(ledger.values.values())
        exclusive = sum(float(item["exclusive_seconds"]) for item in records)
        payload = {**metadata, "wall_seconds": wall, "process_outcome": process_outcome,
                   "return_code": return_code, "patch_alias_counts": patch_counts,
                   "phases": ledger.values,
                   "exclusive_total_seconds": exclusive,
                   "residual_seconds": wall - exclusive,
                   "residual_category": "unwrapped CLI/projection/other runtime"}
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
