# Implementation Plan — Store address containment and strict `storeAddress` (#710)

Baseline: [issue #710](https://github.com/tya5/chrona/issues/710) on `main` `0ab5a6eb` (2026-10-01), owner decision "tighten" (2026-10-01).
Design: [design](../../design/issue-710-store-address-containment-design-2026-10-01.md). Review: [architecture review](../../reviews/current/issue-710-store-address-containment-architecture-review-2026-10-01.md).
This record holds the baseline, the literal acceptance and the slice order; the behaviour lives in the design.

## Published, inferred, unverified

Published (read on `main`): the issue body, the reviewer finding and the owner decision comment; `storage/revision_store.py`, `storage/snapshots.py`, `storage/snapshot_paths.py`,
`usecases/materialize.py`, `presentation/model/{font_resources,closure,theme_inheritance}.py`, `operational/{command_engine,references,store_config}.py`, `commands/actual_commands.py`, `app/cli.py`
reader construction sites, the schemas named in the design, Spec 56 §3.2 and the #662 design (D1, D3/N5).

Measured with throwaway scripts (not committed): the reader table, the symlink read outside the Store root, `PureWindowsPath` join behaviour, the committed-address survey, the `storeAddress` pattern probes, the per-kind file counts.

Inferred: that an unpatched Windows host shows the drive-escape and backslash-traversal read/write that the `PureWindowsPath` arithmetic predicts (no Windows host was used).

Unverified: whether a Windows path segment of three or more dots can alias a parent directory (the design rejects it conservatively).

## Literal acceptance (issue rows, verbatim from the owner decision)

| # | Row | Slice | Status |
| --- | --- | --- | --- |
| 1 | `common` defines a strict `storeAddress`: segments of `[A-Za-z0-9._-]` separated by `/`; no `.`/`..` segment, leading `/`, `:`, backslash, NUL or control characters; fully anchored, so no trailing newline gets through. Every live address site (`layout-profile`, `revision-store-resource-ref` and its users, the `render-context` resource address) references it. The affected kinds take the version bump that Spec 56 requires, and the equivalence gate lists the rejected inputs. | I710-3 (S-A..S-D) | designed here; not implemented |
| 2 | **Containment at every file-opening adapter.** This covers `storage/revision_store.py`, `storage/snapshots.py` and every other reader that joins a Store address. Each one rejects any address whose `PurePath` has a drive or anchor on **any** OS, and asserts that the resolved path lies inside the resolved Store root; otherwise it raises the existing typed reference error, never an OS exception. | I710-2 | pending |
| 3 | Regression tests run on all three OS legs: `C:/x`, `C:x`, `\\server\share\x`, `a\x00b`, `a\nb`, `a\\b`, `./a`, `a/../b` and a symlink pointing outside the root. Each yields the typed diagnostic. | I710-2 | pending |
| 4 | The committed-address survey is recorded: every committed or packaged address matches `storeAddress`, or the exceptions are named and migrated. | I710-1 (design part E) | recorded: 0 exceptions among accepted addresses; 2 negative fixtures |

## Slices

### I710-1 — survey, design, plan, review (documents only)

Files: the three documents of this pack. No code, no schema, no derived output. Gate: conformance.

### I710-2 — the containment helper and its adapters (security fix)

- New `src/chrona/core/store_address.py`: `StoreAddressError`, `check_store_address`, `resolve_store_address` (design C1-C3). Standard library only; no import-direction edge added.
- Adapters converted to the helper, each keeping its existing typed error (design C4): R1 `storage/revision_store.py` (`LocalSnapshotReader.read`), R2 and R3 `storage/snapshots.py` (`LocalBaselineRegistry.read`, `publish`), R4 `usecases/materialize.py` (`_inside`), R5 `_package_resource`, R6 `presentation/model/font_resources.py`, R7 `closure._safe_icon_address` and its Draft branch, R8 `theme_inheritance._safe_relative` and its Draft branch, R10 the identifier-as-file-name joins in `commands/actual_commands.py` and `operational/command_engine.py`.
- Left unchanged on purpose: R9 (workspace-local Draft paths, not Store addresses), R11 (packaged catalogue), R12 (`snapshot_directory`, safe by construction).
- Tests: a new `tests/unit/chrona/core/test_store_address.py` (the row-3 vectors against the pure function, both path flavours, plus accepted vectors for every shape the survey found), and one adapter-level test per converted adapter using a `tmp_path` Store asserting the typed diagnostic; the symlink vector uses `os.symlink` and skips only where the OS refuses it. No test's verdict depends on the host OS.
- Mutation checks, recorded in the PR body: for each guard (drive/anchor, `:`, backslash, NUL, control, dot and empty segments, containment) break it on a worktree copy, see the named test fail, restore.
- Gate: focused tests, `tests/unit`, `tests/unit/tools`, `python conformance/run_conformance.py`, `tools/check_import_direction.py`; PR CI runs the rest.
- Stop conditions (report, do not merge): a legitimate committed address would be rejected; a reader cannot be guarded without changing behaviour for legitimate addresses.

### I710-3 — the schema half (later; needs the owner's review of design part D)

S-A add `storeAddress` to `common-v0.1` and publish `revision-store-resource-ref-v0.2`; S-B `layout-profile` v0.10 and `render-context` v0.17 with the committed corpus re-pointed; S-C `command-request` v0.3, `automation-result` v0.2, `snapshot-ref` v0.3 with dual read; S-D retire the transitioning predecessors except `snapshot-ref` v0.2 (design D4, D6). Each slice states its L1/L3 deltas and the rejected-input probes in the equivalence gate (design D5). Not started by this pack.

### I710-4 — acceptance review

Written by the lead after I710-2 and I710-3: one row per literal acceptance criterion with the exact commit and the three-OS run on the exact main commit.

## Publication boundary

I710-1 and I710-2 are separate pull requests, merged in that order. Each cites `Refs #710` only; none closes the issue. Derived documents are not edited.
