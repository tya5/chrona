"""Schema validation-equivalence gate (I662-S0).

The gate proves, before and after a schema change, that the set of accepted
documents did not move except where a listed delta says so.  It is deliberately
independent of the production loader: it reads ``schemas/`` itself, builds its own
``referencing.Registry`` from every schema ``$id`` and derives the
document-to-schema mapping from each schema's ``version`` constant.  A future
loader bug therefore cannot hide itself from the gate.

Three layers:

* L1 structural: a canonical fingerprint of every schema's *dereferenced* form
  (references inlined, annotations and unused ``$defs`` removed).  ``--base-rev``
  compares the working tree with a git revision.
* L2 corpus: every tracked YAML/JSON document whose ``version`` maps to a schema is
  validated; verdict and first error are compared with the recorded baseline.
* L3 diagnostics: baseline-invalid documents and a probe matrix go through the
  production ingress functions; ``(code, pointer, rule, message)`` is compared with
  the recorded baseline.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import unquote, urljoin

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from tools.schema_inventory import SchemaInventoryError, _additive_only_change, validate_inventory


SCHEMA_SUFFIXES = (".schema.yaml", ".schema.json")
DOCUMENT_SUFFIXES = (".yaml", ".yml", ".json")
EXCLUDED_PREFIXES = ("schemas/", ".github/", "docs/archive/")
EQUIVALENCE_DIRECTORY = Path("conformance/schema-equivalence")
EXPECTED_INVALID = EQUIVALENCE_DIRECTORY / "expected-invalid-v0.1.yaml"
EXPECTED_DELTAS = EQUIVALENCE_DIRECTORY / "expected-deltas-v0.1.yaml"
BASELINE = EQUIVALENCE_DIRECTORY / "baseline-results-v0.1.json"
BASELINE_VERSION = "chrona/schema-equivalence-baseline/v0.1"
EXPECTED_INVALID_VERSION = "chrona/schema-equivalence-expected-invalid/v0.1"
EXPECTED_DELTAS_VERSION = "chrona/schema-equivalence-expected-deltas/v0.1"

# Runtime budget for L2 plus L3 in one process, in seconds (conformance runs it as one step).
RUNTIME_BUDGET_SECONDS = 60.0
# A merged L1 entry is stale (its PR landed, so no later base can use it). It may outlive its landing by this many
# later merges that touch `schemas/`; beyond that a `--base-rev` run fails until `--prune-stale` retires it (#970).
STALE_MERGE_LIMIT = 1

# Explicit document-version to schema-file overrides.  The mapping is otherwise derived from each
# schema's ``version`` constant; the overrides pin the two families whose schema file name does not
# spell the document version (summary-profile: file v0.2 accepts documents declaring v0.1) or whose
# constant is declared through a local ``$ref`` (scene).  A test asserts that the derivation agrees.
VERSION_OVERRIDES = {
    "chrona/summary-profile/v0.1": "summary-profile-v0.2.schema.yaml",
    "chrona/scene/v0.6": "scene-v0.6.schema.yaml",
    "chrona/scene/v0.7": "scene-v0.7.schema.yaml",
}

_MISSING = object()

_ANNOTATION_KEYS = frozenset({
    "title", "description", "examples", "default", "deprecated", "readOnly", "writeOnly", "$comment",
})
_DROPPED_KEYS = _ANNOTATION_KEYS | {"$id", "$schema", "$defs", "definitions", "$anchor"}
_SCHEMA_VALUED = frozenset({
    "items", "additionalProperties", "contains", "not", "if", "then", "else", "propertyNames",
    "unevaluatedItems", "unevaluatedProperties", "contentSchema",
})
_SCHEMA_LISTS = frozenset({"allOf", "anyOf", "oneOf", "prefixItems"})
_SCHEMA_MAPS = frozenset({"properties", "patternProperties", "dependentSchemas"})
# Keywords that assert on their own instance without looking at sibling keywords, so a sibling of
# ``$ref`` can be folded into the target without changing what is accepted.
_INDEPENDENT_KEYWORDS = frozenset({
    "type", "enum", "const", "minLength", "maxLength", "pattern", "format", "minimum", "maximum",
    "exclusiveMinimum", "exclusiveMaximum", "multipleOf", "minItems", "maxItems", "uniqueItems",
    "minProperties", "maxProperties", "required",
})


class GateError(ValueError):
    """The gate itself could not run (unreadable schema, unresolved reference, bad record file)."""


# --------------------------------------------------------------------------------------------
# Reading schemas and documents (no production loader)
# --------------------------------------------------------------------------------------------

_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def _decode(name: str, content: bytes) -> Any:
    if name.endswith(".json"):
        return json.loads(content)
    return yaml.load(content, Loader=_YAML_LOADER)


def _git(root: Path, *args: str) -> bytes:
    completed = subprocess.run(("git", "-C", str(root), *args), check=False, capture_output=True)
    if completed.returncode != 0:
        raise GateError(f"E_EQUIV_GIT:{' '.join(args)}:{completed.stderr.decode(errors='replace').strip()}")
    return completed.stdout


def load_schema_dir(directory: Path) -> dict[str, Any]:
    """Read every schema file of a directory, keyed by file name."""
    schemas: dict[str, Any] = {}
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.name.endswith(SCHEMA_SUFFIXES):
            schemas[path.name] = _decode(path.name, path.read_bytes())
    return schemas


def load_schema_rev(root: Path, rev: str) -> dict[str, Any]:
    """Read every schema file as committed at a git revision."""
    listing = _git(root, "ls-tree", "-r", "--name-only", rev, "--", "schemas/").decode().splitlines()
    schemas: dict[str, Any] = {}
    for entry in sorted(listing):
        name = entry.removeprefix("schemas/")
        if "/" not in name and name.endswith(SCHEMA_SUFFIXES):
            schemas[name] = _decode(name, _git(root, "show", f"{rev}:{entry}"))
    return schemas


def tracked_documents(root: Path) -> dict[str, bytes]:
    """Return tracked YAML/JSON documents outside the excluded trees, keyed by POSIX path."""
    listing = _git(root, "ls-files", "-z").decode().split("\0")
    documents: dict[str, bytes] = {}
    for entry in sorted(item for item in listing if item):
        if not entry.endswith(DOCUMENT_SUFFIXES) or entry.startswith(EXCLUDED_PREFIXES):
            continue
        path = root / entry
        if path.is_file():
            documents[entry] = path.read_bytes()
    return documents


def build_registry(schemas: Mapping[str, Any]) -> Registry:
    """A registry of every schema ``$id``, independent of ``chrona.resources``."""
    registry = Registry()
    seen: dict[str, str] = {}
    for name in sorted(schemas):
        schema = schemas[name]
        identifier = schema.get("$id") if isinstance(schema, dict) else None
        if not isinstance(identifier, str) or not identifier:
            raise GateError(f"E_EQUIV_SCHEMA_ID:{name}")
        if identifier in seen:
            raise GateError(f"E_EQUIV_SCHEMA_ID_DUPLICATE:{identifier}:{seen[identifier]}:{name}")
        seen[identifier] = name
        registry = registry.with_resource(identifier, Resource.from_contents(schema))
    return registry


def _json_pointer(tokens: Iterable[Any]) -> str:
    return "".join("/" + str(token).replace("~", "~0").replace("/", "~1") for token in tokens)


def _pointer_tokens(pointer: str) -> list[str]:
    if pointer in ("", "#"):
        return []
    text = unquote(pointer.removeprefix("#"))
    if not text.startswith("/"):
        raise GateError(f"E_EQUIV_POINTER:{pointer}")
    return [token.replace("~1", "/").replace("~0", "~") for token in text[1:].split("/")]


def _follow(tree: Any, tokens: list[str]) -> Any:
    node = tree
    for token in tokens:
        if isinstance(node, dict) and token in node:
            node = node[token]
        elif isinstance(node, list) and token.isdigit() and int(token) < len(node):
            node = node[int(token)]
        else:
            return _MISSING
    return node


# --------------------------------------------------------------------------------------------
# Version derivation (document version -> schema file)
# --------------------------------------------------------------------------------------------

def _declared_version(schema: Mapping[str, Any]) -> str | None:
    """The schema's ``version`` constant: root property or an enveloping ``allOf`` branch."""
    branches: list[Any] = [schema]
    all_of = schema.get("allOf")
    if isinstance(all_of, list):
        branches.extend(item for item in all_of if isinstance(item, dict))
    for branch in branches:
        properties = branch.get("properties")
        version = properties.get("version") if isinstance(properties, dict) else None
        seen = 0
        while isinstance(version, dict) and "$ref" in version and seen < 8:
            ref = version["$ref"]
            if not isinstance(ref, str) or not ref.startswith("#"):
                version = None
                break
            version = _follow(schema, _pointer_tokens(ref))
            version = None if version is _MISSING else version
            seen += 1
        if isinstance(version, dict) and isinstance(version.get("const"), str):
            return version["const"]
    return None


