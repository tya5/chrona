# Design — Store address containment and the strict `storeAddress` (#710)

**Plan:** [implementation plan](../planning/active/issue-710-store-address-containment-implementation-plan-2026-10-01.md);
**review:** [architecture review](../reviews/current/issue-710-store-address-containment-architecture-review-2026-10-01.md).
Evolution rule: [Spec 56 §3.2](../specification/56-schema-authoring-and-diagnostics.md). Adjacent design: [#662 design](issue-662-schema-parts-design-2026-09-30.md) (D1 part lifecycle, D3 row N5).

Baseline: `main` at `0ab5a6eb` (2026-10-01). Every claim marked *measured* was run against that commit with a throwaway script; none of the scripts is committed.

## Decision being implemented

The owner decided to **tighten** on 2026-10-01. The four acceptance rows, quoted:

> 1. `common` defines a strict `storeAddress`: segments of `[A-Za-z0-9._-]` separated by `/`; no `.`/`..` segment, leading `/`, `:`, backslash, NUL or control characters; fully anchored, so no trailing newline gets through. Every live address site (`layout-profile`, `revision-store-resource-ref` and its users, the `render-context` resource address) references it. The affected kinds take the version bump that Spec 56 requires, and the equivalence gate lists the rejected inputs.
> 2. **Containment at every file-opening adapter.** This covers `storage/revision_store.py`, `storage/snapshots.py` and every other reader that joins a Store address. Each one rejects any address whose `PurePath` has a drive or anchor on **any** OS, and asserts that the resolved path lies inside the resolved Store root; otherwise it raises the existing typed reference error, never an OS exception.
> 3. Regression tests run on all three OS legs: `C:/x`, `C:x`, `\\server\share\x`, `a\x00b`, `a\nb`, `a\\b`, `./a`, `a/../b` and a symlink pointing outside the root. Each yields the typed diagnostic.
> 4. The committed-address survey is recorded: every committed or packaged address matches `storeAddress`, or the exceptions are named and migrated.

This document covers rows 2, 3 and 4 as an implementable design (slice I710-2) and row 1 as a plan for a later, separately published slice (part D below). Row 1 is **not** implemented by the code slice.

## A. Baseline: every reader that joins a Store address

A "Store address" is the `address` of a pinned resource reference (`{id, kind, store, address, revision, contentIdentity?}`) and of a font or icon asset locator. It arrives in a document (Context, Project `extensions[].resource`, layout-profile `extends`, icon catalog, snapshot-ref body) or in a command (`target`, `payload.*`, `payload.snapshotId`). Line numbers are at `0ab5a6eb`.

| # | Reader (file:line) | What it checks today | Reachable with a caller-supplied address? |
| --- | --- | --- | --- |
| R1 | `storage/revision_store.py:194-221` `LocalSnapshotReader.read`; join at 209 | token and address non-empty; no leading `/`; no backslash; no `..` segment (200-207). No drive/`:`/NUL/control check, no `.` or empty segment check, no containment, no `OSError` mapping | yes: `app/cli.py:214,387,596,706`, `operational/store_config.py:34` (`ConfiguredStoreReader`, default `integrity: optional`), every closure read (`presentation/model/closure.py:1047-1056,978`), `extensions/profiles.py:26`, `operational/references.py:32` |
| R2 | `storage/snapshots.py:72-85` `LocalBaselineRegistry.read`; join at 77 | store equals; `startswith("snapshots/")`; no `..` segment (75). A backslash is **not** checked | yes: `operational/store_config.py:32` for any `snapshot-ref` whose token starts `baseline:` |
| R3 | `storage/snapshots.py:59-68` `LocalBaselineRegistry.publish` (**write**); target built at 65 | `snapshot_id` non-empty, no `/`, not `.` or `..` (60). Backslash, `:`, NUL, control not checked | yes: `payload.snapshotId` of a `captureSnapshot` command (`operational/command_engine.py:65`); the schema constrains it to `minLength: 1` only (`command-request-v0.2.schema.yaml:61`) |
| R4 | `usecases/materialize.py:48-52` `_inside`, used at 173, 186, 240, 249, 326, 332 (351, 357, 378 take manifest paths) | resolves and requires the path under the resolved root; no syntax check, so NUL raises `ValueError` from `resolve()` | yes: the addresses of an authored example Context and its catalogs (`materialize`, `chrona init --example`) |
| R5 | `usecases/materialize.py:149-157` `_package_resource`; `files("chrona.resources").joinpath(address)` at 154 | `PurePosixPath` only: non-empty, not absolute, `address == as_posix()`, no empty/`.`/`..` part. `C:/x` passes | yes (`package` provider references, 167; icon assets, 238). On Windows `files()` is a real `WindowsPath` and `joinpath("C:/x")` replaces the base. Identity is compared afterwards |
| R6 | `presentation/model/font_resources.py:18-51` `resolve_font_resource` | `PurePosixPath` check (27-33); `context` provider resolves and requires containment (39-42); `package` provider does `root.joinpath(*parts)` at 48 with no containment | yes: a font locator of a Render Context (`font_metrics.py:311`, `materialize.py:316`) |
| R7 | `presentation/model/closure.py:861-864` `_safe_icon_address`, used at 970 (Store path, then R1) and 1014 (Draft path: `(root / address).resolve()` with `root in parents`, 1016-1018) | `PurePosixPath` syntax; Draft branch resolves and contains | yes (icon catalog `source.address`) |
| R8 | `presentation/model/theme_inheritance.py:28-35` `_safe_relative`; child address built at 54-64; Draft branch joins at 133-135 | `PurePosixPath` syntax; Draft branch resolves and contains; the Store branch only builds the address and hands it to the reader (R1) | yes (`extends.path` of a derived Theme) |
| R9 | `presentation/model/closure.py:375-380` `_declared_child`; `usecases/authoring_materialization.py:90-99` `_relative/_child`; `operational/authoring_commands.py:104-106` `_relative` | host-OS `Path` syntax; resolve and contain | not Store addresses: workspace-local paths of the Draft/authoring flow. Listed because they share the shape; left out of this slice |
| R10 | `commands/actual_commands.py:91,118,130` `LocalActualStore`; `operational/command_engine.py:73` | `actual_set_id` / `target["id"]` interpolated into `root/"actual-tips"/f"{id}.json"` and `.../"actuals"/f"{id}.yaml"`; no check | yes: the `id` comes from the actual-set document or the command target. An identifier used as a file name, not a Store address; included because the escape is the same. The command path needs the tip file to exist (`is_file`), so the reachable effect is a read of a file that looks like a tip |
| R11 | `usecases/preset_library.py:14-21,62,121` `_safe` | `PurePosixPath` syntax on addresses read from the **packaged** `library.yaml` | no: the catalogue is shipped, not supplied |
| R12 | `storage/snapshot_paths.py:8-18` `snapshot_directory` | none needed: the token is percent-encoded with `safe="-_"` and `.` is forced to `%2E`, so `/`, `\`, `:`, NUL and `..` cannot survive | safe by construction (kept as is) |

Not Store-address readers: `app/cli.py` file arguments, `presentation/fonts/importer.py`, `presentation/icons/importer.py`, `usecases/local_authoring.py` (operator paths, not document content).

What *is* guarded across all of R1-R8: nothing in common. There are five different hand-written checks (two of them `PurePosixPath`-based, which cannot see a Windows drive), and only R4, R6 (context branch), R7 (Draft branch) and R8 (Draft branch) assert containment.

### What is measurably wrong today

- **Symlink escape, POSIX, any OS (measured).** `LocalSnapshotReader` joins the address and reads it. A symlink inside a snapshot directory pointing to a directory outside the Store root is followed: address `link/secret.yaml` returned the bytes of a file outside the root. No `contentIdentity` is needed when it is absent from the reference.
- **`contentIdentity` is optional on this path (measured, read in code).** `LocalSnapshotReader(require_content_identity=False)` is the default (`revision_store.py:189`); `ConfiguredStoreReader` builds it without the flag (`store_config.py:34`) and `chrona init --example` writes `integrity: optional` (`usecases/local_authoring.py:51`). `require_content_identity` is opt-in on the CLI. So the reviewer's "whether `contentIdentity` is ever optional on this path": yes, by default. The baseline reader (R2) is different: it always requires `revision.token == baseline:<sha256 of the bytes>`, so a baseline read is always pinned.
- **Windows drive escape (demonstrated with `PureWindowsPath`).** `PureWindowsPath('C:/store/rev') / 'C:/Users/x/secret.yaml'` is `C:\Users\x\secret.yaml`. R1 (and R5, R6-package) accept such an address. On a real Windows leg this reads the file; without `contentIdentity` (above) it reads any YAML/JSON-shaped file the process can open.
- **Windows backslash traversal in R2 and R3 (demonstrated).** `PureWindowsPath('C:/store/rev') / 'snapshots' / '..\..\x.yaml'` keeps two `..` parts. R2 splits on `/` only, so `snapshots/..\..\x.yaml` passes the `..` check. R3 writes (`publish_exclusive`, create-only, forced `.yaml` suffix) at the joined path, so a `captureSnapshot` command with `snapshotId: "..\..\x"` creates a file outside the registry on Windows. This is the most serious finding: it is a **write** and its input is a command field with no schema constraint beyond `minLength: 1`.
- **Accepted but unintended forms (measured):** `./a`, `a//b` and `link//x` pass R1 (only `..` is checked). `a\x00b` and `a\nb` end at `E_STORE_REFERENCE` only because `Path.is_file()` swallows the error; that is luck, not a guard.

## B. The threat model

- **Who supplies an address.** Anything that parses as a document or command: a Context, a Project's `extensions[].resource` (schema-free `type: object`, `project-v0.7.schema.yaml:72`), a layout-profile `extends`, a snapshot-ref body, a command `target`/`payload`, an icon catalog. These arrive from repositories and files an operator did not author. The Store directory itself may also be hostile (a checked-out archive can contain symlinks).
- **Capabilities.** Read: any file the process can open, as bytes handed to a YAML/JSON parser. Existence probing: the typed "no file" versus "identity mismatch" difference. Write: R3 only (create-only, `.yaml`). Nothing executes.
- **What `contentIdentity` limits.** When present it forces the attacker to know the target's sha256, which turns "read any file" into "read a file whose hash is known" plus an existence oracle. It is optional by default (above), so it is **not** a containment control; containment is. The baseline reader's token pin is a real limiter for R2 reads, not for R3 writes.
- **Who is not in the model.** The operator who passes `--snapshot-root` and config files is trusted. Environment, cwd and the Python process are trusted.
- **Residual after the fix.** A TOCTOU between resolving and opening (the Store directory mutated concurrently by another process with write access to the Store). That actor already controls Store content; out of scope, stated.

## C. The containment helper

### C1. One function, one location

`src/chrona/core/store_address.py` (new). Rationale in the review (layer table). It imports only the standard library. `chrona.core` is importable by every package that has a reader (`storage`, `usecases`, `presentation`, `operational`, `commands`) under `tools/check_import_direction.py` without a new edge; `presentation` may import only `core`, `resources` and `schema_diagnostics`, so a helper placed in `storage` would need a new `presentation -> storage` edge.

```python
class StoreAddressError(ValueError):
    kind: Literal["syntax", "containment"]   # which rule refused; .address is the offending text

def check_store_address(address: object) -> tuple[str, ...]:
    """Pure: return the address's segments or raise StoreAddressError('syntax'). Same answer on every OS."""

def resolve_store_address(base: Path, address: object, *, root: Path | None = None) -> Path:
    """check_store_address, then resolve base/address and require the result strictly inside root.resolve() (default: base)."""
```

### C2. Syntax rules (decision is host-independent)

`check_store_address` refuses, on **every** OS, an address that:

1. is not a `str` or is empty;
2. contains NUL or any character whose Unicode category is `Cc` (C0, DEL, C1), a backslash, or `:`;
3. has a non-empty `drive`, `root` or `anchor` under **either** `PurePosixPath` or `PureWindowsPath` (covers `/x`, `//srv/share/x`, `C:/x`, `C:x`, `\x`);
4. has an empty segment (`a//b`, trailing `/`) or a segment made only of dots and spaces (`.`, `..`, `...`, any longer run, and `. `/`.. `, which Win32 strips to `.`/`..`). The all-dots rule is stricter than the owner's "no `.`/`..`": Win32 normalisation strips trailing dots, and whether `...` can alias a parent was not verified on a Windows host, so the conservative rule is adopted (and the schema half, part D, carries the same rule).

It deliberately does **not** restrict letters, digits or `._-` further: the syntax guard is a safety check, the closed character set of owner row 1 belongs to the schema. A legitimate address the survey found (part E) passes both.

### C3. Containment

`resolve_store_address` computes `resolved = (base / address).resolve()` and `root = (root or base).resolve()`. The local revision reader passes `base` = the revision directory and `root` = the Store root, so the address is joined under its revision but may only land inside the Store. It then requires `resolved != root and resolved.is_relative_to(root)`. `resolve()` follows symlinks, so a link pointing outside fails. `OSError`, `RuntimeError` (symlink loop) and `ValueError` from `resolve()` are converted into `StoreAddressError("containment")`. It returns the **resolved** path so the caller opens exactly what was checked.

### C4. Typed errors (existing vocabulary, unchanged)

The helper raises its own `StoreAddressError`; each adapter converts it to the error it already raises, so no diagnostic code is added and no caller changes:

| Adapter | syntax refusal | containment refusal / unreadable |
| --- | --- | --- |
| `LocalSnapshotReader` (R1) | `SnapshotReadError("E_IMMUTABLE_SNAPSHOT_REQUIRED")` (today's code for `..` and leading `/`; an existing test pins it) | `SnapshotReadError("E_STORE_REFERENCE", ...)` (today's "no file") |
| `LocalBaselineRegistry.read` (R2) | `ValueError("E_BASELINE_REFERENCE")` | same |
| `LocalBaselineRegistry.publish` (R3) | returns `None` (today's behaviour for a bad id) | same |
| `materialize._inside` (R4) | `ValueError("E_MATERIALIZER_PATH")` | same |
| `_package_resource`, `resolve_font_resource`, `_safe_icon_address`, `theme_inheritance._safe_relative` (R5-R8) | their existing code (`E_MATERIALIZER_PATH`, `E_FONT_METRICS_UNAVAILABLE`, `E_ICON_ASSET_PATH`, `E_THEME_INHERITANCE_PATH`) | same |

File opening at each adapter is additionally wrapped so an `OSError` from `read_bytes()` becomes the same typed error ("never an OS exception").

### C5. Testing on any OS

The rejection decision must not depend on the host. `check_store_address` is pure and consults both `PurePosixPath` and `PureWindowsPath`, so the vectors of row 3 (`C:/x`, `C:x`, `\\server\share\x`, `a\x00b`, `a\nb`, `a\\b`, `./a`, `a/../b`) are asserted directly on it on all three OS legs, and again through each adapter using a `tmp_path` Store. The symlink vector needs `os.symlink`; the test skips only when the platform refuses to create one (Windows without the privilege), with the reason in the skip message. The Windows-specific join behaviour that motivates rule 3 is asserted with `PureWindowsPath` arithmetic (`PureWindowsPath('C:/s') / 'C:/x'`), which runs anywhere.

## D. The schema half: strict `storeAddress` (plan for a LATER slice; not implemented by the code slice)

### D1. The definition

Add to `common-v0.1` (Spec 56 / #662 D1: "Adding a `$defs` entry to a part version is allowed"; no existing digest changes, so `common` does **not** need `common-v0.2`):

```yaml
storeAddress:
  description: "Strict Store-relative address: segments of letters, digits, `.`, `_`, `-` joined by `/`; no empty segment, no segment made only of dots."
  type: string
  pattern: "^(?!(?:.*/)?\\.+(?:/|(?![\\s\\S])))[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*(?![\\s\\S])"
```

It is newline-proof (`(?![\s\S])` instead of `$`, as #662 D3/T3 already uses for the new defs). Verified against 9 accepted and 24 rejected probes, including `.`, `..`, `...`, `./a`, `a/./b`, `a/../b`, `a//b`, `a/`, `C:/x`, `C:x`, backslash, NUL, `a\n`, `\na`, non-ASCII. Two deliberate differences from the owner's text: (a) "no `.`/`..` segment" is widened to "no all-dots segment" (same reason as C2.4); (b) trailing-dot or trailing-space segments (`a.`) are **not** rejected, because the owner's closed set allows `.`; the Windows alias of `a.` to `a` is recorded as a residual in the review.

### D2. Sites

| Site | Today | Change |
| --- | --- | --- |
| `layout-profile-v0.9` `extends.address` (line 106) | `relativeAddress` | `$ref storeAddress` |
| `revision-store-resource-ref-v0.1` `address` (inline, line 40-44) | inline loose pattern | `$ref storeAddress` |
| `render-context-v0.16` font `locator.address` (line 138) | `relativeAddressDotTolerant` | `$ref storeAddress` |
| `render-context-v0.16` `#/$defs/reference.address` (line 194), used by project/view/theme/colorScheme/layout/actual/snapshot/iconCatalog refs | **`minLength: 1` only: no traversal guard at all** | `$ref storeAddress`. Not named in the issue; the reader guards it today, the schema does not |
| `project-v0.7` `extensions[].resource` (line 72) | `type: object`, unconstrained | not in the owner's list. The resource is handed to a reader (`extensions/profiles.py:26`), so the reader guard covers it; a schema constraint is a separate owner decision (proposed: reference `revision-store-resource-ref-v0.2` at Project's next bump) |
| `icon-catalog-v0.4` `source.address` (line 183), `preset-library-v0.2` `address` (via `safeRelativePath`) | own strict-ish patterns that end in `$` (a trailing newline passes) | not in the owner's list. Fold into the same bumps when those kinds next change; record, do not widen this slice |
| `command-request-v0.2` `payload.snapshotId` (line 61) | `minLength: 1` only | constrain to a one-segment `storeAddress` (the registry builds `snapshots/<id>.yaml`); ships in the command-request bump |

### D3. Which kinds bump, and how

Spec 56 §3.2: a change that makes an existing valid resource invalid is an incompatible change and takes a version bump; batch pending incompatible changes. Every change in D2 rejects inputs that were accepted, so each affected kind bumps:

| Kind (current) | Reason | New version | Committed/packaged files naming the old version (measured) |
| --- | --- | --- | --- |
| `layout-profile` v0.9 | `extends.address` | v0.10 | 41 (src 9, tests 8, examples+conformance 19, docs 4) |
| `render-context` v0.16 | font locator and reference address | v0.17 | 73 (src 4, tests 4, examples+conformance 58, docs 6) |
| `revision-store-resource-ref` v0.1 | the shared part itself | v0.2 (new URN `urn:chrona:revision-store-resource-ref-v0.2`) | n/a: a part, not a resource |
| `command-request` (`chrona/command/v0.2`) | `target`, `payload.*`, `snapshotId` | v0.3 | 10 (tests 5, src 0) |
| `automation-result` v0.1 | `inputs`, `resultTarget`, `artifacts` | v0.2 | 6 (src 3, docs 2) |
| `snapshot-ref` v0.2 | nested Project reference | v0.3 | 10 (src 2, tests 4, examples 1, docs 2) |

**How a version bump is done for a part shared through `$ref`.** A part is frozen once published (`frozenDefs`; #662 D1). `revision-store-resource-ref-v0.1` is both a part and frozen under digest `649e7dd8...`, and its four users reference it by URN. So:

1. Publish `revision-store-resource-ref-v0.2.schema.yaml` (new `$id`; address is `$ref storeAddress`), register it `live` in the inventory with its own `frozenDefs` digest.
2. Publish the new version of each user (`command-request` v0.3, `automation-result` v0.2, `snapshot-ref` v0.3) whose `$ref` names the v0.2 URN and whose `version` const moves; `layout-profile` v0.10 and `render-context` v0.17 reference `storeAddress` directly.
3. Move each predecessor to `state: transitioning` with `successor` and `removalSlice` (the inventory already models this for `scene-v0.6`). `revision-store-resource-ref-v0.1` stays `live` while any live or transitioning schema still references it, then becomes `transitioning`, then is archived in its removal slice. A part is never edited in place.
4. Move the consumers: `src/chrona/resources/__init__.py:150` (part registration), `presentation/contracts/resources.py` (version tables), `app/cli.py`, `operational/command_engine.py` and `snapshots.py:61` (the writer emits the new `snapshot-ref` version).

### D4. Transition and removal slices

- **S-A (this plan's first schema slice):** add `storeAddress` to `common-v0.1`; publish `revision-store-resource-ref-v0.2`; no kind uses them yet. Gate: digest lock for the new def and part; probes (D5) on the def alone.
- **S-B:** the two resource-bearing bumps that ripple through committed corpora: `layout-profile` v0.10 and `render-context` v0.17, re-pointing the committed Context and Layout files (114 files by the counts above), each file's `version` string only, with L1 equivalence proving no document changes verdict.
- **S-C:** the command/result/baseline bumps: `command-request` v0.3, `automation-result` v0.2, `snapshot-ref` v0.3. The reader and writer support v0.2 and v0.3 during the transition.
- **S-D (removal):** after one release of dual support and once no committed fixture uses the predecessors, retire the `transitioning` entries. **Exception:** `snapshot-ref` v0.2 files are immutable, content-pinned resources that already exist in operators' Stores (`snapshots.py:61` has published v0.2 since M26); rewriting them is impossible without changing their identity. Retiring v0.2 would orphan them. See D6.

### D5. What the equivalence gate lists

For each bumped kind the S0 gate (#662) already computes L1 (dereferenced schema) and L3 (probe verdicts). The deliberate deltas to list, per site, as `expected-invalid` probes that the **successor** rejects and the predecessor accepted (both results recorded): `a\x00b`, `a\\b`, `a\nb`, `a\n`, `./a`, `a/./b`, `a//b`, `a/`, `C:/x`, `C:x`, `\\server\share\x`, `a/...`, `..`, and (for `render-context` `reference.address`, which accepts everything) `../x`, `/x`. The gate must also assert that **every committed address is still accepted** (the survey of part E, made permanent), and that `ACCEPTED_TODAY` in `tests/unit/tools/test_schema_parts.py` stays true of the frozen `relativeAddress*` defs: they remain in `common-v0.1` for the predecessors and gain a note that no live successor references them.

### D6. Does anything stop the owner's row-1 bumps as written?

Nothing stops them, with three adjustments the design records for the owner:

1. **The list in row 1 is incomplete.** `render-context`'s `reference.address` (every pinned input), `command-request` `snapshotId`, and Project's `extensions[].resource` are live address sites that the row does not name; the first two are in D2's "change" rows; Project is proposed, not included.
2. **`snapshot-ref` cannot be fully retired.** Its v0.2 instances are immutable, pinned and already in Stores. The bump is sound for new writes, but the predecessor stays readable, so "removal slice" for it means removing the *schema for new authoring*, not refusing to read old baselines. The code guard of this slice is what protects those old baselines.
3. **A schema cannot replace the code guard.** The schema cannot see a symlink, and a document that never went through schema validation (the readers are also called on references decoded from a Store) reaches the adapter directly. That is why rows 2 and 3 ship first and independently.

## E. The committed-address survey (owner row 4)

Method: every tracked `.yaml`, `.yml`, `.json` file outside `schemas/` was parsed and every string value under an `address` key was tested against the strict form (`[A-Za-z0-9._-]+` segments joined by `/`, no `.`/`..` segment); every `"address": <literal>` in tracked `.py` files was tested the same way (f-string placeholders substituted). *Measured* at `0ab5a6eb`.

| Population | Files with addresses | Address occurrences | Distinct |
| --- | --- | --- | --- |
| `examples/` and `conformance/` | 42 | 405 | 89 |
| `docs/` (YAML/JSON evidence, mostly archived) | 11 | 50 | 14 |
| packaged `src/chrona/resources/` | 2 | 7 | 7 |
| `packages/chrona-fonts-noto-cjk` | 1 | 4 | 4 |
| Python test/source literals (`"address": ...`) | 39 literals | 39 | |

- Characters used across all structured addresses: `- . / 0-9 _ a-y` (lowercase only, at most 4 segments). No space, colon, backslash, NUL, control or non-ASCII character appears anywhere.
- **Exceptions (2), both deliberate negative fixtures that must stay rejected:** `conformance/revision-store/invalid-address.yaml` (`../controller-x.yaml`) and `tests/unit/chrona/presentation/model/test_presentation_closure.py:29` (`../context.yaml`, asserts `E_IMMUTABLE_SNAPSHOT_REQUIRED`). There are **no** exceptions among addresses that are meant to be accepted, and none uses a `.` or `..` segment, a `./` prefix, or a repeated `/`.
- Runtime-derived addresses (`context_path.relative_to(example).as_posix()`, `snapshots/<id>.yaml`, theme child addresses) are exercised by the existing unit and integration tests, which the code slice runs in full.

Conclusion: the tightening (both the code guard and, later, `storeAddress`) is compatible in practice with every committed and packaged address. No migration is needed.
