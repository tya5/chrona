# Architecture Review — Minimal Template Package Topology Correction (#376)

**Decision:** Accepted for implementation.

The correction reduces, rather than changes, packaging authority.  A resource
inside the `chrona` package is owned by normal package inclusion and accessed
only through `importlib.resources`; the force-include table remains reserved
for authorities outside that tree.  It introduces no repository-relative
runtime lookup or duplicate package path.