def derive_version_map(schemas: Mapping[str, Any]) -> dict[str, str]:
    """Map each declared document version to its schema file; overrides win and are checked."""
    derived: dict[str, list[str]] = {}
    for name in sorted(schemas):
        version = _declared_version(schemas[name])
        if version is not None:
            derived.setdefault(version, []).append(name)
    mapping: dict[str, str] = {}
    for version, names in derived.items():
        if len(names) > 1 and version not in VERSION_OVERRIDES:
            raise GateError(f"E_EQUIV_VERSION_AMBIGUOUS:{version}:{names}")
        mapping[version] = names[0]
    for version, name in VERSION_OVERRIDES.items():
        if name not in schemas:
            raise GateError(f"E_EQUIV_VERSION_OVERRIDE:{version}:{name}")
        mapping[version] = name
    return mapping


# --------------------------------------------------------------------------------------------
# L1: structural fingerprint of the dereferenced schema
# --------------------------------------------------------------------------------------------

class _Dereferencer:
    """Inline every ``$ref`` (local and external) and strip what does not affect acceptance."""

    def __init__(self, schemas: Mapping[str, Any]) -> None:
        self._by_id = {schema["$id"]: schema for schema in schemas.values()}
        self._schemas = schemas
        self._memo: dict[tuple[str, str], Any] = {}
        self._cycles = 0

    def root(self, name: str) -> Any:
        schema = self._schemas[name]
        return self._walk(schema, schema["$id"], frozenset())

    def _resolve(self, ref: str, base: str) -> tuple[str, str, Any]:
        target, _, fragment = ref.partition("#")
        if not target:
            identifier = base
        elif target in self._by_id:
            identifier = target
        elif urljoin(base, target) in self._by_id:
            identifier = urljoin(base, target)
        else:
            raise GateError(f"E_EQUIV_REF_UNRESOLVED:{ref}:from {base}")
        node = _follow(self._by_id[identifier], _pointer_tokens(fragment))
        if node is _MISSING:
            raise GateError(f"E_EQUIV_REF_UNRESOLVED:{ref}:from {base}")
        return identifier, fragment, node

    def _walk(self, schema: Any, identifier: str, active: frozenset[tuple[str, str]]) -> Any:
        if not isinstance(schema, dict):
            return schema
        out: dict[str, Any] = {}
        for key, value in schema.items():
            if key in _DROPPED_KEYS or key == "$ref":
                continue
            if key in _SCHEMA_VALUED:
                out[key] = (
                    [self._walk(item, identifier, active) for item in value]
                    if isinstance(value, list) else self._walk(value, identifier, active)
                )
            elif key in _SCHEMA_LISTS and isinstance(value, list):
                out[key] = [self._walk(item, identifier, active) for item in value]
            elif key in _SCHEMA_MAPS and isinstance(value, dict):
                out[key] = {name: self._walk(item, identifier, active) for name, item in value.items()}
            else:
                out[key] = value
        ref = schema.get("$ref")
        if not isinstance(ref, str):
            return out
        target_id, fragment, node = self._resolve(ref, identifier)
        key = (target_id, fragment)
        if key in active:
            self._cycles += 1
            target: Any = {"$recursive": f"{target_id}#{fragment}"}
        elif key in self._memo:
            target = self._memo[key]
        else:
            before = self._cycles
            target = self._walk(node, target_id, active | {key})
            if self._cycles == before:
                self._memo[key] = target
        if not out:
            return target
        if (isinstance(target, dict) and set(out) <= _INDEPENDENT_KEYWORDS
                and not set(out) & set(target)):
            return {**target, **out}
        return {"allOf": [target, out]}


class _Hasher:
    """Merkle hash over canonical JSON, so shared subtrees are hashed once."""

    def __init__(self) -> None:
        self._memo: dict[int, tuple[Any, str]] = {}

    def __call__(self, value: Any) -> str:
        if value is _MISSING:
            return "<missing>"
        if isinstance(value, (dict, list)):
            cached = self._memo.get(id(value))
            if cached is not None and cached[0] is value:
                return cached[1]
            if isinstance(value, dict):
                text = "{" + ",".join(
                    f"{json.dumps(key, ensure_ascii=False)}:{self(value[key])}" for key in sorted(value)
                ) + "}"
            else:
                text = "[" + ",".join(self(item) for item in value) + "]"
            digest = hashlib.sha256(text.encode()).hexdigest()
            self._memo[id(value)] = (value, digest)
            return digest
        return hashlib.sha256(json.dumps(value, ensure_ascii=False, default=str).encode()).hexdigest()


def _difference(before: Any, after: Any, hasher: _Hasher, limit: int = 25) -> list[tuple[str, Any, Any]]:
    """Pointer-level differences between two trees; equal subtrees are skipped by hash."""
    found: list[tuple[str, Any, Any]] = []

    def visit(old: Any, new: Any, where: tuple[str, ...]) -> None:
        if len(found) >= limit or hasher(old) == hasher(new):
            return
        if isinstance(old, dict) and isinstance(new, dict):
            for key in sorted(old.keys() | new.keys()):
                visit(old.get(key, _MISSING), new.get(key, _MISSING), (*where, key))
        elif isinstance(old, list) and isinstance(new, list) and len(old) == len(new):
            for index, (left, right) in enumerate(zip(old, new)):
                visit(left, right, (*where, str(index)))
        else:
            found.append((_json_pointer(where), old, new))

    visit(before, after, ())
    return found


def _replace(tree: Any, tokens: list[str], value: Any) -> Any:
    """Copy ``tree`` with the node at ``tokens`` replaced (or removed when ``value`` is missing)."""
    if not tokens:
        return value
    head, rest = tokens[0], tokens[1:]
    if isinstance(tree, dict):
        copy = dict(tree)
        current = tree.get(head, _MISSING)
        replaced = _replace(current, rest, value) if rest else value
        if replaced is _MISSING:
            copy.pop(head, None)
        else:
            copy[head] = replaced
        return copy
    if isinstance(tree, list) and head.isdigit() and int(head) < len(tree):
        copy_list = list(tree)
        copy_list[int(head)] = _replace(tree[int(head)], rest, value)
        return copy_list
    raise GateError(f"E_EQUIV_DELTA_POINTER:{_json_pointer(tokens)}")


def _is_part(tree: Any) -> bool:
    """A schema file that asserts nothing at its root (a definitions-only part)."""
    return tree == {}


@dataclass(frozen=True)
class SchemaFingerprints:
    """Dereferenced trees and fingerprints for one schema set."""

    trees: dict[str, Any]
    fingerprints: dict[str, str]
    hasher: _Hasher


def fingerprint_schemas(schemas: Mapping[str, Any]) -> SchemaFingerprints:
    dereferencer = _Dereferencer(schemas)
    hasher = _Hasher()
    trees = {name: dereferencer.root(name) for name in sorted(schemas)}
    return SchemaFingerprints(trees, {name: hasher(tree) for name, tree in trees.items()}, hasher)


@dataclass
class Delta:
    """One declared, deliberate change: a layer, a subject, before/after values, reason and test."""

    layer: str
    subject: str
    pointer: str
    before: Any
    after: Any
    reason: str
    test: str
    used: bool = False
    pr: int | None = None  # optional, for readers: the PR that adds the entry (the logic never reads it)
    merged: bool = False  # the base revision's file already holds this entry (L1, set by ``mark_merged``)
    landing: str | None = None  # the first-parent commit that brought it in
    age: int | None = None  # later first-parent commits that touch ``schemas/``, up to the base revision
    applied: bool = False  # ``compare_l1`` applied it to the base in this run


def parse_deltas(content: bytes, *, label: str, name: str = EXPECTED_DELTAS.name) -> list[Delta]:
    document = _decode(name, content)
    if not isinstance(document, dict) or document.get("version") != EXPECTED_DELTAS_VERSION:
        raise GateError(f"E_EQUIV_DELTAS_FORMAT:{label}")
    deltas: list[Delta] = []
    for entry in document.get("deltas") or ():
        if not isinstance(entry, dict) or not entry.get("reason") or not entry.get("test"):
            raise GateError(f"E_EQUIV_DELTAS_ENTRY:{entry!r}")
        layer = entry.get("layer", "L1")
        subject = entry.get({"L1": "schema", "L2": "document", "L3": "probe"}.get(layer, ""), "")
        pr = entry.get("pr")
        if layer not in ("L1", "L2", "L3") or not subject or (
                pr is not None and (not isinstance(pr, int) or isinstance(pr, bool) or pr < 1)):
            raise GateError(f"E_EQUIV_DELTAS_ENTRY:{entry!r}")
        deltas.append(Delta(layer, subject, entry.get("pointer", ""),
                            entry["before"] if "before" in entry else _MISSING,
                            entry["after"] if "after" in entry else _MISSING,
                            entry["reason"], entry["test"], pr=pr))
    return deltas


def load_deltas(path: Path) -> list[Delta]:
    if not path.is_file():
        return []
    return parse_deltas(path.read_bytes(), label=str(path), name=path.name)


