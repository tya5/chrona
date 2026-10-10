# Issue 918 — diagnostic owner and transport design

Plan: [design plan](../archive/planning/issue-918-diagnostic-owners-design-plan-2026-10-09.md).
Normative authorities: Specs 08, 35, 50, 56 and 66.

## Owner detail and result contracts

Keep stable diagnostic codes and their existing error classes/status semantics.
The raising owner supplies the invalid field, identifier, token, revision or
measurement and the expected form. Do not echo full Project/Actual documents,
raw sensitive schema values, or unbounded text. Type/field/identifier evidence
is preferable to a whole-object repr. A local helper may standardize a family,
but must accept the actual operands; transport cannot invent them.

Use `sufficient` only after checking every site for that code: no useful operand
exists and the identifier names the invariant completely. Record the reason;
never use frequency, internal visibility or a fallback catalogue as the reason.
Every changed code requires a provoking value assertion, with separate owner
fixtures for heterogeneous families. Remove the policy's `sites` after the last
bare site is resolved. Inventory completeness is not proof of message quality.

Actual/intake/snapshot diagnostics retain `tuple[str, ...]` and carry
`E_X: detail`. Existing leading-code extraction feeds automation rows; update
whole-string comparisons, not codes. Inventory recognizes these named result
constructors' diagnostic tuple arguments, including keyword arguments, without
counting unrelated string tuples or counting a site twice. Revisions, keys,
observation/snapshot IDs and identity mismatches come from command/storage
owners. Rejection remains atomic and performs no new writes.

## Render transport

Select one unconditional stdout JSON envelope after successful artifact
publication: `{status: "ok", diagnostics: [], warnings: [...]}`. It includes
`warnings: []` for a warning-free render; successful warnings keep exit 0.
Apply it to `render`, `render-review` and `render-workspace`. Expected warnings
are not also printed to stderr. Failures keep their existing envelope/exit
mapping. Tracebacks/logging, if any, remain stderr, not a second machine API.

Compared alternatives: optional `--json` retains two discoverable machine
contracts; stdout plus a human stderr line duplicates successful-reporting
work; keeping JSON lines on stderr perpetuates the special agent parser. The
selected unconditional envelope removes that exception. This intentionally
changes empty stdout/stderr-warning consumers: read stdout.warnings instead.
Reversal is an explicit Spec 66/skill/golden change back to the documented
stderr policy, not a hidden alias or fallback flag. Artifact bytes are separate
from console JSON. CLI and MCP retain their existing warning-row projections;
compare each row's common fields and lossless ledger `detail`, including info
counts, rather than silently flattening MCP's contract.

## Producer-side provenance

Use immutable diagnostic subject facts: canonical source pointer and optional
known title, captured from an explicitly identified Project object. Escape
`~` and `/` in an object ID as JSON Pointer tokens (`/objects/<escaped-id>`).
Never identify an object by splitting a diagnostic/placement/primitive ID.

Layout carries an ordered provenance sidecar alongside its existing diagnostic
strings, plus explicit subjects for typed fit warnings. Completed Scene
projection carries that sidecar without measuring or changing geometry.
Primitive-to-subject links are captured while the typed source is available,
and Scene findings use exact primitive identities to retrieve those links.
The use case passes subject facts to the warning ledger; the ledger formats
them, and CLI/MCP merely serialize. Sidecars are runtime facts, not new Scene
schema members, paint, identity inputs, or authoring resources.

Object-backed rows, marks, labels and annotations carry their actual object
pointer/title even when the label is suppressed. View/calendar/slot/axis,
Theme/legend, field/entity group and relation-only diagnostics do not acquire
a fictional Project object. A finding involving several subjects keeps their
stable first-seen order, names the known titles in its subject, uses the first
Project pointer as `sourceRef`, and retains additional subjects in detail.
An ownerless finding retains its existing source (or `/`). Missing title means
the known pointer/identifier is used, never a fabricated title.

Keep each original diagnostic identity and its order. For fit warnings, any
existing raw source in the identity remains unchanged even when payload
`sourceRef` is enriched. Subject metadata never enters the collapse cause or
key. Preserve first-occurrence metadata, exact count, distinct occurrence
order/cap and every Scene per-placement fact. No metadata may enter Scene
serialization, SVG/PNG content or layout input metrics.

## Verification and migration

### Additional failure-path closure (review 6085291520)

Color-scale errors retain the `ValueError` family but expose stable `code`,
bounded `detail`, and canonical `source_ref`. The resolver names scale and
missing/extra keys; Theme slot failures point to
`/body/colorScales/<escaped-id>/slots` (the actual schema property, not the
review's illustrative `scales`). Encoding failures carry the caller's View
pointer, including `/body/grouping/tint` for group tint. The outer
`render_review` boundary catches `ColorScaleError` around all of `_render_review`,
replacing the inner resolver-only catch; this covers later normalization's
`color_for` too. The resolved model scale retains the caller's encoding pointer
as non-identity runtime provenance. Never use a formatted exception string as
a diagnostic code. A dangling Theme slot reference belongs to that slot;
malformed Scheme categories retain their existing Scheme-owned code/pointer,
not a fabricated Theme source.

View normalization captures `/body/annotations/<index>/anchor` on the typed
annotation intent. This optional runtime provenance is excluded from equality,
hash and repr and is not a schema, geometry, Scene or cache-identity field.
Layout uses it for typed `LayoutError` anchor failures, naming annotation,
object, facet/endpoint and why the selected mark or endpoint is unavailable.
Post-resolution anchor failures use the same provenance. Synthetic intents
without a declared source use `/`, never an invented index. Do not substitute
a planned mark for an absent actual or change mark eligibility.

Only `tools/materialize_example.py:main` maps failures through the existing
pure `report_failure` service: one stdout `{status, diagnostics}` envelope and
its mapped exit code, preserving all typed diagnostic rows and source data.
Successful standalone materialization stays silent; library calls still raise
their typed exceptions and never print. This intentionally replaces the
standalone failure traceback as its usable machine interface. Unexpected
exceptions use the existing `E_TOOL_FAILURE` mapping, not a new taxonomy.
The test cache reads fresh warning rows from stdout; no stderr fallback.

These changes add diagnostic provenance/transport only. No resource migration,
schema version, color allocation, anchor fallback, geometry or artifact byte
change is authorized. Direct owner tests and use-case/adapter tests must prove
stable codes separately from messages, canonical escaped pointers, explicit
absence reasons, complete rejected diagnostics, silent success and warning
mutation isolation; CI audits generated artifacts as one batch.

Tests provoke each fixed code with distinctive operands; named detail-removal
or operand-replacement mutations must fail those assertions. Test escaped IDs,
unknown titles, suppressed labels, same-cause different objects, non-object
and multi-owner findings. Verify enriched subjects independently of geometry
and compare before/after Scene diagnostic strings, SVG and PNG bytes. Review
the CLI characterization delta and MCP parity row by row, not by regenerating
goldens without explanation. No Project/View/Theme/Scene schema version change
is required; only diagnostic text/console transport intentionally changes.
