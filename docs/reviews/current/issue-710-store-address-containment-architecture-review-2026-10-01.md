# Architecture Review — Store address containment (#710)

Reviews the [design](../../design/issue-710-store-address-containment-design-2026-10-01.md) and [implementation plan](../../planning/active/issue-710-store-address-containment-implementation-plan-2026-10-01.md) against `main` `0ab5a6eb` (2026-10-01). This is a design and architecture review, not the acceptance review.

## Verdict

Approve the design for slice I710-2 (containment). The issue's framing ("defence in depth, not an open vulnerability") is wrong and should be corrected before the fix is described publicly: three exploitable paths exist today, one of them a write. The schema half (design part D) is sound but its row-1 list is incomplete and one kind cannot be fully retired; it needs the owner's acknowledgement before I710-3.

## Findings

| # | Finding | Severity | Evidence | Disposition |
| --- | --- | --- | --- | --- |
| F1 | A symlink inside a snapshot directory is followed out of the Store root by `LocalSnapshotReader` (and by every adapter that does not resolve). | High on every OS that can create symlinks; needs a hostile or careless Store (a checked-out archive can carry symlinks) | measured: address `link/secret.yaml` returned a file outside the root | fixed by the containment assertion (C3), test with `os.symlink` |
| F2 | Windows: a drive-absolute address replaces the base in `Path` join (R1, R5, R6-package). | High on Windows | `PureWindowsPath('C:/store/rev') / 'C:/Users/x/secret.yaml'` is `C:\Users\x\secret.yaml`; no Windows host was used | fixed by the anchor/drive/`:` rules (C2), tested with `PureWindowsPath` on every OS |
| F3 | Windows: `LocalBaselineRegistry.publish` builds `root/snapshots/<snapshotId>.yaml` checking only `/`, `.` and `..`; a backslash id traverses, and the call **writes** (create-only, `.yaml` suffix). `read` has the same hole (split on `/` only). | **Highest** (write, command field constrained only by `minLength: 1`) | `PureWindowsPath('C:/store/rev') / 'snapshots' / '..\..\x.yaml'` keeps two `..` parts | fixed by applying the helper to `snapshot_id` and to the read address; the schema constraint follows in I710-3 |
| F4 | `contentIdentity` is optional on this path by default, so it cannot be relied on as a limiter. | design input | `revision_store.py:189` default `False`; `store_config.py:34` builds the reader without the flag; `chrona init --example` writes `integrity: optional`. The baseline reader always requires the `baseline:<sha256>` token | recorded in the threat model; containment does not depend on it |
| F5 | `render-context` `#/$defs/reference.address` (every pinned input) is `minLength: 1` with no guard at all; the issue's "render-context resource address" names only the font locator. `command-request` `snapshotId` is also unconstrained. | medium (schema), covered at runtime by the code guard | schema lines quoted in the design | added to the design's site table |
| F6 | The hand-written checks disagree: five variants, two `PurePosixPath`-based (blind to `C:`), and only four of the readers assert containment. | design debt | design part A | replaced by one function |
| F7 | `./a`, `a//b` are accepted by R1 today; `a\x00b` and `a\nb` end in the typed "no file" error only because `Path.is_file()` swallows the error. | low | measured | rejected explicitly |
| F8 | Identifier-as-file-name: `actual_set_id` and `target["id"]` are interpolated into paths (R10). | low-medium | `actual_commands.py:91,118,130`, `command_engine.py:73` | guarded with the same function (one-segment address); not a Store address, listed so it is not lost |
| F9 | The owner's `storeAddress` character set allows a segment of three or more dots (`...`) and trailing-dot segments. | schema | pattern probe | the design forbids all-dot segments in both the guard and the schema; trailing-dot is recorded as a residual (Win32 strips it, which aliases `a.` to `a`, not an escape) |
| F10 | `snapshot-ref` v0.2 instances are immutable and already in Stores; the bump cannot retire the predecessor. | compatibility | `snapshots.py:61` writes v0.2 | design D6 item 2 |