# --------------------------------------------------------------------------------------------
# Entry lifecycle (#970): an L1 entry is meaningful only against the base that predates its PR
# --------------------------------------------------------------------------------------------

def delta_key(item: Delta) -> str:
    """Identity of an entry: layer, subject, pointer and both values (an absent value is its own marker)."""
    def plain(value: Any) -> Any:
        return {"absent": True} if value is _MISSING else value
    return json.dumps([item.layer, item.subject, item.pointer, plain(item.before), plain(item.after)],
                      sort_keys=True, default=str)


def _deltas_at(root: Path, commit: str, path: str) -> list[Delta]:
    try:
        content = _git(root, "show", f"{commit}:{path}")
    except GateError:  # the file does not exist in that commit
        return []
    return parse_deltas(content, label=f"{commit}:{path}")


def entry_landings(root: Path, base_rev: str, path: str = EXPECTED_DELTAS.as_posix()) -> dict[str, tuple[str, int]]:
    """For each entry the file holds at ``base_rev``: its landing commit and the later merges that touched ``schemas/``.

    The landing commit is the oldest commit of the unbroken run, in the first-parent history of the file, that holds
    the entry; its first parent is the base the entry was recorded for.
    """
    commits = _git(root, "log", "--first-parent", "--format=%H", base_rev, "--", path).decode().split()
    if not commits:
        return {}
    landing = {delta_key(item): commits[0] for item in _deltas_at(root, commits[0], path)}
    running = set(landing)
    for commit in commits[1:]:
        if not running:
            break
        present = {delta_key(item) for item in _deltas_at(root, commit, path)}
        for key in tuple(running):
            if key in present:
                landing[key] = commit
            else:
                running.discard(key)
    ages: dict[str, int] = {}
    result: dict[str, tuple[str, int]] = {}
    for key, commit in landing.items():
        if commit not in ages:
            ages[commit] = int(_git(root, "rev-list", "--count", "--first-parent", f"{commit}..{base_rev}",
                                    "--", "schemas").decode().strip())
        result[key] = (commit, ages[commit])
    return result


def mark_merged(root: Path, base_rev: str, deltas: list[Delta], path: str = EXPECTED_DELTAS.as_posix()) -> None:
    """Flag the L1 entries the base revision's file already holds, with their landing commit and age."""
    landings = entry_landings(root, base_rev, path)
    for item in deltas:
        found = landings.get(delta_key(item)) if item.layer == "L1" else None
        if found is not None:
            item.merged, (item.landing, item.age) = True, found


def stale_entries(deltas: Iterable[Delta]) -> list[Delta]:
    """Merged L1 entries that did not apply to the base: their PR landed and nothing needs them."""
    return [item for item in deltas if item.layer == "L1" and item.merged and not item.applied]


def stale_findings(deltas: Iterable[Delta]) -> tuple[list[str], list[str]]:
    """Failures (stale for more than ``STALE_MERGE_LIMIT`` later schema merges) and notes (still within the limit)."""
    failures: list[str] = []
    notes: list[str] = []
    for item in stale_entries(deltas):
        age = item.age or 0
        text = (f"stale expected-delta for {item.subject} {item.pointer or '<file>'}: landed in "
                f"{(item.landing or '')[:8]}, {age} later schema merge(s); retire it with --prune-stale")
        if age > STALE_MERGE_LIMIT:
            failures.append(f"L1 {text} (limit {STALE_MERGE_LIMIT})")
        else:
            notes.append(text)
    return failures, notes


def _applies(trees: Mapping[str, Any], item: Delta) -> bool:
    """Would the entry excuse a change made on top of these (dereferenced) schemas?"""
    if item.pointer == "" and item.after == "removed":
        return item.subject in trees
    if item.pointer == "" and item.after == "added":
        return item.subject not in trees
    return item.subject in trees and _same(_follow(trees[item.subject], _pointer_tokens(item.pointer)), item.before)


def _landed(trees: Mapping[str, Any], item: Delta) -> bool:
    """Do these (dereferenced) schemas already show the entry's result?"""
    if item.pointer == "" and item.after == "removed":
        return item.subject not in trees
    if item.pointer == "" and item.after == "added":
        return item.subject in trees
    return item.subject in trees and _same(_follow(trees[item.subject], _pointer_tokens(item.pointer)), item.after)


@dataclass
class PruneResult:
    removed: list[Delta] = field(default_factory=list)
    kept: list[tuple[Delta, str]] = field(default_factory=list)
    proofs: dict[str, str] = field(default_factory=dict)  # delta_key -> how the entry was proven stale


def prune_stale(root: Path, base_rev: str, *, deltas_path: Path | None = None) -> PruneResult:
    """Remove the stale L1 entries, each only after proving it against the base it was recorded for.

    The proof: ``before`` no longer holds at ``base_rev``, and either ``before`` holds at the landing commit's first
    parent and ``after`` holds at the landing commit, or ``after`` already held at that parent (a repair entry).
    An entry that fails the proof is kept and named with the reason.
    """
    path = deltas_path or root / EXPECTED_DELTAS
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    deltas = load_deltas(path)
    mark_merged(root, base_rev, deltas, relative)
    cache: dict[str, dict[str, Any]] = {}

    def trees(rev: str) -> dict[str, Any]:
        if rev not in cache:
            cache[rev] = fingerprint_schemas(load_schema_rev(root, rev)).trees
        return cache[rev]

    result = PruneResult()
    for item in deltas:
        if item.layer != "L1" or not item.merged:
            continue
        assert item.landing is not None
        if _applies(trees(base_rev), item):
            result.kept.append((item, f"its before value still holds at {base_rev}"))
            continue
        parent = _git(root, "rev-parse", f"{item.landing}^1").decode().strip()
        if _landed(trees(parent), item):
            result.removed.append(item)  # a repair: the result already held in the base it was recorded for
            result.proofs[delta_key(item)] = f"after already held at {parent[:8]}, the base it was recorded for"
        elif not _applies(trees(parent), item):
            result.kept.append((item, f"neither its before nor its after value holds at {parent[:8]}, the base it was recorded for; "
                               f"inspect {item.subject} {item.pointer or '<file>'} at {parent[:8]} and {item.landing[:8]}, "
                               "before merging, restate the recorded before/after values to match the actual schema change; "
                               "this entry is already merged, so manually retire it only after verifying the accepted historical "
                               "transition and subsequent schema changes. Rewriting a merged entry changes its landing identity "
                               "and cannot repair its --prune-stale proof"))
        elif not _landed(trees(item.landing), item):
            result.kept.append((item, f"its after value does not hold at the landing commit {item.landing[:8]}"))
        else:
            result.removed.append(item)
            result.proofs[delta_key(item)] = (f"before held at {parent[:8]}, after holds at {item.landing[:8]}, "
                                              f"before no longer holds at the base")
    if result.removed:
        dropped = {delta_key(item) for item in result.removed}
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        kept_lines = []
        for line in lines:
            if line.startswith("  - "):
                header = f"version: {EXPECTED_DELTAS_VERSION}\ndeltas:\n"
                entries = parse_deltas((header + line).encode(), label=relative)
                if len(entries) == 1 and delta_key(entries[0]) in dropped:
                    continue
            kept_lines.append(line)
        if len(lines) - len(kept_lines) != len(result.removed):
            raise GateError(f"E_EQUIV_PRUNE_LINES:{relative}: an entry spans lines or repeats; edit the file by hand")
        path.write_text("".join(kept_lines), encoding="utf-8")
    return result


@dataclass
class L1Row:
    schema: str
    status: str
    detail: str = ""


def compare_l1(base: SchemaFingerprints, head: SchemaFingerprints, deltas: list[Delta]) -> list[L1Row]:
    """Per-schema verdict: equal, additive, delta, added, removed, or changed (a failure)."""
    rows: list[L1Row] = []
    hasher = head.hasher
    for name in sorted(base.trees.keys() | head.trees.keys()):
        listed = [item for item in deltas if item.layer == "L1" and item.subject == name]
        if name not in head.trees:
            marker = [item for item in listed if item.pointer == "" and item.after == "removed"]
            for item in marker:
                item.used = True
            rows.append(L1Row(name, "removed" if marker or _is_part(base.trees[name]) else "changed",
                              "" if marker or _is_part(base.trees[name]) else "schema removed without a delta"))
            continue
        if name not in base.trees:
            marker = [item for item in listed if item.pointer == "" and item.after == "added"]
            for item in marker:
                item.used = True
            ok = bool(marker) or _is_part(head.trees[name])
            rows.append(L1Row(name, "added" if ok else "changed", "" if ok else "schema added without a delta"))
            continue
        before, after = base.trees[name], head.trees[name]
        if base.fingerprints[name] == head.fingerprints[name]:
            rows.append(L1Row(name, "equal"))
            continue
        patched = before
        applied: list[Delta] = []
        problems: list[str] = []
        for item in listed:
            tokens = _pointer_tokens(item.pointer)
            current = _follow(patched, tokens)
            if _same(current, item.before):
                patched = _replace(patched, tokens, item.after)
                applied.append(item)
            elif _same(current, item.after):
                item.used = True  # already landed in the base revision
            elif not item.merged:  # a merged entry that no longer applies is stale; run_gate reports it by age
                problems.append(f"delta {item.pointer} does not apply: base has {_short(current)}")
        for item in applied:
            item.used = item.applied = True
        if problems:
            rows.append(L1Row(name, "changed", "; ".join(problems)))
            continue
        if hasher(patched) == hasher(after):
            rows.append(L1Row(name, "delta", ", ".join(item.pointer for item in applied)))
            continue
        additive, ambiguity = _additive_only_change(patched, after)
        if additive:
            rows.append(L1Row(name, "additive"))
            continue
        differences = _difference(patched, after, hasher)
        rendered = "; ".join(f"{pointer or '/'} {_short(old)} -> {_short(new)}" for pointer, old, new in differences[:5])
        note = f" (not additive at {ambiguity})" if ambiguity else ""
        rows.append(L1Row(name, "changed", rendered + note))
    return rows


