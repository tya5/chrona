"""The workspace an agent tool may read: one resolved root, a path guard, and a scrubber.

An agent names files by text, so every path is untrusted. ``WorkspaceScope`` resolves its
root once, refuses a filesystem root, and turns a tool's path argument into a regular
file strictly inside that root through the shared Store address guard
(``core.store_address``, the same syntax and containment rules the Store uses). It adds
what the guard does not: Windows reserved device names, a regular-file requirement and a
size cap. It also holds the scrubber that keeps host paths out of a result.

This module is SDK-free and prints nothing. It is a safety rail for a local process the
user started, not a sandbox against a hostile agent that has its own shell: the check and
the open are two steps (a symlink swapped in between is not detected).
"""
from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path
from typing import Any

from chrona.core.store_address import StoreAddressError, check_store_address, resolve_store_address
from chrona.usecases.failure_report import StableFailure

MAX_INPUT_BYTES = 2 * 1024 * 1024
"""An input file larger than this is refused: YAML alias expansion is otherwise unbounded."""

_COMPONENT = "mcp"
_RESERVED_DEVICE_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    | {f"COM{digit}" for digit in "123456789¹²³"}
    | {f"LPT{digit}" for digit in "123456789¹²³"}
)

# A host path that survives the exact-string pass: a Windows drive or UNC path, or a POSIX path under a
# top-level directory that only a host has. A JSON pointer or a workspace-relative path never matches.
_HOST_PATH = re.compile(
    r"[A-Za-z]:[\\/][^\s'\"<>|*?]*"
    r"|\\\\[^\s'\"\\]+\\[^\s'\"<>|*?]*"
    r"|(?<![\w.~-])/(?:Users|home|private|var|tmp|opt|usr|etc|mnt|Volumes)"
    r"(?:/[^\s'\"<>:,;()\[\]{}]*)?"
)


def _failure(code: str, message: str, source_ref: str) -> StableFailure:
    return StableFailure(code, message, _COMPONENT, source_ref, 2)


def _is_device_name(segment: str) -> bool:
    """Whether Windows would open ``segment`` as a device: the stem before the first dot, ignoring case and spaces."""
    return segment.split(".", 1)[0].strip(" ").upper() in _RESERVED_DEVICE_NAMES


class WorkspaceScope:
    """The one directory a tool call may read below, resolved once at construction."""

    def __init__(self, root: str | Path):
        given = Path(root)
        try:
            resolved = given.resolve()
            is_directory = resolved.is_dir()
        except (OSError, RuntimeError) as error:
            raise _failure("E_INPUT_IO", "the workspace directory cannot be resolved", "/workspace") from error
        if not is_directory:
            raise _failure("E_INPUT_IO", "the workspace is not an existing directory", "/workspace")
        if resolved.parent == resolved:
            raise _failure(
                "E_MCP_WORKSPACE_TOO_BROAD",
                "the workspace must be a project directory, not a filesystem root; start the server with --workspace DIR",
                "/workspace",
            )
        self._root = resolved
        self._scrub_exact = self._host_strings(given, resolved)

    def _host_strings(self, given: Path, resolved: Path) -> tuple[tuple[str, str], ...]:
        """``(text, replacement)`` pairs, longest text first: the workspace becomes empty, other host roots ``<path>``."""
        workspace = {str(resolved), resolved.as_posix(), str(given), given.as_posix(), str(given.absolute()),
                     given.absolute().as_posix()}
        others: set[str] = set()
        for candidate in (Path.cwd, Path.home, lambda: Path(tempfile.gettempdir())):
            try:
                path = candidate()
                others.update({str(path), path.as_posix(), str(path.resolve()), path.resolve().as_posix()})
            except (OSError, RuntimeError):
                continue
        others.update({sys.prefix, sys.base_prefix, sys.exec_prefix, str(Path(__file__).resolve().parents[1])})
        pairs = {text: "" for text in workspace}
        pairs.update({text: "<path>" for text in others if text not in workspace})
        # A text shorter than three characters (a filesystem root, ".") would mangle every message.
        usable = {text: value for text, value in pairs.items() if len(text) >= 3 and text.strip("/\\.") != ""}
        return tuple(sorted(usable.items(), key=lambda item: (-len(item[0]), item[0])))

    def resolve_path(self, value: object, pointer: str) -> Path:
        """Return the resolved regular file ``value`` names below the workspace, or raise ``StableFailure``.

        ``pointer`` is the input property (``/project``) reported as the diagnostic's ``sourceRef``.
        """
        try:
            segments = check_store_address(value, charset="file-name")
        except StoreAddressError as error:
            raise _failure(
                "E_MCP_PATH_SYNTAX",
                f"not a workspace-relative path ({error.reason}); use a '/'-separated path below the workspace root, "
                "such as plans/project.yaml",
                pointer,
            ) from error
        if any(_is_device_name(segment) for segment in segments):
            raise _failure("E_MCP_PATH_SYNTAX",
                           "a path segment names a reserved device (CON, PRN, AUX, NUL, COMn, LPTn); rename the file",
                           pointer)
        try:
            target = resolve_store_address(self._root, value, charset="file-name")
        except StoreAddressError as error:
            raise _failure("E_MCP_PATH_CONTAINMENT",
                           "the path resolves outside the workspace; use a path whose real location is inside the workspace root",
                           pointer) from error
        try:
            if not target.is_file():
                raise _failure("E_INPUT_IO", "no regular file exists at this workspace path", pointer)
            size = target.stat().st_size
        except OSError as error:
            raise _failure("E_INPUT_IO", "the file at this workspace path cannot be read", pointer) from error
        if size > MAX_INPUT_BYTES:
            raise _failure(
                "E_MCP_INPUT_TOO_LARGE",
                f"the file is larger than {MAX_INPUT_BYTES} bytes; split the plan or use the chrona command line",
                pointer,
            )
        return target

    def scrub(self, text: str) -> str:
        """Remove host paths from ``text``: the workspace prefix goes, every other absolute host path becomes ``<path>``."""
        for needle, replacement in self._scrub_exact:
            if replacement == "":
                # Drop the root and its separator so ``<root>/plans/p.yaml`` becomes ``plans/p.yaml``.
                text = text.replace(needle + "/", "").replace(needle + "\\", "").replace(needle, ".")
            else:
                text = text.replace(needle, replacement)
        return _HOST_PATH.sub("<path>", text)

    def scrub_value(self, value: Any) -> Any:
        """``scrub`` applied to every string inside a JSON-like value (keys are kept)."""
        if isinstance(value, str):
            return self.scrub(value)
        if isinstance(value, dict):
            return {key: self.scrub_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.scrub_value(item) for item in value]
        return value
