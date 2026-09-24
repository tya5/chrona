# Windows Portability Release Review (#359) — 2026-09-24

## Scope and result

#359 is complete. Chrona now has one Windows-safe, injective filesystem codec
for opaque snapshot and Actual revision tokens. It preserves the externally
visible token while storing it as a `revision-`-prefixed percent-encoded path
component, eliminating invalid colon, device-name, and trailing-dot cases.

The CLI no longer imports POSIX locking support at module import time. Its
authoring lock selects `fcntl` on POSIX and `msvcrt` on Windows. Immutable
baseline/result publication uses exclusive destination reservation and atomic
replacement instead of hard links. `python -m chrona` is a supported entry
point.

## Boundary review

The codec remains in storage adapters and materialization boundaries; it does
not alter Revision values, schemas, closure identities, scheduling, Layout,
Scene, or renderer semantics. LocalSnapshotReader, LocalActualStore, Context
materialization, and render asset lookup share that one codec. Absolute and
backslash resource addresses are rejected before filesystem access.

Repository text is LF-normalized and binary assets are marked binary through
`.gitattributes`. Runtime, test, tool, and conformance readers declare UTF-8;
the AST gate protects the production/tool/conformance roots. Structural gate
path handling is normalized through `Path.as_posix()`, so the gate itself is
portable.

## Evidence

- Focused codec, lock, no-hard-link, module-entry, baseline-to-Context, and
  Windows clone tests passed locally.
- Local full suite: 659 passed, 16 platform-specific skips.
- Local conformance, structural gates, wheel build/install, and isolated smoke
  passed.
- GitHub Actions run
  [35953823198](https://github.com/tya5/chrona/actions/runs/35953823198)
  passed on `ubuntu-latest`, `macos-latest`, and `windows-latest`, including
  full pytest, the Windows default-autocrlf clone/materializer reproduction,
  wheel install, and smoke test.

## Release decision

Accept. The original #359 acceptance criteria have evidence on all supported
CI platforms, with no user-visible rendering-policy change.
