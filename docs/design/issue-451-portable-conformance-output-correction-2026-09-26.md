# Design Correction — Portable Conformance Output (#451)

Conformance's aggregation boundary owns its output encoding.  Before printing
the aggregate report, it configures writable stdout as UTF-8.  Child outputs
remain decoded Unicode facts; no fallback escaping, OS-specific text policy,
or product-layer dependency is introduced.
