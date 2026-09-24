# Implementation Plan: Windows Portability (#359)

## W359-1 — Source-byte and entry-point foundation

Add `.gitattributes`, contributor guidance, `python -m chrona`, explicit UTF-8
text I/O, and an AST gate. Add unit tests for the gate and module entry point.

**Acceptance:** a CRLF-configured clone preserves every identity-pinned source
byte, and no production/tool/conformance text call has an implicit encoding.

## W359-2 — Portable filesystem adapters

Implement the `revision-`-prefixed token-directory codec (including device-name
and trailing-dot safety), replace hard-link publication with exclusive
reservation plus replacement, and add lazy POSIX/Windows locking. Route
snapshot readers and materializers through the codec.

**Acceptance:** `baseline:<digest>` round-trips through local snapshot reads and
materialization; races remain no-overwrite; lock and publication tests do not
require `fcntl` on a simulated Windows import path.

## W359-3 — Windows release gate

Add `windows-latest` to the existing conformance matrix and a Windows-only
default-autocrlf clone/materializer reproduction test. Run focused tests, full
suite, conformance, structural gates, wheel build/install, isolated smoke, and
inspect the GitHub matrix before release review.
