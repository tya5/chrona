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
import inspect
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from types import ModuleType
from typing import Callable
from collections import Counter


class Frame:
    __slots__ = ("children",)

    def __init__(self) -> None:
        self.children = 0.0


class Ledger:
    def __init__(self, clock: Callable[[], float] = time.perf_counter) -> None:
        self.clock = clock
        self.context = contextvars.ContextVar("chrona_probe_context", default=("unclassified", "unspecified", None))
        self.values: dict[str, dict[str, float | int]] = {}
        self.graph_identities = None
        self.graph_memo_admission = {"attempted_records": 0, "refused_entries": 0,
                                     "refused_records": 0, "over_limit_attempts": 0}

    def wrap(self, category: str, function: Callable, *,
             pass_value: Callable | None = None,
             stage_value: Callable | None = None,
             callbacks: tuple[str, ...] = (),
             before_call: Callable | None = None) -> Callable:
        ledger = self

        def timed_call(callable_, args, kwargs, category_, pass_override=None, stage_override=None):
            old_pass, old_stage, parent = ledger.context.get()
            current_pass = pass_override if pass_override is not None else old_pass
            current_stage = stage_override if stage_override is not None else old_stage
            frame = Frame()
            token = ledger.context.set((current_pass, current_stage, frame))
            if before_call is not None:
                before_call(args, kwargs)
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


