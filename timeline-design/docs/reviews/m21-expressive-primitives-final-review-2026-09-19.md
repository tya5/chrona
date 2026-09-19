# M21 Expressive Review Primitives Final Review — 2026-09-19

**Disposition:** Pass — M21 complete.

The adapter derives quarter labels, table hierarchy, relation connectors, and optional
annotation notes from Layout slots, View-selected rows, and semantic Project references.
Connector output is gated by the declared layout constraint and uses stable relation IDs;
it does not use profile/title/sample-specific branches. Roles resolve expression tokens
without changing semantic facts.

Evidence: generic relation primitive test, Controller Z expressive SVG, full conformance,
and 91 passing tests.
