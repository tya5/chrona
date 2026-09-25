# Design Plan — Portable Derived-Artifact Report Paths (#451)

## Trigger

The #451 release run at `46ed616f` passes conformance, Linux, macOS, and the
newest-Python materializer reproduction.  Windows full pytest fails one
derived-artifact report test: the report emits `docs\\report.md` whereas its
cross-platform contract and test fixture require the repository identity
`docs/report.md`.

## Question

How should the tool-only report distinguish a filesystem `Path` used for local
I/O from the stable repository-relative path it publishes in text, unified-diff
headers, and GitHub Actions annotations?

## Planned decision work

1. Confirm every outward report path field uses one canonical POSIX repository
   identity rather than an OS-native `Path.__str__` representation.
2. Preserve `Path` objects for file I/O and containment checks; canonicalize
   only at the report boundary.
3. Review the result against #451's platform-safe reporting invariant and
   ensure it neither alters comparison bytes nor tool exit authority.

## Evidence

- focused stale-report fixtures on normal and separator-sensitive relative
  paths;
- existing stale producer and conformance checks; and
- one three-platform CI release result after the correction.