class GraphIdentityLedger:
    """Bounded-by-observed-calls identities for exact sparse-graph inputs."""

    def __init__(self, obstacle_index_type) -> None:
        self.obstacle_index_type = obstacle_index_type
        self.signature = None
        self.calls: Counter[tuple[str, bool]] = Counter()
        self.skipped = 0
        self.request_context = contextvars.ContextVar("chrona_graph_request_context", default=None)
        self.route_signature = None
        self.route_clear_code = None
        self.sequences: dict[int, dict] = {}
        self.skipped_requests = 0

    def identity(self, args, kwargs):
        try:
            bound = self.signature.bind(*args, **kwargs)
            values = bound.arguments
            clear = values["clear"]
            closure = inspect.getclosurevars(clear).nonlocals
            required = {"index", "port_ids", "classes", "regions", "rects"}
            if set(closure) != required:
                return None
            for name in ("start", "end", "rects"):
                if not isinstance(values[name], tuple):
                    return None
            if not isinstance(closure["rects"], tuple):
                return None
            if not isinstance(closure["port_ids"], tuple):
                return None
            for name in ("classes", "regions"):
                value = closure[name]
                if value is not None and not isinstance(value, (tuple, frozenset)):
                    return None
            index = closure["index"]
            if index is None:
                index_facts = None
            elif isinstance(index, self.obstacle_index_type):
                # Include the whole immutable obstacle inventory, not only a
                # guessed selection, so unknown/excluded-port semantics cannot
                # accidentally produce a false identity match.
                index_facts = tuple(repr(item) for item in index.all())
            else:
                return None
            visibility = values.get("visibility_base")
            if visibility is None:
                visibility_facts = None
            else:
                visibility_facts = (
                    tuple(sorted(visibility.nodes)),
                    tuple(sorted(visibility.visibility.items())),
                    tuple(visibility.x_events), tuple(visibility.y_events),
                )
            closure_code = clear.__code__
            facts = (
                values["start"], values["end"], values["rects"],
                values["grid_offset"], values.get("bounds"),
                visibility_facts,
                hashlib.sha256(closure_code.co_code).hexdigest(),
                repr(closure_code.co_consts),
                index_facts, closure["rects"],
                closure["port_ids"],
                None if closure["classes"] is None else tuple(closure["classes"]),
                None if closure["regions"] is None else tuple(closure["regions"]),
            )
            digest = hashlib.sha256(repr(facts).encode("utf-8")).hexdigest()
            return digest, bool(values.get("exact_bound", True))
        except Exception:
            return None

    def record(self, args, kwargs) -> None:
        try:
            identity = self.identity(args, kwargs)
        except Exception:
            identity = None
        if identity is None:
            self.skipped += 1
        else:
            self.calls[identity] += 1

    @staticmethod
    def _visibility_facts(visibility):
        if visibility is None:
            return None
        return (tuple(sorted(visibility.nodes)), tuple(sorted(visibility.visibility.items())),
                tuple(visibility.x_events), tuple(visibility.y_events))

    def record_endpoint_request(self, selection, key, hit: bool) -> None:
        context = self.request_context.get()
        try:
            if context is None:
                raise ValueError("unknown request context")
            values = context
            index = values["obstacles"]
            if not isinstance(index, self.obstacle_index_type):
                raise ValueError("unknown obstacle index")
            start, end = values["start"], values["end"]
            grid_offset = values.get("grid_offset", 2.0)
            bounds = values.get("bounds")
            port_ids = values.get("port_ids", ())
            classes, regions = values.get("classes"), values.get("regions")
            if (not isinstance(start, tuple) or not isinstance(end, tuple)
                    or not isinstance(port_ids, tuple)):
                raise ValueError("non-immutable query inputs")
            if any(value is not None and not isinstance(value, (tuple, frozenset))
                   for value in (classes, regions)):
                raise ValueError("non-immutable selection inputs")
            if not isinstance(key, tuple) or len(key) != 2:
                raise ValueError("unknown geometry key")
            selected_ports = key[1]
            base_key = ("visibility-base-v1", repr((grid_offset, bounds)), selected_ports)
            visibility = selection.visibility_bases.get(base_key)
            identity_facts = (
                start, end, selection.envelopes, grid_offset, bounds,
                self._visibility_facts(visibility),
                hashlib.sha256(self.route_clear_code.co_code).hexdigest(),
                repr(self.route_clear_code.co_consts),
                tuple(repr(item) for item in index.all()),
                selection.envelopes, port_ids,
                None if classes is None else tuple(classes),
                None if regions is None else tuple(regions),
                selected_ports, key[0],
            )
            digest = hashlib.sha256(repr(identity_facts).encode("utf-8")).hexdigest()
            exact_bound = bool(values.get("exact_bound", True))
            owner_id = id(selection)
            group = self.sequences.get(owner_id)
            if group is None:
                group = {"owner": selection, "requests": []}
                self.sequences[owner_id] = group
            cache_key_digest = hashlib.sha256(
                repr((key[0], tuple(sorted(selected_ports)))).encode("utf-8")).hexdigest()
            group["requests"].append((digest, exact_bound, bool(hit), cache_key_digest))
        except Exception:
            self.skipped_requests += 1

    def sequence_events(self) -> dict:
        groups = []
        mode_counts = Counter()
        actual_hits = actual_misses = request_count = 0
        for ordinal, group in enumerate(self.sequences.values()):
            events = []
            for digest, exact_bound, hit, cache_key_digest in group["requests"]:
                mode_counts["exact" if exact_bound else "relaxed"] += 1
                actual_hits += int(hit)
                actual_misses += int(not hit)
                request_count += 1
                events.append({"identity": digest, "exact_bound": exact_bound,
                               "slot_hit": hit, "geometry_key": cache_key_digest})
            groups.append({"selection": ordinal, "events": events})
        return {
            "selection_count": len(groups),
            "request_count": request_count,
            "skipped_unknown_requests": self.skipped_requests,
            "requests_by_bound_mode": dict(mode_counts),
            "actual_one_slot_hits": actual_hits,
            "actual_one_slot_misses": actual_misses,
            "groups": groups,
        }

    def summary(self) -> dict:
        by_mode = Counter()
        for (_, exact_bound), count in self.calls.items():
            by_mode["exact" if exact_bound else "relaxed"] += count
        by_digest: dict[str, dict[bool, int]] = {}
        for (digest, exact_bound), count in self.calls.items():
            by_digest.setdefault(digest, {})[exact_bound] = count
        paired = [item for item in by_digest.values() if True in item and False in item]
        return {
            "observed_calls": sum(self.calls.values()),
            "skipped_unknown_closure": self.skipped,
            "calls_by_exact_bound": dict(by_mode),
            "distinct_input_identities": len(by_digest),
            "identities_seen_in_both_modes": len(paired),
            "paired_call_count": sum(min(item[True], item[False]) for item in paired),
            "same_mode_duplicate_calls": sum(max(0, count - 1) for count in self.calls.values()),
        }