def _same(left: Any, right: Any) -> bool:
    if left is _MISSING or right is _MISSING:
        return left is right
    return json.dumps(left, sort_keys=True, default=str) == json.dumps(right, sort_keys=True, default=str)


def _short(value: Any) -> str:
    if value is _MISSING:
        return "<absent>"
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return text if len(text) <= 100 else text[:97] + "..."


# --------------------------------------------------------------------------------------------
# L2: corpus verdicts
# --------------------------------------------------------------------------------------------

def _schema_value(value: Any) -> Any:
    """JSON-compatible view of a YAML value (YAML resolves ISO dates to ``date`` objects)."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _schema_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_schema_value(item) for item in value]
    return value


@dataclass
class CorpusResult:
    records: list[dict[str, Any]]
    parsed: dict[str, Any]
    unmapped: Counter
    unparseable: list[str]
    total: int


class SchemaValidators:
    """Independent validators over one schema set, built once."""

    def __init__(self, schemas: Mapping[str, Any]) -> None:
        self.schemas = schemas
        self.registry = build_registry(schemas)
        self.version_map = derive_version_map(schemas)
        self._cache: dict[str, Draft202012Validator] = {}

    def validator(self, name: str) -> Draft202012Validator:
        if name not in self._cache:
            self._cache[name] = Draft202012Validator(self.schemas[name], registry=self.registry)
        return self._cache[name]

    def first_error(self, name: str, value: Any) -> dict[str, str] | None:
        errors = sorted(
            self.validator(name).iter_errors(_schema_value(value)),
            key=lambda item: (tuple(str(part) for part in item.absolute_path), str(item.validator),
                              "/".join(str(part) for part in item.absolute_schema_path)),
        )
        if not errors:
            return None
        return {"pointer": _json_pointer(errors[0].absolute_path) or "/", "rule": str(errors[0].validator)}


def run_l2(documents: Mapping[str, bytes], validators: SchemaValidators) -> CorpusResult:
    records: list[dict[str, Any]] = []
    parsed: dict[str, Any] = {}
    unmapped: Counter = Counter()
    unparseable: list[str] = []
    for path in sorted(documents):
        try:
            value = _decode(path, documents[path])
        except Exception:  # noqa: BLE001 - any decode failure means "not a mapped document"
            unparseable.append(path)
            continue
        version = value.get("version") if isinstance(value, dict) else None
        if not isinstance(version, str):
            unmapped["<no version>"] += 1
            continue
        schema = validators.version_map.get(version)
        if schema is None:
            unmapped[version] += 1
            continue
        parsed[path] = value
        error = validators.first_error(schema, value)
        records.append({"path": path, "schema": schema, "valid": error is None, "error": error})
    return CorpusResult(records, parsed, unmapped, unparseable, len(documents))


def _record_text(record: Any) -> str:
    if record is None:
        return "accepted"
    if "valid" in record:
        return "valid" if record["valid"] else f"invalid {record['error']['pointer']} {record['error']['rule']}"
    return f"{record.get('code')} {record.get('pointer')} {record.get('rule')} {record.get('message')}"


def load_expected_invalid(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    document = _decode(path.name, path.read_bytes())
    if not isinstance(document, dict) or document.get("version") != EXPECTED_INVALID_VERSION:
        raise GateError(f"E_EQUIV_EXPECTED_INVALID_FORMAT:{path}")
    listed: dict[str, dict[str, str]] = {}
    for entry in document.get("documents") or ():
        if not isinstance(entry, dict) or not all(isinstance(entry.get(key), str) and entry[key]
                                                   for key in ("path", "schema", "reason")):
            raise GateError(f"E_EQUIV_EXPECTED_INVALID_ENTRY:{entry!r}")
        listed[entry["path"]] = entry
    return listed


def load_baseline(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise GateError(f"E_EQUIV_BASELINE_MISSING:{path}")
    document = json.loads(path.read_bytes())
    if not isinstance(document, dict) or document.get("version") != BASELINE_VERSION:
        raise GateError(f"E_EQUIV_BASELINE_FORMAT:{path}")
    return document


def compare_records(layer: str, baseline: Mapping[str, Any], current: Mapping[str, Any],
                    deltas: list[Delta]) -> tuple[list[str], list[str]]:
    """Compare baseline and current records by key; a listed delta excuses exactly one change."""
    failures: list[str] = []
    notes: list[str] = []
    for key in sorted(baseline):
        if key not in current:
            notes.append(f"{layer} {key}: absent from the current run (moved, deleted or no longer mapped)")
            continue
        if _same(baseline[key], current[key]):
            continue
        excused = [item for item in deltas if item.layer == layer and item.subject == key
                   and _same(item.before, baseline[key]) and _same(item.after, current[key])]
        if excused:
            for item in excused:
                item.used = True
            continue
        failures.append(f"{layer} {key}: {_record_text(baseline[key])} -> {_record_text(current[key])}")
    return failures, notes


# --------------------------------------------------------------------------------------------
# L3: diagnostics through the production ingress functions
# --------------------------------------------------------------------------------------------


def _diagnostic(code: str, pointer: str = "", rule: str = "", message: str = "") -> dict[str, str]:
    return {"code": code, "pointer": pointer, "rule": rule, "message": message}


def _split_detail(detail: str) -> tuple[str, str]:
    """Split a ``"/pointer: message"`` detail; anything else is all message."""
    pointer, separator, message = detail.partition(": ")
    if separator and (pointer.startswith("/") or pointer == ""):
        return pointer, message
    return "", detail


def _ingress_project(document: Mapping[str, Any], _schema: str) -> dict[str, str] | None:
    from chrona.core.validation import validate_project

    diagnostics = validate_project(deepcopy(dict(document)))
    if not diagnostics:
        return None
    first = diagnostics[0]
    return _diagnostic(first.id, first.path or "", "", first.message)


def _ingress_contract(identity_kind: str) -> Callable[[Mapping[str, Any], str], dict[str, str] | None]:
    def ingress(document: Mapping[str, Any], _schema: str) -> dict[str, str] | None:
        from chrona.presentation.contracts import ClosureIdentity, ContractError, parse_contract

        identifier = document.get("id") if isinstance(document.get("id"), str) else "probe"
        identity = ClosureIdentity(identity_kind, identifier, "draft", "sha256:" + "0" * 64)
        try:
            parse_contract(identity, deepcopy(dict(document)))
        except ContractError as error:
            violation = getattr(error, "violation", None)
            code = error.diagnostic_id.split(":", 1)[0]
            message = violation.message if violation is not None else (error.detail or error.diagnostic_id)
            return _diagnostic(code, error.source_ref, violation.rule if violation is not None else "", message)
        except Exception as error:  # noqa: BLE001 - the gate records any failure of the ingress
            return _diagnostic(type(error).__name__, "", "", str(error)[:200])
        return None

    return ingress


def _ingress_operational(document: Mapping[str, Any], schema: str) -> dict[str, str] | None:
    from chrona.operational.resources import OperationalResourceError, parse_document

    try:
        parse_document(json.dumps(_schema_value(document), ensure_ascii=True), schema)
    except OperationalResourceError as error:
        pointer, message = _split_detail(error.detail)
        return _diagnostic(error.code, pointer, "", message)
    return None


def _ingress_authoring_command(document: Mapping[str, Any], _schema: str) -> dict[str, str] | None:
    from chrona.usecases.authoring_commands import parse_authoring_command

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "command.json"
        path.write_text(json.dumps(_schema_value(document), ensure_ascii=True), encoding="utf-8")
        try:
            parse_authoring_command(path)
        except ValueError as error:
            code, _, detail = str(error).partition(": ")
            pointer, message = _split_detail(detail)
            return _diagnostic(code, pointer, "", message)
    return None


def _ingress_scene(document: Mapping[str, Any], _schema: str) -> dict[str, str] | None:
    from chrona.presentation.scene.serialization import SceneSerializationError, validate_scene_document

    try:
        validate_scene_document(deepcopy(dict(document)))
    except SceneSerializationError as error:
        # SceneSerializationError now carries owner-local detail, but L3's
        # diagnostic contract records its stable leading code only.
        return _diagnostic(str(error).partition(":")[0], "", "", "")
    return None


def _ingress_direct(document: Mapping[str, Any], schema: str, validators: SchemaValidators) -> dict[str, str] | None:
    """Kinds whose production reader takes no caller-supplied document: schema plus the reducer."""
    from chrona.schema_diagnostics import explain_errors

    errors = tuple(validators.validator(schema).iter_errors(_schema_value(document)))
    if not errors:
        return None
    violation = explain_errors(errors, resource_kind=schema.removesuffix(".schema.yaml"))
    return _diagnostic("E_SCHEMA", violation.pointer, violation.rule, violation.message)


# Document-version segment (``chrona/<segment>/vN``, ``timeline/vN``) -> production ingress.
_CONTRACT_SEGMENTS = {
    "view": "view", "theme": "theme", "color-scheme": "color-scheme", "layout-profile": "layout-profile",
    "icon-catalog": "icon-catalog", "render-context": "render-context", "actual-set": "actual-set",
    "snapshot-ref": "snapshot-ref", "profile": "profile-package", "summary-profile": "summary-profile",
    "review-detail-profile": "review-detail-profile", "presentation-preset": "presentation-preset",
    "authoring-workspace": "authoring-workspace",
}
_OPERATIONAL_SEGMENTS = frozenset({
    "actual-intake-batch", "command", "automation-result", "authoring-command-result", "store-config",
})


def _segment(version: str) -> str:
    parts = version.split("/")
    return parts[1] if len(parts) == 3 and parts[0] == "chrona" else parts[0]


def run_ingress(document: Mapping[str, Any], validators: SchemaValidators) -> dict[str, str] | None:
    """Send one document through the production reader of its kind, or the direct fallback."""
    version = document.get("version")
    schema = validators.version_map.get(version) if isinstance(version, str) else None
    if schema is None:
        raise GateError(f"E_EQUIV_INGRESS_UNMAPPED:{version!r}")
    segment = _segment(version)
    if segment == "timeline":
        return _ingress_project(document, schema)
    if segment in _CONTRACT_SEGMENTS:
        return _ingress_contract(_CONTRACT_SEGMENTS[segment])(document, schema)
    if segment in _OPERATIONAL_SEGMENTS:
        return _ingress_operational(document, schema)
    if segment == "authoring-command":
        return _ingress_authoring_command(document, schema)
    if segment == "scene":
        return _ingress_scene(document, schema)
    return _ingress_direct(document, schema, validators)


# The probe matrix: strings the design names, per site family.  ``(label, value)`` pairs.
PROBE_STRINGS: dict[str, tuple[tuple[str, str], ...]] = {
    "date": (
        ("valid", "2026-09-30"), ("impossible-month", "2026-13-45"), ("impossible-day", "2026-02-30"),
        ("zero-date", "2026-00-00"), ("year-zero", "0000-01-01"), ("non-leap-february-29", "2026-02-29"),
        ("unicode-digits", "２０２６-09-30"), ("trailing-newline", "2026-09-30\n"),
    ),
    "sha256": (
        ("valid", "sha256:" + "a" * 64), ("trailing-newline", "sha256:" + "a" * 64 + "\n"),
        ("uppercase-hex", "sha256:" + "A" * 64), ("short", "sha256:" + "a" * 63), ("no-prefix", "a" * 64),
    ),
    "path": (
        ("valid", "a.yaml"), ("nested", "sub/a.yaml"), ("traversal", "../escape.yaml"), ("absolute", "/etc/passwd"),
        ("backslash", "a\\b.yaml"), ("nul", "a\x00b.yaml"), ("trailing-newline", "a.yaml\n"),
        ("embedded-newline", "a\nb.yaml"), ("dot", "."), ("dot-dot", ".."), ("double-slash", "a//b.yaml"),
        ("space", "my plan.yaml"), ("non-ascii", "計画.yaml"),
    ),
    "identifier": (
        ("valid", "ok-id"), ("empty", ""), ("space", "has space"), ("non-ascii", "計画"),
        ("nul", "x\x00y"), ("newline", "x\ny"),
    ),
    "endpoint": (
        ("start", "start"), ("finish", "finish"), ("end", "end"), ("at", "at"), ("body", "body"),
        ("unknown", "middle"),
    ),
    # A Store address site (#710 design D5): the strict `storeAddress` refuses every input but the first.
    "address": (
        ("valid", "layouts/briefing.yaml"), ("nul", "a\x00b"), ("backslash", "a\\b"), ("embedded-newline", "a\nb"),
        ("trailing-newline", "a\n"), ("dot-segment-leading", "./a"), ("dot-segment-inner", "a/./b"),
        ("empty-segment", "a//b"), ("trailing-slash", "a/"), ("drive-absolute", "C:/x"), ("drive-relative", "C:x"),
        ("unc", "\\\\server\\share\\x"), ("all-dot-segment", "a/..."), ("dot-dot", ".."), ("traversal", "../x"),
        ("inner-traversal", "a/../b"), ("absolute", "/x"), ("colon", "a:b"), ("space", "a b"), ("non-ascii", "\u00e9"),
        ("tab", "a\tb"),
    ),
    # The widening of moving a site from a letter-or-digit-first pattern to `storeAddress` (#731): accepted only after the move.
    "address-widened": (
        ("leading-dot", ".hidden/x"), ("leading-underscore", "_x"), ("leading-hyphen", "-x"),
    ),
    # One Store address segment used as a file name (`snapshotId`; the registry stores `snapshots/<id>.yaml`).
    "segment": (
        ("valid", "baseline-2027-06"), ("nul", "a\x00b"), ("backslash", "a\\b"), ("windows-traversal", "..\\..\\x"),
        ("embedded-newline", "a\nb"), ("trailing-newline", "a\n"), ("separator", "a/b"), ("dot", "."), ("dot-dot", ".."),
        ("all-dot", "..."), ("drive-relative", "C:x"), ("colon", "a:b"), ("space", "a b"), ("non-ascii", "\u00e9"),
        ("tab", "a\tb"),
    ),
}


@dataclass(frozen=True)
class ProbeSite:
    """One string site of one kind: a document, a JSON pointer, a probe family."""

    kind: str  # the schema inventory kind, for the coverage check
    source: str  # a tracked document path, or ``inline:<name>``
    pointer: str
    family: str
    repair: tuple[tuple[str, Any], ...] = ()  # (pointer, value) replacements that make a committed document valid


_C = "conformance/"
_REGISTRY_REPAIR = (("/payload/registry", {"provider": "local", "identity": "ci-baselines"}),)
_SCENE = "examples/controller-z/generated/plan-only.scene.json"
_OPERATIONAL = "docs/examples/operational-workflows/"

PROBE_SITES: tuple[ProbeSite, ...] = (
    ProbeSite("actual-intake-batch", _OPERATIONAL + "accepted-intake-batch.yaml", "/body/records/0/actual/finish", "date"),
    ProbeSite("actual-intake-batch", _OPERATIONAL + "accepted-intake-batch.yaml", "/body/source/contentIdentity", "sha256"),
    ProbeSite("actual-intake-batch", _OPERATIONAL + "accepted-intake-batch.yaml", "/id", "identifier"),
    ProbeSite("actual-set", _C + "presentation/actuals/controller-observed-duplicate-sequence.yaml",
              "/body/observations/0/actual/start", "date"),
    ProbeSite("actual-set", _C + "presentation/actuals/controller-observed-duplicate-sequence.yaml",
              "/body/observations/0/id", "identifier"),
    ProbeSite("automation-result", _OPERATIONAL + "accepted-baseline-result.yaml", "/requestContentIdentity", "sha256"),
    ProbeSite("automation-result", _OPERATIONAL + "accepted-baseline-result.yaml", "/inputs/0/address", "path"),
    ProbeSite("automation-result", _OPERATIONAL + "accepted-baseline-result.yaml", "/inputs/0/id", "identifier"),
    ProbeSite("color-scheme", "examples/aster-ssd/schemes/executive-light.yaml", "/id", "identifier"),
    ProbeSite("command-request", _OPERATIONAL + "accepted-capture-command.yaml", "/expectedContentIdentity", "sha256",
              repair=_REGISTRY_REPAIR),
    ProbeSite("command-request", _OPERATIONAL + "accepted-capture-command.yaml", "/target/address", "path",
              repair=_REGISTRY_REPAIR),
    ProbeSite("command-request", _OPERATIONAL + "accepted-capture-command.yaml", "/commandId", "identifier",
              repair=_REGISTRY_REPAIR),
    ProbeSite("icon-catalog", "tests/fixtures/icons/theme-assets-valid.normalized-v0.5.yaml",
              "/body/provenance/sourceContentIdentity", "sha256"),
    ProbeSite("icon-catalog", "tests/fixtures/icons/theme-assets-valid.normalized-v0.5.yaml", "/id", "identifier"),
    ProbeSite("layout-profile", _C + "layout-profile-intent-v0.2.yaml", "/root/id", "identifier"),
    ProbeSite("layout-profile", _C + "layout-profile-intent-v0.2.yaml", "/root/children/0/source", "path"),
    ProbeSite("presentation-preset", "examples/controller-z/elevated-light.preset.yaml", "/body/resources/view/path", "path"),
    ProbeSite("presentation-preset", "examples/controller-z/elevated-light.preset.yaml", "/id", "identifier"),
    ProbeSite("builtin-preset-library", "src/chrona/resources/presets/library.yaml",
              "/entries/6/members/iconCatalogs/0/contentIdentity", "sha256"),
    ProbeSite("builtin-preset-library", "src/chrona/resources/presets/library.yaml", "/entries/0/id", "identifier"),
    ProbeSite("profile-package", _C + "implementation-delivery-profile-invalid-field-v0.2.yaml", "/contentIdentity", "sha256"),
    ProbeSite("project", _C + "calendar.yaml", "/calendars/standard/exceptions/0/date", "date"),
    ProbeSite("project", _C + "calendar.yaml", "/objects/predecessor/schedule/start", "date"),
    ProbeSite("project", _C + "calendar.yaml", "/project/id", "identifier"),
    ProbeSite("project", _C + "calendar.yaml", "/relations/0/from/endpoint", "endpoint"),
    ProbeSite("render-context", "examples/aster-ssd/contexts/01-overview.yaml", "/body/project/address", "path"),
    ProbeSite("render-context", "examples/aster-ssd/contexts/01-overview.yaml",
              "/body/environment/fontMetrics/assets/0/metrics/contentIdentity", "sha256"),
    ProbeSite("render-context", "examples/aster-ssd/contexts/01-overview.yaml", "/id", "identifier"),
    ProbeSite("review-detail-profile", _C + "review-detail-profile-v0.1.yaml", "/id", "identifier"),
    ProbeSite("inspection-scene", _SCENE, "/surfaces/0/scale/domainStart", "date"),
    ProbeSite("inspection-scene", _SCENE, "/provenance/resources/0/contentIdentity", "sha256"),
    ProbeSite("inspection-scene", _SCENE, "/provenance/resources/0/id", "identifier"),
    ProbeSite("snapshot-ref", "examples/halcyon-1/snapshots/baseline-2027-06.yaml", "/body/project/address", "path"),
    ProbeSite("snapshot-ref", "examples/halcyon-1/snapshots/baseline-2027-06.yaml", "/id", "identifier"),
    ProbeSite("summary-profile", "examples/halcyon-1/profiles/scenario-summary.yaml", "/id", "identifier"),
    ProbeSite("theme", "src/chrona/resources/presets/bundles/technical-print/theme.yaml", "/id", "identifier"),
    ProbeSite("view", "examples/halcyon-1/views/02-programme-board.yaml", "/body/window/start", "date"),
    ProbeSite("view", "examples/halcyon-1/views/02-programme-board.yaml", "/body/annotations/0/anchor/endpoint", "endpoint"),
    ProbeSite("view", "examples/halcyon-1/views/02-programme-board.yaml", "/body/annotations/0/id", "identifier"),
    ProbeSite("example-registry", "src/chrona/resources/example-registry.yaml", "/examples/0/id", "identifier"),
    ProbeSite("example-registry", "src/chrona/resources/example-registry.yaml", "/examples/0/path", "path"),
    ProbeSite("theme-asset-source", "tests/fixtures/icons/theme-assets-valid.yaml", "/id", "identifier"),
    # Kinds with no committed document: inline base documents (see ``INLINE_DOCUMENTS``).
    ProbeSite("project", "inline:project-derived-point", "/objects/gate/schedule/constraints/at/min", "date"),
    ProbeSite("project", "inline:project-derived-point", "/objects/gate/schedule/constraints/at/max", "date"),
    ProbeSite("authoring-command", "inline:authoring-command-task", "/commandId", "identifier"),
    ProbeSite("authoring-command", "inline:authoring-command-task", "/target/path", "path"),
    ProbeSite("authoring-command", "inline:authoring-command-task", "/baseRevision", "sha256"),
    ProbeSite("authoring-command", "inline:authoring-command-task", "/payload/task/id", "identifier"),
    ProbeSite("authoring-command", "inline:authoring-command-task", "/payload/task/planned/start", "date"),
    ProbeSite("authoring-command", "inline:authoring-command-task", "/payload/task/planned/finish", "date"),
    ProbeSite("authoring-command", "inline:authoring-command-actual", "/payload/actual/actual/finish", "date"),
    ProbeSite("authoring-command", "inline:authoring-command-preset", "/payload/preset/path", "path"),
    ProbeSite("authoring-command", "inline:authoring-command-materialize", "/payload/directory", "path"),
    ProbeSite("authoring-command-result", "inline:authoring-command-result", "/commandBaseRevision", "sha256"),
    ProbeSite("authoring-command-result", "inline:authoring-command-result", "/commandId", "identifier"),
    ProbeSite("presentation-materialization-receipt", "inline:materialization-receipt",
              "/body/presetContentIdentity", "sha256"),
    ProbeSite("presentation-materialization-receipt", "inline:materialization-receipt", "/id", "identifier"),
    ProbeSite("store-config", "inline:store-config", "/stores/0/root", "path"),
    ProbeSite("store-config", "inline:store-config", "/stores/0/identity", "identifier"),
    ProbeSite("authoring-workspace", "inline:authoring-workspace", "/id", "identifier"),
    ProbeSite("authoring-workspace", "inline:authoring-workspace", "/body/project/tasks/0/planned/start", "date"),
    ProbeSite("authoring-workspace", "inline:authoring-workspace", "/body/presentation/binding/preset/path", "path"),
    ProbeSite("derived-theme", "inline:derived-theme", "/body/extends/path", "path"),
    ProbeSite("derived-theme", "inline:derived-theme", "/body/extends/contentIdentity", "sha256"),
    # Store address sites of the strict `storeAddress` (#710): the `address` family lists every rejected input.
    ProbeSite("render-context", "examples/aster-ssd/contexts/01-overview.yaml", "/body/project/address", "address"),
    ProbeSite("render-context", "examples/aster-ssd/contexts/01-overview.yaml", "/body/layout/address", "address"),
    ProbeSite("render-context", "examples/aster-ssd/contexts/01-overview.yaml",
              "/body/environment/fontMetrics/assets/0/metrics/locator/address", "address"),
    ProbeSite("layout-profile", _C + "layout-profile-override-v0.2.yaml", "/extends/address", "address"),
    ProbeSite("command-request", _OPERATIONAL + "accepted-capture-command.yaml", "/target/address", "address",
              repair=_REGISTRY_REPAIR),
    ProbeSite("command-request", _OPERATIONAL + "accepted-capture-command.yaml", "/payload/snapshotId", "segment",
              repair=_REGISTRY_REPAIR),
    ProbeSite("automation-result", _OPERATIONAL + "accepted-baseline-result.yaml", "/inputs/0/address", "address"),
    ProbeSite("snapshot-ref", "inline:snapshot-ref", "/body/project/address", "address"),
    # The two sites #731 moved in place (their consumers were made to refuse the same values first).
    ProbeSite("builtin-preset-library", "src/chrona/resources/presets/library.yaml",
              "/entries/6/members/iconCatalogs/0/sourcePath", "address"),
    ProbeSite("builtin-preset-library", "src/chrona/resources/presets/library.yaml",
              "/entries/6/members/iconCatalogs/0/noticeSourcePath", "address"),
    ProbeSite("builtin-preset-library", "src/chrona/resources/presets/library.yaml",
              "/entries/6/members/view/sourceRoot", "address"),
    ProbeSite("builtin-preset-library", "src/chrona/resources/presets/library.yaml",
              "/entries/6/members/iconCatalogs/0/sourcePath", "address-widened"),
    ProbeSite("icon-catalog", "inline:icon-catalog-raster", "/body/icons/ok/source/address", "address"),
    ProbeSite("icon-catalog", "inline:icon-catalog-raster", "/body/icons/ok/source/address", "address-widened"),
)

_REVISION = "sha256:" + "0123456789abcdef" * 4


def _inline_command(command_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"version": "chrona/authoring-command/v0.1", "commandId": "change-1", "type": command_type,
            "target": {"kind": "authoring-workspace", "path": "workspace.yaml"},
            "baseRevision": _REVISION, "payload": payload}


INLINE_DOCUMENTS: dict[str, Callable[[], dict[str, Any]]] = {
    "project-derived-point": lambda: {
        "version": "timeline/v0.7", "project": {"id": "derived-point"}, "objects": {
            "gate": {"type": "gate", "schedule": {"mode": "scheduled-point", "constraints": {"at": {
                "min": "2026-01-01", "max": "2026-12-31"}}}}}},
    "authoring-command-task": lambda: _inline_command("setWorkspaceTask", {"task": {
        "id": "one", "title": "One", "planned": {"start": "2026-01-01", "finish": "2026-01-02"}}}),
    "authoring-command-actual": lambda: _inline_command("setWorkspaceActual", {"actual": {
        "taskId": "one", "actual": {"start": "2026-01-01", "finish": "2026-01-02"}}}),
    "authoring-command-preset": lambda: _inline_command("selectPresentationPreset", {"preset": {
        "id": "starter", "version": "1", "path": "preset.yaml"}}),
    "authoring-command-materialize": lambda: _inline_command("materializePresentationPreset", {"directory": "presentation"}),
    "authoring-command-result": lambda: {
        "version": "chrona/authoring-command-result/v0.1", "status": "accepted", "commandId": "change-1",
        "commandBaseRevision": _REVISION, "workspaceRevision": _REVISION, "resultRevision": _REVISION,
        "diagnostics": []},
    "materialization-receipt": lambda: {
        "version": "chrona/presentation-materialization-receipt/v0.1", "kind": "presentation-materialization-receipt",
        "id": "receipt-1", "body": {
            "presetContentIdentity": _REVISION, "bindingContentIdentity": _REVISION,
            "normalizerVersion": "chrona/authoring-normalizer/v0.1", "resources": {"view.yaml": _REVISION}}},
    "store-config": lambda: {
        "version": "chrona/store-config/v0.1",
        "stores": [{"provider": "local", "identity": "local-store", "root": "store", "integrity": "required"}]},
    "authoring-workspace": lambda: {
        "version": "chrona/authoring-workspace/v0.1", "kind": "authoring-workspace", "id": "workspace",
        "body": {"project": {"id": "project", "tasks": [
            {"id": "one", "title": "One", "planned": {"start": "2026-01-01", "finish": "2026-01-02"}}]},
                 "presentation": {"mode": "guided", "binding": {"preset": {
                     "id": "starter", "version": "1", "path": "preset.yaml"}}}}},
    "snapshot-ref": lambda: {
        "version": "chrona/snapshot-ref/v0.3", "kind": "snapshot-ref", "id": "baseline", "body": {"project": {
            "id": "project", "kind": "project", "store": {"provider": "local", "identity": "store"},
            "address": "projects/main.yaml", "revision": {"token": "main"}}}},
    "icon-catalog-raster": lambda: {
        "version": "chrona/icon-catalog/v0.5", "kind": "icon-catalog", "id": "raster-assets", "body": {
            "set": "starter", "aliases": [],
            "provenance": {"sourceKind": "theme-asset-source", "sourceContentIdentity": _REVISION,
                           "license": {"spdx": "CC0-1.0", "notice": "CC0 notice"}},
            "icons": {"ok": {"kind": "raster", "source": {"address": "icons/ok.png", "contentIdentity": _REVISION},
                             "viewport": {"inlineSize": 24, "blockSize": 24}, "alternative": "ok"}},
            "entryAliases": {}, "glyphs": {}, "patterns": {}}},
    "derived-theme": lambda: {
        "version": "chrona/theme/v0.16", "kind": "theme", "id": "variation", "body": {
            "extends": {"id": "base", "path": "base.yaml", "sourceContentIdentity": _REVISION,
                        "contentIdentity": _REVISION},
            "values": {"text-size": {"type": "number", "value": 16}}}},
}

# Live kinds that are schema parts or otherwise reached only through a consuming kind's probes.
KIND_COVERED_THROUGH = {
    "presentation-resource-foundation": "view",
    "revision-store-resource-reference": "automation-result",
    "schema-part-common": "project",
    "schema-part-graphics": "icon-catalog",
    "schema-part-vocabulary": "render-context",
}


def _set_at(tree: Any, pointer: str, value: Any) -> None:
    tokens = _pointer_tokens(pointer)
    parent = _follow(tree, tokens[:-1])
    key = tokens[-1]
    if isinstance(parent, dict) and key in parent:
        parent[key] = value
    elif isinstance(parent, list) and key.isdigit() and int(key) < len(parent):
        parent[int(key)] = value
    else:
        raise GateError(f"E_EQUIV_PROBE_POINTER:{pointer}")


def probe_id(site: ProbeSite, label: str) -> str:
    return f"{site.kind}|{site.source}{site.pointer}|{site.family}:{label}"


def probe_documents(site: ProbeSite, corpus: Mapping[str, Any]) -> Any:
    """A fresh base document for a site: a tracked document (repaired) or an inline one."""
    if site.source.startswith("inline:"):
        return INLINE_DOCUMENTS[site.source.removeprefix("inline:")]()
    if site.source not in corpus:
        raise GateError(f"E_EQUIV_PROBE_SOURCE:{site.source}")
    document = deepcopy(corpus[site.source])
    for pointer, value in site.repair:
        _set_at(document, pointer, value)
    return document


def run_probes(corpus: Mapping[str, Any], validators: SchemaValidators,
               sites: Iterable[ProbeSite] = PROBE_SITES) -> dict[str, dict[str, str] | None]:
    """Run every probe string through the production ingress of its kind."""
    results: dict[str, dict[str, str] | None] = {}
    for site in sites:
        for label, value in PROBE_STRINGS[site.family]:
            document = probe_documents(site, corpus)
            _set_at(document, site.pointer, value)
            results[probe_id(site, label)] = run_ingress(document, validators)
    return results


def run_invalid_documents(corpus: Mapping[str, Any], paths: Iterable[str],
                          validators: SchemaValidators) -> dict[str, dict[str, str] | None]:
    """Production diagnostics for each document that is invalid at the baseline."""
    return {path: run_ingress(deepcopy(corpus[path]), validators) for path in sorted(paths) if path in corpus}


def _load_corpus(documents: Mapping[str, bytes], paths: Iterable[str]) -> dict[str, Any]:
    """Decode the named tracked documents (probe sources are not always L2-mapped)."""
    loaded: dict[str, Any] = {}
    for path in paths:
        if path in documents:
            loaded[path] = _decode(path, documents[path])
    return loaded


# --------------------------------------------------------------------------------------------
# Gate orchestration
# --------------------------------------------------------------------------------------------

@dataclass
class GateReport:
    """Everything one run learned: verdicts, notes, timings and the rendered text."""

    failures: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    timings: dict[str, float] = field(default_factory=dict)
    l1: list[L1Row] = field(default_factory=list)
    corpus: CorpusResult | None = None
    probes: dict[str, dict[str, str] | None] = field(default_factory=dict)
    invalid: dict[str, dict[str, str] | None] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not self.failures

    def render(self) -> str:
        out = list(self.lines)
        out.extend(f"NOTE {note}" for note in self.notes)
        out.extend(f"FAIL {failure}" for failure in self.failures)
        out.append("schema-equivalence: " + ("PASS" if self.passed else f"FAIL ({len(self.failures)} problems)"))
        return "\n".join(out)


def _coverage_failures(entries: Iterable[Mapping[str, Any]], records: Iterable[Mapping[str, Any]],
                       sites: Iterable[ProbeSite]) -> list[str]:
    """Every live schema kind needs at least one document mapped to it or one probe."""
    kind_of = {entry["file"]: entry.get("kind") for entry in entries}
    covered = {kind_of.get(record["schema"]) for record in records}
    covered |= {site.kind for site in sites}
    failures = []
    for entry in entries:
        kind = entry.get("kind")
        if entry.get("state") != "live":
            continue
        if kind in covered or KIND_COVERED_THROUGH.get(kind) in covered:
            continue
        failures.append(f"E_EQUIV_KIND_UNCOVERED:{kind}: no document maps to {entry['file']} and no probe names the kind")
    return sorted(set(failures))


def run_gate(root: Path, *, layers: Iterable[str] = ("L1", "L2", "L3"), base_rev: str | None = None,
             base_schemas: Mapping[str, Any] | None = None, schemas_dir: Path | None = None,
             inventory_path: Path | None = None, documents: Mapping[str, bytes] | None = None,
             baseline_path: Path | None = None, expected_invalid_path: Path | None = None,
             deltas_path: Path | None = None, sites: Iterable[ProbeSite] = PROBE_SITES,
             enforce_runtime_budget: bool = True) -> GateReport:
    """Run the requested layers against the baseline (L2, L3) and a base revision (L1).

    The CLI keeps the 60-second L2/L3 guard by default. Callers checking semantic
    results in tests may disable only that host-dependent guard; the validation
    work and all corpus/probe verdicts remain unchanged.
    """
    wanted = frozenset(layers)
    report = GateReport()
    schemas_dir = schemas_dir or root / "schemas"
    inventory_path = inventory_path or schemas_dir / "schema-inventory-v0.1.yaml"
    baseline_path = baseline_path or root / BASELINE
    expected_invalid_path = expected_invalid_path or root / EXPECTED_INVALID
    deltas_path = deltas_path or root / EXPECTED_DELTAS
    sites = tuple(sites)
    deltas = load_deltas(deltas_path)
    head = load_schema_dir(schemas_dir)
    entries: tuple[dict[str, Any], ...] = ()
    try:
        entries = validate_inventory(schemas_dir, inventory_path)
    except SchemaInventoryError as error:
        report.failures.append(f"inventory: {error}")

    if "L1" in wanted:
        started = time.monotonic()
        head_prints = fingerprint_schemas(head)
        if base_schemas is None and base_rev is not None:
            base_schemas = load_schema_rev(root, base_rev)
        if base_schemas is None:
            report.lines.append(f"L1 structural: {len(head_prints.fingerprints)} schema fingerprints computed; "
                                "no base revision given, nothing compared")
        else:
            if base_rev is not None:
                try:
                    mark_merged(root, base_rev, deltas, deltas_path.resolve().relative_to(root.resolve()).as_posix())
                except (GateError, ValueError) as error:
                    report.notes.append(f"expected-deltas: merged entries not checked ({error})")
            report.l1 = compare_l1(fingerprint_schemas(base_schemas), head_prints, deltas)
            tally = Counter(row.status for row in report.l1)
            report.lines.append("L1 structural (base " + (base_rev or "<supplied>") + "): "
                                + ", ".join(f"{name}={tally[name]}" for name in sorted(tally)))
            for row in report.l1:
                if row.status not in ("equal",):
                    report.lines.append(f"  {row.status:9} {row.schema} {row.detail}".rstrip())
                if row.status == "changed":
                    report.failures.append(f"L1 {row.schema}: {row.detail}")
        report.timings["L1"] = time.monotonic() - started

    if wanted & {"L2", "L3"}:
        baseline = load_baseline(baseline_path)
        expected_invalid = load_expected_invalid(expected_invalid_path)
        documents = documents if documents is not None else tracked_documents(root)
        validators = SchemaValidators(head)

    if "L2" in wanted:
        started = time.monotonic()
        result = run_l2(documents, validators)
        report.corpus = result
        current = {record["path"]: record for record in result.records}
        baseline_records = {record["path"]: record for record in baseline["documents"]}
        failures, notes = compare_records("L2", baseline_records, current, deltas)
        report.failures.extend(failures)
        report.notes.extend(notes)
        for path, record in sorted(current.items()):
            if path in baseline_records:
                continue
            if not record["valid"] and path not in expected_invalid:
                report.failures.append(f"L2 {path}: new document is invalid ({_record_text(record)}) and is not listed in expected-invalid")
        for path, entry in sorted(expected_invalid.items()):
            record = current.get(path)
            if record is None:
                report.notes.append(f"L2 {path}: expected-invalid document is absent or unmapped")
            elif record["valid"]:
                report.failures.append(f"L2 {path}: listed as expected-invalid but validates")
            elif record["schema"] != entry["schema"]:
                report.failures.append(f"L2 {path}: expected-invalid lists {entry['schema']} but it maps to {record['schema']}")
        invalid = [record for record in result.records if not record["valid"]]
        report.lines.append(
            f"L2 corpus: {len(documents)} tracked documents, {len(result.records)} mapped, {len(invalid)} invalid, "
            f"{sum(result.unmapped.values())} unmapped ({len(result.unmapped)} versions), "
            f"{len(result.unparseable)} unparseable; baseline {len(baseline_records)} documents")
        for record in invalid:
            report.lines.append(f"  invalid {record['path']} [{record['schema']}] {_record_text(record)}")
        report.timings["L2"] = time.monotonic() - started
        if entries:
            report.failures.extend(_coverage_failures(entries, result.records, sites))

    if "L3" in wanted:
        started = time.monotonic()
        paths = {site.source for site in sites if not site.source.startswith("inline:")} | set(expected_invalid)
        corpus = _load_corpus(documents, sorted(paths))
        report.probes = run_probes(corpus, validators, sites)
        report.invalid = run_invalid_documents(corpus, expected_invalid, validators)
        recorded = baseline.get("diagnostics", {})
        failures, notes = compare_records("L3", recorded.get("probes", {}), report.probes, deltas)
        report.failures.extend(failures)
        report.notes.extend(notes)
        failures, notes = compare_records("L3", recorded.get("invalidDocuments", {}), report.invalid, deltas)
        report.failures.extend(failures)
        report.notes.extend(notes)
        unrecorded = sorted(set(report.probes) - set(recorded.get("probes", {})))
        if unrecorded:
            report.notes.append(f"L3: {len(unrecorded)} probes are not in the baseline (recorded only in this output)")
        rejected = sum(1 for value in report.probes.values() if value is not None)
        report.lines.append(f"L3 diagnostics: {len(report.probes)} probes ({rejected} rejected, "
                            f"{len(report.probes) - rejected} accepted), {len(report.invalid)} invalid documents")
        for path, record in report.invalid.items():
            report.lines.append(f"  invalid {path}: {_record_text(record)}")
        report.timings["L3"] = time.monotonic() - started

    if "L1" in wanted:
        stale_failures, stale_notes = stale_findings(deltas)
        report.failures.extend(stale_failures)
        report.notes.extend(stale_notes)
    for item in deltas:
        if not item.used and not item.merged:
            report.notes.append(f"expected-deltas: unused {item.layer} entry for {item.subject} {item.pointer}".rstrip())
    total = report.timings.get("L2", 0.0) + report.timings.get("L3", 0.0)
    if wanted & {"L2", "L3"}:
        report.lines.append("runtime: " + ", ".join(f"{name}={report.timings[name]:.1f}s" for name in sorted(report.timings))
                            + f"; L2+L3={total:.1f}s (budget {RUNTIME_BUDGET_SECONDS:.0f}s)")
        if enforce_runtime_budget and total > RUNTIME_BUDGET_SECONDS:
            report.failures.append(f"runtime: L2+L3 took {total:.1f}s, over the {RUNTIME_BUDGET_SECONDS:.0f}s budget")
    return report


def record_baseline(root: Path, *, documents: Mapping[str, bytes] | None = None,
                    schemas_dir: Path | None = None, expected_invalid_path: Path | None = None,
                    sites: Iterable[ProbeSite] = PROBE_SITES) -> dict[str, Any]:
    """Compute the L2 verdicts and L3 diagnostics of the current tree as a baseline document."""
    schemas_dir = schemas_dir or root / "schemas"
    expected_invalid_path = expected_invalid_path or root / EXPECTED_INVALID
    documents = documents if documents is not None else tracked_documents(root)
    validators = SchemaValidators(load_schema_dir(schemas_dir))
    result = run_l2(documents, validators)
    invalid_paths = [record["path"] for record in result.records if not record["valid"]]
    sites = tuple(sites)
    paths = {site.source for site in sites if not site.source.startswith("inline:")} | set(invalid_paths)
    corpus = _load_corpus(documents, sorted(paths))
    try:  # the S0 base commit is the published main the slice branched from
        revision = _git(root, "rev-parse", "origin/main").decode().strip()
    except GateError:
        revision = _git(root, "rev-parse", "HEAD").decode().strip()
    return {
        "version": BASELINE_VERSION,
        "baseRevision": revision,
        "documents": result.records,
        "diagnostics": {
            "invalidDocuments": run_invalid_documents(corpus, invalid_paths, validators),
            "probes": run_probes(corpus, validators, sites),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--base-rev", help="git revision whose schemas L1 compares against")
    parser.add_argument("--layers", default="L1,L2,L3", help="comma-separated subset of L1,L2,L3")
    parser.add_argument("--record-baseline", action="store_true",
                        help="write the L2 verdicts and L3 diagnostics of this tree to the baseline file")
    parser.add_argument("--list-probes", action="store_true", help="print every probe verdict, not only the summary")
    parser.add_argument("--prune-stale", action="store_true",
                        help="remove the stale L1 expected-delta entries (merged and no longer applying), each proven "
                             "against the base it was recorded for; needs --base-rev")
    args = parser.parse_args(argv)
    if args.prune_stale and not args.base_rev:
        parser.error("--prune-stale needs --base-rev")
    root = args.root.resolve()
    try:
        if args.record_baseline:
            baseline = record_baseline(root)
            path = root / BASELINE
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(baseline, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
            print(f"recorded {len(baseline['documents'])} document verdicts, "
                  f"{len(baseline['diagnostics']['probes'])} probes to {path}")
            return 0
        if args.prune_stale:
            pruned = prune_stale(root, args.base_rev)
            for item in pruned.removed:
                print(f"pruned {item.subject} {item.pointer or '<file>'}: {pruned.proofs[delta_key(item)]}")
            for item, reason in pruned.kept:
                print(f"kept   {item.subject} {item.pointer or '<file>'}: {reason}")
            print(f"schema-equivalence: pruned {len(pruned.removed)} stale entries, kept {len(pruned.kept)} merged entries")
            return 0
        layers = tuple(item.strip() for item in args.layers.split(",") if item.strip())
        report = run_gate(root, layers=layers, base_rev=args.base_rev)
    except GateError as error:
        print(f"schema-equivalence: ERROR {error}", file=sys.stderr)
        return 2
    print(report.render())
    if args.list_probes:
        for name, record in sorted(report.probes.items()):
            print(f"  probe {name}: {_record_text(record)!r}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
