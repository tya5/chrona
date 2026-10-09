"""Characterization of the CLI: stdout, stderr, exit code and written files.

I142-S0 extracts the validate, schedule and draft-render pipelines and the
failure-to-diagnostics ladder out of ``chrona.app.cli``. The extraction must not
change one byte of what the CLI prints, so this suite records, for a matrix of
invocations (success paths and every failure family), exactly what ``main()``
produced, and compares it with ``tests/fixtures/cli_characterization/golden.json``.

Rules the matrix keeps:

* every invocation runs in a fresh scratch directory with relative paths, so no
  host path reaches the record (any absolute scratch path is replaced by ``<tmp>``);
* the OS wording of an ``OSError`` (``[Errno 2] ...`` against ``[WinError 2] ...``)
  is replaced by ``<os error>``, because it is the only OS-dependent text;
* a rendered artifact is described by what it is (well-formed SVG root, PNG
  signature, Scene JSON keys), not by its bytes, so a legitimate presentation change
  does not rewrite the golden file; ``CHRONA_CHARACTERIZATION_RAW=<file>`` records
  the unnormalised output and the SHA-256 of every written file for a before/after
  comparison of the exact bytes;
* the CLI is deterministic: `test_hash_seed_determinism.py` runs it under eight hash seeds, so the
  key order of ``analysis.totalFloat`` (Project object order, Spec 57) is recorded as printed;
* nothing here reads the clock or the host environment.

Re-record the golden file only for an intended CLI change:
``python -m tests.cli.test_cli_characterization --record``.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Callable

import pytest

from chrona.app.cli import main
from chrona.storage.snapshot_paths import snapshot_directory

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "cli_characterization"
GOLDEN = FIXTURES / "golden.json"

_STARTER = (FIXTURES / "starter.yaml").read_text(encoding="utf-8")

_SYNTHETIC: dict[str, str] = {
    "broken-yaml.yaml": "version: [unclosed\nproject: {id: p\n",
    "not-a-mapping.yaml": "- a\n- b\n",
    "empty.yaml": "",
    "broken.json": "{\"version\": \n",
    # Valid YAML, wrong shape: a task with no schedule.
    "schema-error.yaml": (
        "version: timeline/v0.7\nproject: {id: p, title: P}\n"
        "objects:\n  a: {type: task, title: A}\nrelations: []\n"
    ),
    # Structurally valid, a relation names an object that does not exist.
    "reference-error.yaml": _STARTER.replace(
        "relations: []",
        "relations:\n  - {id: r1, type: dependency, from: {object: design, endpoint: end}, "
        "to: {object: ghost, endpoint: start}, lag: 0d}",
    ),
    # Two derived tasks that depend on each other: valid, but cannot be scheduled.
    "cycle.yaml": (
        "version: timeline/v0.7\nproject: {id: cyc, title: Cycle}\n"
        "objects:\n"
        "  a: {type: task, title: A, schedule: {mode: scheduled, amount: 2d}}\n"
        "  b: {type: task, title: B, schedule: {mode: scheduled, amount: 2d}}\n"
        "relations:\n"
        "  - {id: a-b, type: dependency, from: {object: a, endpoint: end}, to: {object: b, endpoint: start}, lag: 0d}\n"
        "  - {id: b-a, type: dependency, from: {object: b, endpoint: end}, to: {object: a, endpoint: start}, lag: 0d}\n"
    ),
    # Valid, but a hard maximum is earlier than the dependency allows.
    "contradictory.yaml": (
        "version: timeline/v0.7\nproject: {id: bounds, title: Bounds}\n"
        "objects:\n"
        "  design: {type: task, title: Design, schedule: {mode: fixed-span, start: '2026-10-01', end: '2026-10-30'}}\n"
        "  build: {type: task, title: Build, schedule: {mode: scheduled, amount: 5d, constraints: {end: {max: '2026-10-05'}}}}\n"
        "relations:\n"
        "  - {id: d-b, type: dependency, from: {object: design, endpoint: end}, to: {object: build, endpoint: start}, lag: 0d}\n"
    ),
    # Valid and schedulable: a fixed span and a derived gate that both finish after their deadline (W_DEADLINE).
    "late-deadline.yaml": (
        "version: timeline/v0.7\nproject: {id: late, title: Late}\n"
        "objects:\n"
        "  qa: {type: task, title: QA, deadline: '2026-10-05', schedule: {mode: fixed-span, start: '2026-10-01', end: '2026-10-08'}}\n"
        "  launch: {type: gate, title: Launch, deadline: '2026-10-08', schedule: {mode: scheduled-point}}\n"
        "relations:\n"
        "  - {id: qa-launch, type: dependency, from: {object: qa, endpoint: end}, to: {object: launch, endpoint: at}, lag: 2d}\n"
    ),
    # A deadline that is not a calendar date is rejected now that it is read.
    "deadline-not-a-date.yaml": _STARTER.replace(
        "title: Release,", "title: Release, deadline: '2026-02-30',"),
    "bad-theme.yaml": "version: chrona/theme/v0.1\nkind: theme\nid: nope\nbody: {tokens: 3}\n",
    "snapshot-reference.yaml": (
        "id: starter-ref\nkind: project\nstore: {provider: local, identity: char-store}\n"
        "address: project.yaml\nrevision: {token: r1}\n"
    ),
}


@dataclass(frozen=True)
class Case:
    id: str
    argv: tuple[str, ...]
    pre: tuple[tuple[str, ...], ...] = ()
    edit: Callable[[pathlib.Path], None] | None = None
    boom: bool = False
    note: str = ""


def _case(case_id: str, *argv: str, pre: tuple[tuple[str, ...], ...] = (),
          edit: Callable[[pathlib.Path], None] | None = None, boom: bool = False) -> Case:
    return Case(case_id, tuple(argv), pre, edit, boom)


def _stale_preset(root: pathlib.Path) -> None:
    """A copied builtin preset whose theme was written against an older version."""
    theme = root / "pc" / "theme.yaml"
    text = theme.read_text(encoding="utf-8")
    first, rest = text.split("\n", 1)
    theme.write_text("version: chrona/theme/v0.0\n" + rest if first.startswith("version:") else text, encoding="utf-8")


def _prepare_snapshot(root: pathlib.Path) -> None:
    snapshot = snapshot_directory(root / "snaps", "r1")
    snapshot.mkdir(parents=True)
    (snapshot / "project.yaml").write_text(_STARTER, encoding="utf-8")


def _edit_yaml(name: str, path: tuple[str, ...], value: object) -> Callable[[pathlib.Path], None]:
    def edit(root: pathlib.Path) -> None:
        import yaml
        target = root / name
        document = yaml.safe_load(target.read_text(encoding="utf-8"))
        node = document
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
        target.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return edit


def _edit_many(*edits: Callable[[pathlib.Path], None]) -> Callable[[pathlib.Path], None]:
    def edit(root: pathlib.Path) -> None:
        for step in edits:
            step(root)
    return edit


_PC = (("preset", "copy", "editorial", "--output", "pc"),)
_HAL = ("halcyon-1/project.yaml",)
_HAL_RES = ("--view", "halcyon-1/view.yaml", "--theme", "halcyon-1/theme.yaml",
            "--scheme", "halcyon-1/scheme.yaml", "--layout", "halcyon-1/layout.yaml",
            "--actual", "halcyon-1/actual.yaml")

CASES: tuple[Case, ...] = (
    # validate
    _case("validate-starter-ok", "validate", "starter.yaml"),
    _case("validate-halcyon-ok", "validate", *_HAL),
    _case("validate-missing-file", "validate", "missing.yaml"),
    _case("validate-path-is-directory", "validate", "halcyon-1"),
    _case("validate-broken-yaml", "validate", "broken-yaml.yaml"),
    _case("validate-not-a-mapping", "validate", "not-a-mapping.yaml"),
    _case("validate-empty-file", "validate", "empty.yaml"),
    _case("validate-schema-error", "validate", "schema-error.yaml"),
    _case("validate-reference-error", "validate", "reference-error.yaml"),
    _case("validate-cycle-rejected", "validate", "cycle.yaml"),
    _case("validate-no-project", "validate"),
    _case("validate-unknown-flag", "validate", "starter.yaml", "--nope"),
    _case("validate-snapshot-partial", "validate", "--snapshot-reference", "snapshot-reference.yaml"),
    _case("validate-snapshot-and-project", "validate", "starter.yaml", "--snapshot-reference", "snapshot-reference.yaml",
          "--snapshot-root", "snaps", "--store-identity", "char-store"),
    _case("validate-snapshot-missing-reference", "validate", "--snapshot-reference", "absent.yaml",
          "--snapshot-root", "snaps", "--store-identity", "char-store"),
    _case("validate-snapshot-unreadable-resource", "validate", "--snapshot-reference", "snapshot-reference.yaml",
          "--snapshot-root", "snaps", "--store-identity", "char-store"),
    _case("validate-snapshot-ok", "validate", "--snapshot-reference", "snapshot-reference.yaml",
          "--snapshot-root", "snaps", "--store-identity", "char-store", "--allow-missing-content-identity",
          edit=_prepare_snapshot),
    _case("validate-deadline-late-unchanged", "validate", "late-deadline.yaml"),
    _case("validate-unexpected-exception", "validate", "starter.yaml", boom=True),
    _case("unknown-command", "frobnicate"),
    _case("no-command"),
    # schedule
    _case("schedule-starter-ok", "schedule", "starter.yaml"),
    _case("schedule-halcyon-ok", "schedule", *_HAL),
    _case("schedule-missing-file", "schedule", "missing.yaml"),
    _case("schedule-broken-yaml", "schedule", "broken-yaml.yaml"),
    _case("schedule-schema-error", "schedule", "schema-error.yaml"),
    _case("schedule-reference-error", "schedule", "reference-error.yaml"),
    _case("schedule-cycle-rejected", "schedule", "cycle.yaml"),
    _case("schedule-contradictory-bounds", "schedule", "contradictory.yaml"),
    _case("schedule-deadline-warning", "schedule", "late-deadline.yaml"),
    _case("schedule-deadline-not-a-date", "schedule", "deadline-not-a-date.yaml"),
    _case("schedule-no-project", "schedule"),
    _case("schedule-snapshot-ok", "schedule", "--snapshot-reference", "snapshot-reference.yaml",
          "--snapshot-root", "snaps", "--store-identity", "char-store", "--allow-missing-content-identity",
          edit=_prepare_snapshot),
    _case("schedule-unexpected-exception", "schedule", "starter.yaml", boom=True),
    # draft render: success paths
    _case("render-default-svg", "render", "starter.yaml", "-o", "out.svg"),
    _case("render-default-no-suffix", "render", "starter.yaml", "-o", "out"),
    _case("render-default-png", "render", "starter.yaml", "-o", "out.png"),
    _case("render-deadline-warning", "render", "late-deadline.yaml", "-o", "out.svg"),
    _case("render-format-svg-explicit", "render", "starter.yaml", "--format", "svg", "-o", "out.svg"),
    _case("render-format-png-no-suffix", "render", "starter.yaml", "--format", "png", "-o", "out"),
    _case("render-actual", "render", "starter.yaml", "--actual", "starter-actual.yaml", "-o", "out.svg"),
    _case("render-viewport", "render", "starter.yaml", "--viewport", "900x700", "-o", "out.svg"),
    _case("render-viewport-width-only", "render", "starter.yaml", "--viewport", "900xauto", "-o", "out.svg"),
    _case("render-visual-profile", "render", "starter.yaml", "--visual-profile", "chrona-output/visual/v0.7-svg",
          "-o", "out.svg"),
    _case("render-preset-builtin-id", "render", "starter.yaml", "--preset", "editorial", "-o", "out.svg"),
    _case("render-preset-builtin-id-png", "render", "starter.yaml", "--preset", "technical-print", "-o", "out.png"),
    _case("render-preset-copied-path", "render", "starter.yaml", "--preset", "pc/preset.yaml", "-o", "out.svg", pre=_PC),
    _case("render-preset-with-scheme-override", "render", "starter.yaml", "--preset", "editorial",
          "--scheme", "halcyon-1/scheme.yaml", "-o", "out.svg"),
    _case("render-halcyon-default", "render", *_HAL, "--actual", "halcyon-1/actual.yaml", "-o", "out.svg"),
    _case("render-halcyon-view-theme-scheme-layout", "render", *_HAL, *_HAL_RES, "-o", "out.svg"),
    _case("render-halcyon-resources-png", "render", *_HAL, *_HAL_RES, "-o", "out.png"),
    _case("render-halcyon-emit-scene", "render", *_HAL, *_HAL_RES, "-o", "out.svg", "--emit-scene", "scene.json"),
    _case("render-starter-emit-scene", "render", "starter.yaml", "-o", "out.svg", "--emit-scene", "scene.json"),
    _case("render-view-only", "render", *_HAL, "--view", "halcyon-1/view.yaml", "-o", "out.svg"),
    _case("render-theme-only", "render", "starter.yaml", "--theme", "halcyon-1/theme.yaml", "-o", "out.svg"),
    _case("render-layout-only", "render", "starter.yaml", "--layout", "halcyon-1/layout.yaml", "-o", "out.svg"),
    _case("render-format-pdf", "render", "starter.yaml", "--format", "pdf", "-o", "out.pdf"),
    # draft render: failure families
    _case("render-missing-project", "render", "missing.yaml", "-o", "out.svg"),
    _case("render-broken-yaml-project", "render", "broken-yaml.yaml", "-o", "out.svg"),
    _case("render-not-a-mapping-project", "render", "not-a-mapping.yaml", "-o", "out.svg"),
    _case("render-schema-error-project", "render", "schema-error.yaml", "-o", "out.svg"),
    _case("render-reference-error-project", "render", "reference-error.yaml", "-o", "out.svg"),
    _case("render-cycle-project-rejected", "render", "cycle.yaml", "-o", "out.svg"),
    _case("render-contradictory-project", "render", "contradictory.yaml", "-o", "out.svg"),
    _case("render-preset-unknown", "render", "starter.yaml", "--preset", "no-such-preset", "-o", "out.svg"),
    _case("render-preset-path-missing", "render", "starter.yaml", "--preset", "nowhere/preset.yaml", "-o", "out.svg"),
    _case("render-preset-stale-copy", "render", "starter.yaml", "--preset", "pc/preset.yaml", "-o", "out.svg",
          pre=_PC, edit=_stale_preset),
    _case("render-view-missing-file", "render", "starter.yaml", "--view", "nowhere/view.yaml", "-o", "out.svg"),
    _case("render-theme-missing-file", "render", "starter.yaml", "--theme", "nowhere/theme.yaml", "-o", "out.svg"),
    _case("render-theme-schema-error", "render", "starter.yaml", "--theme", "bad-theme.yaml", "-o", "out.svg"),
    _case("render-ingress-one-finding", "render", *_HAL, *_HAL_RES, "-o", "out.svg",
          edit=_edit_yaml("halcyon-1/view.yaml", ("body", "surface"), "table-timelinez")),
    _case("render-ingress-findings-across-resources", "render", *_HAL, *_HAL_RES, "-o", "out.svg",
          edit=_edit_many(_edit_yaml("halcyon-1/view.yaml", ("body", "surface"), "table-timelinez"),
                          _edit_yaml("halcyon-1/theme.yaml", ("body", "values", "opacity.axis-band", "type"), "numberz"))),
    _case("render-theme-is-a-view", "render", "starter.yaml", "--theme", "halcyon-1/view.yaml", "-o", "out.svg"),
    _case("render-view-is-a-theme", "render", "starter.yaml", "--view", "halcyon-1/theme.yaml", "-o", "out.svg"),
    _case("render-actual-missing", "render", "starter.yaml", "--actual", "nowhere/actual.yaml", "-o", "out.svg"),
    _case("render-font-metrics-missing", "render", "starter.yaml", "--font-metrics", "nowhere/metrics.yaml",
          "-o", "out.svg"),
    _case("render-icon-catalog-missing", "render", "starter.yaml", "--icon-catalog", "nowhere/icons.yaml",
          "-o", "out.svg"),
    _case("render-output-extension-unknown", "render", "starter.yaml", "-o", "out.gif"),
    _case("render-output-format-mismatch", "render", "starter.yaml", "--format", "png", "-o", "out.svg"),
    _case("render-bad-viewport-shape", "render", "starter.yaml", "--viewport", "900", "-o", "out.svg"),
    _case("render-bad-viewport-number", "render", "starter.yaml", "--viewport", "wide x tall", "-o", "out.svg"),
    _case("render-bad-viewport-zero", "render", "starter.yaml", "--viewport", "0x100", "-o", "out.svg"),
    _case("render-bad-viewport-and-unknown-preset", "render", "starter.yaml", "--viewport", "0x100",
          "--preset", "no-such-preset", "-o", "out.svg"),
    _case("render-typesetter-descriptor-missing", "render", "starter.yaml", "--format", "typst", "-o", "out.typ"),
    _case("render-typesetter-descriptor-on-svg", "render", "starter.yaml", "--typesetter-engine", "typst",
          "-o", "out.svg"),
    _case("render-typst-with-descriptor", "render", "starter.yaml", "--format", "typst", "--typesetter-engine", "typst",
          "--typesetter-version", "0.13.1", "--typesetter-adapter-grammar", "chrona/typst-adapter/v0.1",
          "-o", "out.typ"),
    _case("render-emit-scene-exists", "render", "starter.yaml", "-o", "out.svg", "--emit-scene", "scene.json",
          pre=(("render", "starter.yaml", "-o", "first.svg", "--emit-scene", "scene.json"),)),
    _case("render-missing-output-argument", "render", "starter.yaml"),
    _case("render-no-project-argument", "render", "-o", "out.svg"),
    _case("render-output-directory-missing", "render", "starter.yaml", "-o", "nowhere/out.svg"),
    _case("render-unexpected-exception", "render", "starter.yaml", "-o", "out.svg", boom=True),
    # the rest of the exception ladder, through other commands
    _case("preset-list", "preset", "list"),
    _case("preset-copy-unknown", "preset", "copy", "no-such-preset", "--output", "pc"),
    _case("preset-copy-into-existing-directory", "preset", "copy", "editorial", "--output", "halcyon-1"),
    _case("identity-bytes-ok", "identity", "bytes", "starter.yaml"),
    _case("identity-bytes-missing", "identity", "bytes", "missing.yaml"),
    _case("identity-document-ok", "identity", "document", "starter.yaml"),
    _case("identity-document-not-an-object", "identity", "document", "not-a-mapping.yaml"),
    _case("identity-document-broken-yaml", "identity", "document", "broken-yaml.yaml"),
    _case("identity-document-broken-json", "identity", "document", "broken.json"),
    _case("font-import-missing-source", "font", "import", "missing.ttf", "--family", "X", "--weight", "400",
          "--output", "fonts"),
    _case("font-import-not-a-font", "font", "import", "starter.yaml", "--family", "X", "--weight", "400",
          "--output", "fonts"),
    _case("icon-catalog-import-missing-source", "icon-catalog", "import", "missing.json", "--license-spdx", "MIT",
          "--notice-file", "starter.yaml", "--output", "icons.yaml"),
    _case("icon-catalog-import-missing-licence", "icon-catalog", "import", "starter.yaml", "--output", "icons.yaml"),
    _case("render-review-missing-context", "render-review", "--context-reference", "missing.yaml",
          "--snapshot-root", "snaps", "--store-identity", "char-store", "-o", "out.svg"),
    _case("render-review-no-store", "render-review", "--context-reference", "starter.yaml", "-o", "out.svg"),
    _case("render-review-store-config-missing", "render-review", "--context-reference", "starter.yaml",
          "--store-config", "missing-store.yaml", "-o", "out.svg"),
    _case("render-review-gallery-one-context", "render-review-gallery", "--context-reference", "starter.yaml",
          "--snapshot-root", "snaps", "--store-identity", "char-store", "--output-directory", "gallery"),
    _case("render-workspace-missing", "render-workspace", "missing.yaml", "-o", "out.svg"),
    _case("render-workspace-bad-viewport", "render-workspace", "missing.yaml", "--viewport", "0x0", "-o", "out.svg"),
    _case("workspace-revision-missing", "workspace", "revision", "missing.yaml"),
    _case("review-missing-reference", "review", "a.yaml", "b.yaml", "--snapshot-root", "snaps",
          "--store-identity", "char-store"),
    _case("command-check-broken-json", "command-check", "--command", "broken.json", "--result", "result.json"),
    _case("command-check-missing", "command-check", "--command", "missing.yaml", "--result", "result.json"),
)


# --------------------------------------------------------------------------- running


@contextlib.contextmanager
def _boom():
    """Make every Path read raise a RuntimeError: an unexpected failure at the boundary."""
    saved = {name: getattr(pathlib.Path, name) for name in ("open", "read_text", "read_bytes")}

    def explode(self, *args, **kwargs):
        raise RuntimeError("characterization: unexpected failure")

    for name in saved:
        setattr(pathlib.Path, name, explode)
    try:
        yield
    finally:
        for name, value in saved.items():
            setattr(pathlib.Path, name, value)


def _invoke(argv: tuple[str, ...], boom: bool = False) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    saved = sys.argv
    sys.argv = ["chrona", *argv]
    code = 0
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            with (_boom() if boom else contextlib.nullcontext()):
                try:
                    main()
                except SystemExit as exit_:
                    code = exit_.code if isinstance(exit_.code, int) else (0 if exit_.code is None else 1)
    finally:
        sys.argv = saved
    return code, out.getvalue(), err.getvalue()


def _populate(root: pathlib.Path) -> set[str]:
    for source in FIXTURES.rglob("*"):
        if source.is_file() and source.name != "golden.json":
            relative = source.relative_to(FIXTURES)
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    for name, text in _SYNTHETIC.items():
        (root / name).write_text(text, encoding="utf-8")
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


def _describe(path: pathlib.Path) -> dict[str, object]:
    data = path.read_bytes()
    suffix = path.suffix
    if suffix == ".svg":
        try:
            return {"kind": "svg", "root": ET.fromstring(data).tag}
        except ET.ParseError:
            return {"kind": "svg", "root": None}
    if suffix == ".png":
        return {"kind": "png", "signature": data[:8] == b"\x89PNG\r\n\x1a\n"}
    if suffix == ".json":
        try:
            value = json.loads(data)
        except ValueError:
            return {"kind": "json", "valid": False}
        return {"kind": "json", "keys": sorted(value) if isinstance(value, dict) else None}
    return {"kind": suffix.lstrip(".") or "file"}


_OS_ERROR = re.compile(r"\[(?:Errno|WinError) \d+\] [^:]*?: ")


def _normalise(text: str, root: pathlib.Path) -> str:
    for spelling in {str(root), root.as_posix(), str(root.resolve()), root.resolve().as_posix()}:
        text = text.replace(spelling, "<tmp>")
        text = text.replace(spelling.replace("\\", "\\\\"), "<tmp>")
    text = _OS_ERROR.sub("<os error>: ", text)
    # On Windows a relative path in a message carries a backslash, which the JSON text escapes as two
    # characters; the record uses the POSIX spelling so one golden file serves every OS.
    return re.sub(r"\\{2,}", "/", text)


def _stream(text: str, *, preserve: bool = False) -> object:
    if preserve or len(text) <= 3000:
        return text
    return {"sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "lines": text.count("\n"), "length": len(text)}


def _warning_stream(text: str) -> object:
    """Describe the stderr warning lines of a successful render without pinning their wording.

    Each line must be one JSON object printed with sorted keys; the record keeps the line
    count per code and the key set, so a changed format fails while a changed layout
    finding (which warnings a given render raises) does not rewrite the golden file.
    """
    lines = [line for line in text.split("\n") if line]
    summary: dict[str, dict[str, object]] = {}
    for line in lines:
        try:
            value = json.loads(line)
        except ValueError:
            return {"unparsed": _stream(text)}
        canonical = json.dumps(value, ensure_ascii=False, sort_keys=True)
        entry = summary.setdefault(str(value.get("code")), {"count": 0, "keys": sorted(value), "sortedKeyLines": True})
        entry["count"] = int(entry["count"]) + 1
        entry["sortedKeyLines"] = bool(entry["sortedKeyLines"]) and canonical == line
        if entry["keys"] != sorted(value):
            entry["keys"] = sorted(set(entry["keys"]) | set(value))
    return {"endsWithNewline": text.endswith("\n"), "codes": dict(sorted(summary.items()))}


def run_case(case: Case) -> tuple[dict[str, object], dict[str, object]]:
    """Return ``(golden record, raw record)`` for one invocation in a fresh directory."""
    previous = pathlib.Path.cwd()
    with tempfile.TemporaryDirectory(prefix="chrona-characterization-") as scratch:
        root = pathlib.Path(scratch)
        initial = _populate(root)
        os.chdir(root)
        try:
            for argv in case.pre:
                _invoke(argv)
            if case.edit is not None:
                case.edit(root)
            code, stdout, stderr = _invoke(case.argv, case.boom)
            written = sorted(
                path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
            )
        finally:
            os.chdir(previous)
        created = [name for name in written if name not in initial]
        files = {name: _describe(root / name) for name in created}
        raw_files = {
            name: {**files[name], "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest(),
                   "size": (root / name).stat().st_size}
            for name in created
        }
        golden = {
            "argv": list(case.argv), "exit": code,
            "stdout": _stream(_normalise(stdout, root), preserve=(code == 0 and case.argv[0] in {
                "render", "render-review", "render-workspace"})),
            "stderr": _warning_stream(stderr) if code == 0 and stderr else _stream(_normalise(stderr, root)),
            "files": files,
        }
        raw = {"argv": list(case.argv), "exit": code, "stdout": stdout.replace(str(root), "<tmp>"),
               "stderr": stderr.replace(str(root), "<tmp>"), "files": raw_files}
    return golden, raw


def _load_golden() -> dict[str, dict[str, object]]:
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


def test_case_ids_are_unique():
    ids = [case.id for case in CASES]
    assert len(ids) == len(set(ids))


def test_golden_records_exactly_the_matrix():
    assert sorted(_load_golden()) == sorted(case.id for case in CASES)


@pytest.mark.parametrize("case", CASES, ids=[case.id for case in CASES])
def test_cli_output_is_unchanged(case: Case):
    golden, raw = run_case(case)
    target = os.environ.get("CHRONA_CHARACTERIZATION_RAW")
    if target:
        with open(target, "a", encoding="utf-8") as stream:
            stream.write(json.dumps({"id": case.id, **raw}, sort_keys=True, ensure_ascii=False) + "\n")
    assert golden == _load_golden()[case.id]


def test_golden_holds_no_host_path():
    text = GOLDEN.read_text(encoding="utf-8")
    for needle in ("/Users/", "/home/", "/private/", "/var/folders", "C:\\\\", "AppData", "chrona-characterization-"):
        assert needle not in text, needle


def _record() -> None:
    records = {}
    # Capture exact artifacts in the same pass as the golden, not a second
    # round of expensive renders just to recover their byte evidence.
    with contextlib.ExitStack() as stack:
        target = os.environ.get("CHRONA_CHARACTERIZATION_RAW")
        raw_stream = stack.enter_context(open(target, "w", encoding="utf-8")) if target else None
        for case in CASES:
            golden, raw = run_case(case)
            records[case.id] = golden
            if raw_stream is not None:
                raw_stream.write(json.dumps({"id": case.id, **raw}, sort_keys=True, ensure_ascii=False) + "\n")
    GOLDEN.write_text(json.dumps(records, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"recorded {len(records)} cases to {GOLDEN}")


def test_successful_render_envelopes_remain_auditable_above_the_stream_digest_limit():
    envelope = json.dumps({"status": "ok", "diagnostics": [], "warnings": [
        {"code": "W_LAYOUT_LABEL_SUPPRESSED", "message": "x" * 4000}
    ]})
    assert _stream(envelope, preserve=True) == envelope
    assert isinstance(_stream(envelope), dict)


def test_record_captures_golden_and_byte_evidence_in_one_pass(tmp_path, monkeypatch):
    target = tmp_path / "raw.jsonl"
    golden_path = tmp_path / "golden.json"
    cases = (Case("first", ("render",)), Case("second", ("render",)))
    calls = []

    def invoke(case):
        calls.append(case.id)
        return {"exit": 0}, {"files": {"output.svg": {"sha256": case.id}}}

    monkeypatch.setattr(sys.modules[__name__], "GOLDEN", golden_path)
    monkeypatch.setattr(sys.modules[__name__], "CASES", cases)
    monkeypatch.setattr(sys.modules[__name__], "run_case", invoke)
    monkeypatch.setenv("CHRONA_CHARACTERIZATION_RAW", str(target))
    _record()
    assert calls == ["first", "second"]
    assert json.loads(golden_path.read_text()) == {"first": {"exit": 0}, "second": {"exit": 0}}
    assert [json.loads(line)["files"]["output.svg"]["sha256"]
            for line in target.read_text().splitlines()] == calls


if __name__ == "__main__":  # pragma: no cover
    if "--record" not in sys.argv:
        raise SystemExit("usage: python -m tests.cli.test_cli_characterization --record")
    _record()


def test_normalise_uses_the_posix_spelling_of_a_windows_relative_path(tmp_path):
    """Windows stdout carries `nowhere\\\\view.yaml` (repr escape, then JSON escape: four backslashes); the golden file records `nowhere/view.yaml`."""
    posix = '{"message": "[Errno 2] No such file or directory: \'nowhere/view.yaml\'"}'
    expected = '{"message": "<os error>: \'nowhere/view.yaml\'"}'
    for backslashes in ("\\" * 4, "\\" * 2):
        windows = ('{"message": "[WinError 2] The system cannot find the file specified: '
                   f"\'nowhere{backslashes}view.yaml\'\"}}")
        assert _normalise(windows, tmp_path) == expected
    assert _normalise(posix, tmp_path) == expected