## Threat model check

Who supplies an address: documents and commands that arrive from outside the operator's own authoring (design B). What `contentIdentity` limits: when present, it reduces "read any file" to "read a file with a known hash" plus an existence oracle; it is **optional by default**, so the design treats it as an independent second control, never as the containment. Whether it is ever optional on this path: yes (F4). The design's residuals are a concurrent mutation of the Store by an actor who already controls it (TOCTOU) and the Windows trailing-dot alias; both are stated, neither is an escape.

## Layer boundaries

Where the helper lives decides whether "one function at every adapter" is achievable under `tools/check_import_direction.py`:

| Consumer | Package | May import (ALLOWED) | `core` | `storage` |
| --- | --- | --- | --- | --- |
| R1, R2, R3 | `storage` | core, scheduling, resources | yes | (itself) |
| R4, R5 | `usecases` | core, extensions, presentation, scheduling, storage, resources, schema_diagnostics | yes | yes |
| R6, R7, R8 | `presentation` | core, resources, schema_diagnostics | yes | **no** |
| R10 | `commands`, `operational` | core, ... | yes | yes |

A helper in `storage` would need a new `presentation -> storage` edge, which the table exists to prevent and which would also create a dependency from the rendering model onto an adapter package. `core` is importable by all of them, already owns the reader port (`core/ports.py`: `SnapshotReader`, `SnapshotReadError`), and the helper is a pure function over `pathlib` with no adapter state. `core/store_address.py` is therefore the one location; no allowed edge changes. The alternative of one helper per package was rejected because it reproduces finding F6.

Responsibility split: the helper decides *syntax and containment* and raises a neutral `StoreAddressError`; each adapter decides *which typed diagnostic* it reports (its existing one). The helper knows no Store, no revision token and no diagnostic vocabulary, so the dependency stays inward.

## Windows-only behaviour on every OS

The reviewer asked for a Windows-leg regression test. The design does not depend on the leg: rejection is decided by `PurePosixPath` **and** `PureWindowsPath` together, both of which exist on every platform, so the decision is identical on Ubuntu, macOS and Windows and the row-3 vectors are plain unit tests. The join arithmetic that causes the escape is asserted with `PureWindowsPath`, not with the host `Path`. The one host-dependent vector, the symlink, skips only when `os.symlink` is refused (Windows without the privilege) and says so. PR CI runs Ubuntu only; the three-OS run happens on `main`, which is why no test may depend on the host.

## Compatibility

No committed or packaged address is rejected (design part E: 466 structured values in 56 files and 39 Python literals; two negative fixtures, both already expected to fail). The typed diagnostics are unchanged, so callers that map them (`closure.py:1054`, `profiles.py:26`, `references.py:32`) behave the same. New rejections are limited to forms the survey shows nobody uses: `./`, empty segments, `:`, backslash, control characters and drive anchors.

## Risks to watch during I710-2

- **`resolve()` cost and symlinked Store roots.** Both root and target are resolved, so a Store reached through a symlinked parent (for example `/tmp` on macOS) still works; the tests use `tmp_path` and cover it.
- **A Store that legitimately symlinks inside itself** stays allowed (containment is against the Store root, not the revision directory). Tightening to the revision directory would be stricter and is a possible follow-up.
- **`materialize` keeps an existing `is_symlink()` refusal for icon sources** (`materialize.py:241`); the helper does not replace it.
- **Message text** of rejected addresses is not part of any contract, but `detail` strings that echo the address already exist (`revision_store.py:213`); echoing a control character into a diagnostic is avoided by using `repr` in the new detail.

## Open questions for the owner (none blocks I710-2)

1. Accept the wider row-1 site list (F5) and the all-dots rule (F9).
2. Accept that `snapshot-ref` v0.2 stays readable indefinitely (F10).
3. Project `extensions[].resource` (schema-free object): constrain it at Project's next bump, or leave it to the reader guard.
