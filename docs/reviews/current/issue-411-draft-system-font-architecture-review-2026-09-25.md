# Architecture Review — Draft System-Font Provider (#411)

**Decision:** accepted.

The design preserves the central rule that Layout measures the exact face an
adapter paints.  It relaxes only immutable closure, not measurement or
fallback policy.  A renderer that enables unrestricted system lookup would be
unsound, because its chosen face could differ from Layout's; passing the one
resolved file while retaining `skip_system_fonts=True` avoids that split.

The system locator cannot be a normal Render Context resource: a host path is
not portable, addressable through a snapshot reader, or safe as immutable
provenance.  Keeping it in `DraftRender` makes the volatile capability
explicit and lets ordinary immutable closure/materialization retain their
existing contract.

Fontconfig is an appropriate initial bridge only behind a port and only with
post-resolution OpenType verification.  The review rejects directory scanning
and family fallback as product behavior.  CoreText/DirectWrite are future
platform adapters, not reasons to claim cross-platform support before their
bridges exist.

The implementation must add structural tests proving that system files never
enter immutable Context serialization or Scene provenance, and that PNG does
not disable its restricted font set merely because a host font was resolved.
