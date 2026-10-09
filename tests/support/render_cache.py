"""A digest-keyed render cache shared by every xdist worker of one pytest run (#657).

The cache renders one *unmodified committed input* through the public CLI once and hands
the same result to every test that asks for it.  A test that changes its input renders
its own copy and never uses this module: the key covers the bytes of every input file, and
paths outside ``examples/`` and ``src/chrona/resources/`` are rejected, so a stale or
foreign hit is impossible.

Results are immutable (``bytes``/``str``); ``scene`` and ``warnings`` are parsed afresh on
every access, so one test cannot change what another sees.

Sharing between xdist workers is through a directory (``O_EXCL`` lock files and
``os.replace``, portable to Windows).  ``renders.log`` has one line per real render and is
the render counter; the miss path refuses to render a key that is already logged.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALLOWED_ROOTS = (ROOT / "examples", ROOT / "src" / "chrona" / "resources")
LOCK_TIMEOUT_SECONDS = 300.0


class RenderCacheError(RuntimeError):
    """The cache could not produce or wait for a render."""


@dataclass(frozen=True)
class RenderKey:
    project: str
    actual: str | None
    preset: str | None
    extra: tuple[str, ...]
    inputs: str

    @property
    def digest(self) -> str:
        blob = json.dumps([self.project, self.actual, self.preset, list(self.extra), self.inputs])
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]

    @property
    def label(self) -> str:
        parts = [self.project]
        if self.actual:
            parts.append(f"actual={self.actual}")
        if self.preset:
            parts.append(f"preset={self.preset}")
        parts.extend(self.extra)
        return " ".join(parts)


@dataclass(frozen=True)
class RenderResult:
    svg: bytes
    scene_text: str
    stdout: str
    stderr: str

    @property
    def scene(self) -> dict:
        """The Scene JSON, parsed afresh: mutating it never reaches another reader."""
        return json.loads(self.scene_text)

    @property
    def warnings(self) -> list[dict]:
        """The CLI success-envelope warning rows, parsed afresh from stdout."""
        envelope = json.loads(self.stdout)
        if envelope.get("status") != "ok" or envelope.get("diagnostics") != []:
            raise RenderCacheError("a successful cached render requires the CLI success envelope")
        warnings = envelope.get("warnings")
        if not isinstance(warnings, list):
            raise RenderCacheError("the CLI success envelope must contain warning rows")
        return warnings


def _under_allowed_root(path: Path) -> bool:
    resolved = path.resolve()
    return any(root == resolved or root in resolved.parents for root in ALLOWED_ROOTS)


def _files_under(path: Path) -> list[Path]:
    return sorted(item for item in path.rglob("*") if item.is_file()) if path.is_dir() else [path]


def digest_files(paths: list[Path]) -> str:
    """SHA-256 over the relative name and bytes of every file, so any edit changes it."""
    hasher = hashlib.sha256()
    for path in paths:
        hasher.update(str(path).encode("utf-8") + b"\0")
        hasher.update(path.read_bytes())
    return hasher.hexdigest()


def _repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def make_key(project: str | Path, actual: str | Path | None = None, preset: str | None = None,
             extra: tuple[str, ...] = ()) -> RenderKey:
    """Build a key and refuse any input the cache may not serve."""
    files: list[Path] = []
    paths = [_repo_path(project)] + ([_repo_path(actual)] if actual else [])
    for token in extra:
        candidate = _repo_path(token)
        if not token.startswith("-") and candidate.exists():
            paths.append(candidate)
    for path in paths:
        if not _under_allowed_root(path):
            raise ValueError(f"the render cache only serves committed inputs, not {path}")
        files.extend(_files_under(path))
    if preset is not None:
        bundle = ROOT / "src" / "chrona" / "resources" / "presets"
        files.extend([bundle / "library.yaml", *_files_under(bundle / "bundles" / preset)])
    relative = lambda path: _repo_path(path).relative_to(ROOT).as_posix()  # noqa: E731
    return RenderKey(relative(project), relative(actual) if actual else None, preset, tuple(extra),
                     digest_files(files))


def render_uncached(argv: list[str]) -> tuple[str, str]:
    """Run the CLI in-process with ``argv`` and return ``(stdout, stderr)``.

    Raises ``RenderCacheError`` on a non-zero exit.
    """
    from chrona.app.cli import main

    out, err = io.StringIO(), io.StringIO()
    saved = sys.argv
    sys.argv = ["chrona", *argv]
    code: object = 0
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                main()
            except SystemExit as exited:
                code = exited.code
    finally:
        sys.argv = saved
    if code not in (0, None):
        raise RenderCacheError(f"chrona {' '.join(argv)} exited {code}: {err.getvalue()[-500:]}{out.getvalue()[-500:]}")
    return out.getvalue(), err.getvalue()


class RenderCache:
    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self._log = root / "renders.log"

    def render(self, project: str | Path, actual: str | Path | None = None, preset: str | None = None,
               extra: tuple[str, ...] = ()) -> RenderResult:
        key = make_key(project, actual, preset, extra)
        entry = self.root / key.digest
        if entry.is_dir():
            return self._load(entry)
        lock = self.root / f"{key.digest}.lock"
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return self._wait_for(entry, lock)
        try:
            if entry.is_dir():  # another worker finished between our check and our lock
                return self._load(entry)
            if key.digest in self._logged():
                raise RenderCacheError(f"refusing a second render of {key.label}")
            return self._render(key, entry)
        finally:
            os.close(descriptor)
            with contextlib.suppress(FileNotFoundError):
                lock.unlink()

    def render_counts(self) -> dict[str, int]:
        """Real renders so far in this run, by key digest (across all workers)."""
        counts: dict[str, int] = {}
        for digest in self._logged():
            counts[digest] = counts.get(digest, 0) + 1
        return counts

    def labels(self) -> dict[str, str]:
        found: dict[str, str] = {}
        if self._log.is_file():
            for line in self._log.read_text(encoding="utf-8").splitlines():
                digest, _, label = line.partition("\t")
                found[digest] = label
        return found

    def _logged(self) -> list[str]:
        if not self._log.is_file():
            return []
        return [line.partition("\t")[0] for line in self._log.read_text(encoding="utf-8").splitlines() if line]

    def _render(self, key: RenderKey, entry: Path) -> RenderResult:
        staging = self.root / f"{key.digest}.tmp"
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir()
        argv = ["render", str(_repo_path(key.project))]
        if key.actual:
            argv += ["--actual", str(_repo_path(key.actual))]
        if key.preset:
            argv += ["--preset", key.preset]
        argv += list(key.extra)
        argv += ["--output", str(staging / "out.svg"), "--emit-scene", str(staging / "scene.json")]
        stdout, stderr = render_uncached(argv)
        (staging / "stdout.txt").write_text(stdout, encoding="utf-8")
        (staging / "stderr.txt").write_text(stderr, encoding="utf-8")
        descriptor = os.open(self._log, os.O_CREAT | os.O_APPEND | os.O_WRONLY)
        try:
            os.write(descriptor, f"{key.digest}\t{key.label}\n".encode("utf-8"))
        finally:
            os.close(descriptor)
        os.replace(staging, entry)
        return self._load(entry)

    def _wait_for(self, entry: Path, lock: Path) -> RenderResult:
        deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if entry.is_dir():
                return self._load(entry)
            if not lock.exists():
                if entry.is_dir():
                    return self._load(entry)
                raise RenderCacheError(f"the worker rendering {entry.name} failed; see its own test failure")
            time.sleep(0.1)
        raise RenderCacheError(f"timed out waiting for the render of {entry.name}")

    @staticmethod
    def _load(entry: Path) -> RenderResult:
        return RenderResult(
            svg=(entry / "out.svg").read_bytes(),
            scene_text=(entry / "scene.json").read_text(encoding="utf-8"),
            stdout=(entry / "stdout.txt").read_text(encoding="utf-8"),
            stderr=(entry / "stderr.txt").read_text(encoding="utf-8"),
        )