class ObservedEndpointGeometry(dict):
    """Plain dict behavior with observation at the existing slot read seam."""

    __slots__ = ("owner", "ledger")

    def __init__(self, owner, ledger) -> None:
        super().__init__()
        self.owner = owner
        self.ledger = ledger

    def get(self, key, default=None):
        value = super().get(key, default)
        self.ledger.record_endpoint_request(self.owner, key, value is not default)
        return value


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
    sparse_graph = modules["route_search"]._build_sparse_graph
    ledger.graph_identities = GraphIdentityLedger(modules["route_search"].SurfaceObstacleIndex)
    ledger.graph_identities.signature = inspect.signature(sparse_graph)
    obstacles_module = importlib.import_module("chrona.presentation.layout.obstacles")
    memo_type = obstacles_module._RouteMemo
    original_store = memo_type.store
    memo_record_limit = obstacles_module.ROUTE_MEMO_LIMIT
    route_function = modules["route_search"].orthogonal_route_candidates
    ledger.graph_identities.route_signature = inspect.signature(route_function)
    ledger.graph_identities.route_clear_code = next(
        (code for code in route_function.__code__.co_consts
         if getattr(code, "co_name", None) == "clear"), None)
    if ledger.graph_identities.route_clear_code is None:
        raise RuntimeError("route_search clear closure was not found for graph identity tracing")

    prepared_type = obstacles_module._PreparedSelection
    original_prepared_init = prepared_type.__init__

    def observed_prepared_init(selection, *args, **kwargs):
        original_prepared_init(selection, *args, **kwargs)
        selection.endpoint_geometry = ObservedEndpointGeometry(selection, ledger.graph_identities)

    prepared_type.__init__ = observed_prepared_init

    def observed_route(*args, **kwargs):
        try:
            route_values = ledger.graph_identities.route_signature.bind(*args, **kwargs).arguments
        except Exception:
            route_values = None
        token = ledger.graph_identities.request_context.set(route_values)
        try:
            yield from route_function(*args, **kwargs)
        finally:
            ledger.graph_identities.request_context.reset(token)

    observed_route.__name__ = getattr(route_function, "__name__", "orthogonal_route_candidates")
    observed_route.__qualname__ = getattr(route_function, "__qualname__", observed_route.__name__)
    observed_route.__doc__ = getattr(route_function, "__doc__", None)
    observed_route.__wrapped__ = route_function
    counts_route = patch_aliases(route_function, observed_route)
    counts: dict[str, int] = {"graph.endpoint_requests": counts_route}

    def observed_store(memo, key, value, *, record_count=1):
        stats = ledger.graph_memo_admission
        stats["attempted_records"] += record_count
        had_key = key in memo.results
        before = memo.result_records
        result = original_store(memo, key, value, record_count=record_count)
        if not had_key and key not in memo.results:
            stats["refused_entries"] += 1
            stats["refused_records"] += record_count
            if before + record_count > memo_record_limit:
                stats["over_limit_attempts"] += 1
        return result

    memo_type.store = observed_store
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
        before_call = ledger.graph_identities.record if function is sparse_graph else None
        replacement = ledger.wrap(category, function, pass_value=pass_value,
                                  stage_value=stage_value, callbacks=callbacks,
                                  before_call=before_call)
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

    rects = ((1.0, 2.0, 3.0, 4.0),)

    def make_clear(rects):
        index, port_ids, classes, regions = None, (), None, None

        def clear(a, b):
            return (index, port_ids, classes, regions, rects, a, b) is not None
        return clear

    def sparse(start, end, rects, *, grid_offset, bounds, clear,
               visibility_base=None, exact_bound=True):
        return start, end, rects, grid_offset, bounds, clear, visibility_base, exact_bound

    identities = GraphIdentityLedger(object)
    identities.signature = inspect.signature(sparse)
    clear = make_clear(rects)
    common = ((0.0, 0.0), (10.0, 10.0), rects)
    options = {"grid_offset": 2.0, "bounds": None, "clear": clear, "visibility_base": None}
    relaxed = identities.identity(common, {**options, "exact_bound": False})
    exact = identities.identity(common, {**options, "exact_bound": True})
    assert relaxed is not None and exact is not None and relaxed[0] == exact[0]
    assert relaxed[1] is False and exact[1] is True
    identities.calls[relaxed] += 1
    identities.calls[exact] += 1
    assert identities.summary()["identities_seen_in_both_modes"] == 1
    assert identities.summary()["paired_call_count"] == 1
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
                   "graph_input_identities": ledger.graph_identities.summary(),
                   "graph_endpoint_sequences": ledger.graph_identities.sequence_events(),
                   "graph_memo_admission": ledger.graph_memo_admission,
                   "exclusive_total_seconds": exclusive,
                   "residual_seconds": wall - exclusive,
                   "residual_category": "unwrapped CLI/projection/other runtime"}
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
