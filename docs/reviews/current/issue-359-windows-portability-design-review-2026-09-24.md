# Windows Portability Architecture Review (#359) — 2026-09-24

## Decision

Accept a portability foundation that preserves existing semantic contracts.

### Opaque revision tokens

Revision tokens remain opaque external identities. A new storage-only codec maps
each token to a single safe directory component using percent encoding with
`-._` as its only unescaped characters. This mapping is injective: `:` becomes
`%3A`, while an authored `%3A` becomes `%253A`. No schema restriction or
semantic token migration is introduced. Local snapshot readers and all
materializers use the same codec.

### Publication and locking

The authoring aggregate lock is an operational adapter. It imports `fcntl` only
on POSIX and `msvcrt` only on Windows, creates a one-byte lock record, and has
the same exclusive advisory lifetime on both platforms. Result and baseline
publication reserve their destination with exclusive creation before replacing
the reservation with completed temporary bytes. This removes hard-link support
as a filesystem requirement while retaining no-overwrite behavior.

### Text and checkout bytes

All runtime, tool, and conformance text I/O declares UTF-8. A structural AST
gate rejects future implicit `read_text`/`write_text` calls in those roots.
Repository text is LF-normalized through `.gitattributes`; binary assets are
marked binary. Content identities continue to identify exact checked-out bytes,
not a normalization performed by Chrona.

### Boundaries

This change does not add Windows behavior to scheduling, Layout, Scene, or
renderers. Filesystem names are an adapter concern; revision token values,
closure identities, and bytes emitted by materializers remain unchanged.

## Whole-architecture alignment

The codec belongs below immutable-reference resolution, so callers supply and
diagnose the original token. Operational locking and writes remain outside the
presentation/use-case pipeline. `.gitattributes` protects source authority
before any parser or identity verifier reads it. The CI matrix therefore tests
the same public use cases rather than adding a Windows-only execution path.
