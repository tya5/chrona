# Work Record: a relocatable Store `root` (#781)

One living record for the baseline, design plan, design, architecture review and implementation plan of
[issue #781](https://github.com/tya5/chrona/issues/781) (found by the #142 design review). Base: `main` at `32a5fb4b`
(observed 2026-10-02). Owner-level decisions are also recorded on the issue.

## 1. Baseline

Published and read in code:

- `usecases/local_authoring.initialize_project(example=...)` writes `.chrona/store.yaml` with
  `root: str(store_root.resolve())`, an absolute host path, for the Store at `<dir>/.chrona/store`. The same function
  already knows the Store is `<dir>/.chrona/store`, a sibling of the config.
- `operational/store_config.ConfiguredStoreReader.__init__` is the single place a `root` becomes a `Path`
  (`Path(entry["root"])`); it receives the parsed dict, not the file location. Every consumer reads `reader.roots`:
  `app/cli.py` (`render-review --store-config`, the writable-Store commands through `_store_reader`) and
  `operational/command_engine.py` (two lookups). `load_store_config(path)` is the only file entry point; both CLI call sites
  reach it through `discover_store_configuration`, which already resolves the explicit path.
- A relative `root` today means "relative to the process working directory", so it is not usable as a committed value.
- Schema `schemas/store-config-v0.1.schema.yaml`: `root` is a non-empty string described as "Filesystem root of the local
  Store". The Store-config text is Spec 35 section 6; the guide path is `docs/guides/first-project.md` ("Render an example
  Context from its Store", #727). The CLI characterization suite does not run `init`; its only `store.yaml` mention is an
  error message that does not involve `root`.
- Tests that build `ConfiguredStoreReader({...})` from a dict use absolute `tmp_path` roots.

Unverified: Windows behaviour (PR CI is Ubuntu-only; see section 4, D5).

## 2. Literal acceptance

- [ ] A Store created by `init --example` keeps working after the directory is moved, by a test that moves it.
- [ ] An absolute `root` still works.
- [ ] The config written by `init` contains no host path.

## 3. Design plan

Use cases: (U1) copy, move or commit an `init --example` directory and keep rendering its Contexts; (U2) hand-write a
config with an absolute root (a Store elsewhere on disk); (U3) read a config from another working directory.
Open decisions: how a relative root is anchored; what `init` writes; what a missing base means for a dict-built reader;
schema and spec wording; Windows spelling. Review questions: does any reader bypass the one resolution point; is a relative
root a way to escape to arbitrary paths more than an absolute one already is (no: an absolute root is already accepted, and
`root` is a transport location with no authority over references, Spec 35 section 6).

## 4. Design

**D1. A relative `root` resolves against the directory that contains the config file.** An absolute `root` is used as
written. The resolved value is lexically normalized (`..` allowed, so `root: ../shared-store` works) and not required to
exist at load time (a read reports the missing file as it does today).

**D2. `init --example` writes `root: store`**, the path of the Store relative to `.chrona/`, computed from the two paths
`initialize_project` already holds and spelled with forward slashes (`as_posix`) so one file reads the same on every OS.
The config then contains no host path (the `identity` is `<example>-example`).

**D3. One resolution point.** `ConfiguredStoreReader(config, *, base=None)` anchors relative roots at `base`;
`load_store_config(path)` passes `Path(path).resolve().parent`, the same resolution `discover_store_configuration` applies,
so a symlinked config is anchored where its target lives. With `base=None` (a dict built in code) a relative root keeps its
current meaning, relative to the working directory. Because every consumer reads `reader.roots`, no other reader changes.

**D4. Compatibility.** Existing `init` directories hold an absolute root and keep working where they are; moving one needs
its `root` rewritten to `store`, the same one-line edit the guide states. No schema version change: the file shape is the
same, only the meaning of an already-valid relative string is defined (Spec 56 section 3.2: a behaviour-preserving change in
place). The schema `description` of `root` states the rule; `python -m tools.schema_equivalence --base-rev origin/main` is
run and recorded in the PR.

**D5. Windows.** The written value is `store`, not an OS path, so there is no separator or drive letter to differ. Resolution
is `base / root` after `Path.is_absolute()`, so `C:\x`, `C:/x` and `\\server\share` stay absolute on Windows and `/x` is
absolute on POSIX. A POSIX-style `/x` read on Windows is a rooted path on the current drive, as for any other path argument,
and is out of scope. Test inputs are taken from the real output of `initialize_project`, not hand-written strings; the
absolute-root test uses `str(tmp_path)`, which is native on each OS; the three-OS run on the review commit is the Windows
evidence.

**Whole-architecture review.** `operational` reads configuration and owns the transport location; `usecases` writes the
starter and knows the layout; `storage` receives a ready `Path` and is unchanged; Core, Presentation and schemas other than
one description string are untouched. No new dependency edge (`tools/check_import_direction.py` unaffected).
Alternatives rejected: resolving against the working directory (not relocatable, the status quo); resolving in each CLI
caller (two call sites and `command_engine`, easy to miss one); a `${CONFIG_DIR}` placeholder (a new mini-language for what a
relative path already says); omitting `root` and deriving it (a schema change and a hidden convention).

## 5. Implementation plan

Publication units: this record (docs PR), then one code PR, then the acceptance review.

| Step | Files | Evidence |
| --- | --- | --- |
| T1 failing tests first | `tests/unit/chrona/usecases/test_local_authoring.py`, `tests/unit/chrona/operational/` store-config test, `tests/integration/test_init_example_documented_path.py` | the written config has no absolute root; the directory moved with `shutil.move` still renders a Context through `--store-config`; a hand-written absolute root still works; a relative root resolves against the config directory, not the working directory; each fails on `main` |
| T2 resolution | `src/chrona/operational/store_config.py` | T1 green |
| T3 writer | `src/chrona/usecases/local_authoring.py` | T1 green, `root: store` read from the real output |
| T4 text | schema `description`, Spec 35 section 6, `docs/guides/first-project.md` | schema-equivalence result, doc-check |
| T5 mutation check | revert D1 (resolve against cwd), revert D2 (absolute writer), resolve against the wrong directory | each fails a named test |

Conformance and the CLI characterization suite stay unchanged; any golden change would be reviewed and stated.

Not changed: integrity handling (#723, #727), the example corpus, Store layout, the reader and registry classes.
