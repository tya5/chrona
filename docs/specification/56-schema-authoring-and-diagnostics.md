# Schema Authoring and Diagnostics

**Status:** Proposed
**Depends on:** [05 Project Format](05-project-format.md), [09 Application
Architecture](09-application-architecture.md), [13 Presentation Format](13-presentation-format.md),
and [32 Repository Layout](32-repository-layout-and-packaging.md).
**Owns:** author-facing schema annotations, structural-validation explanations,
the live-schema documentation-reference gate, and the Project schedule union's
discriminated successor.  It does not own semantic scheduling rules or a
renderer diagnostic surface.

## 1. Decision

Schemas are an author-facing reference surface.  Every live authorable shape
MUST have concise schema-owned descriptions and, when the shape is non-obvious,
an example.  Structural validation MUST return one deterministic explanation
with the resource identity, RFC 6901 instance pointer, failed rule, and useful
expected values.  It MUST NOT return a Python traceback, a flat schema error
list, or recover by choosing another syntax.

The Project schedule union moves from the ambiguous v0.5 `mode: fixed` pair to
the fully tagged v0.6 vocabulary: `fixed-point`, `fixed-span`, `scheduled`, and
`rollup`.  This is a clean contract migration: no parser accepts v0.5 fixed
syntax after first-party migration.

## 2. Schema annotation profile

An **author-facing node** is a reachable schema node that an author can select,
write, omit, or violate: a document/root definition, object property,
array item, branch, enum/const, pattern/range constraint, or required
combination.  Pure reuse plumbing (`$ref` wrapper with no local assertion) and
implementation-only inventory/example schemas are not author-facing.

Every author-facing node MUST have a `description` that states its intent and
constraints in author language.  A node with an awkward shape, a branch choice,
or a non-obvious format MUST additionally have at least one valid `examples`
value.  Descriptions do not restate JSON Schema keywords mechanically and do
not promise semantic behavior owned by a later validation stage.

The repository supplies a schema-annotation lint over all `live` entries in the
schema inventory.  It traverses only reachable author-facing nodes, validates
that the profile is present, validates examples against the enclosing schema,
and reports a schema-location pointer for annotation defects.  It is run in
conformance and before generated reference publication.  Generated reference
may consume this metadata, but tutorials remain independently authored.

## 3. Structured validation explanation

All schema ingress boundaries use the same immutable internal value before
mapping to their existing public error types:

```text
SchemaViolation {
  resourceKind: string
  resourceIdentity: ClosureIdentity | absent
  instancePointer: RFC6901 pointer
  rule: enum | const | required | additionalProperties | type | range | pattern | union
  expected: ordered, JSON-safe values or form descriptions
  actualKind: string | absent
  message: deterministic author-facing explanation
}
```

`instancePointer` identifies the failing input value.  For a missing required
member it identifies the containing object; the message names the missing
member.  For an unexpected member it identifies the containing object and
names the member, including one deterministic near-name suggestion when the
Levenshtein-free `difflib` similarity threshold is met.  Enum/const messages
show the allowed literal values in schema order.  Numeric, length, and pattern
messages name the declared bound or format.  No raw value is echoed when it may
contain large or sensitive user content.

The selection algorithm is deterministic:

1. collect JSON Schema errors;
2. recursively reduce branch contexts;
3. if an input has a declared discriminator, select its matching branch and
   report that branch's most specific violation; an unknown tag reports the
   allowed tags once;
4. for key-shape unions, report the most-specific matching form or a compact
   ordered list of valid forms; do not invent a tag;
5. rank remaining errors by deepest instance pointer, keyword specificity,
   schema order, then message; and
6. construct `SchemaViolation` from the selected error.

Presentation contract parsing maps this value to `SchemaContractError` and
then the existing `E_<KIND>_SCHEMA` / `sourceRef` CLI surface.  Core Project
validation maps it to `Diagnostic("E_SCHEMA", message, pointer)`.  Both retain
their existing semantic validation phase; this shared helper performs no
semantic normalization and is not imported by View, Layout, Scene, or renderer
code.

## 4. Union policy and Project v0.6

Use a discriminator only where a stable author-owned tag already expresses a
real semantic form.  A union whose alternatives are selected by key shape,
literal scalar type, or conditional constraints remains a documented union;
its diagnostic reports the legal forms rather than fake metadata.

Project v0.6 schedule forms are:

| `mode` | Required members | Completed placement |
| --- | --- | --- |
| `fixed-point` | `at` | point at `at` |
| `fixed-span` | `start`, `end` | span `[start, end)` |
| `scheduled` | `amount` | derived span under existing anchors/constraints |
| `rollup` | none | derived envelope of children |

The v0.6 scheduler maps both fixed tags to the existing authoritative fixed
placement operation.  Endpoint availability, fixed-target constraints,
calendar interpretation, rollup derivation, and all semantic dates are
unchanged.  First-party Project documents, snapshot/context fixtures, profiles
that name the project format, commands, public examples, and conformance
evidence migrate atomically.  The v0.5 schema is removed from the live
inventory and parser mapping at that point; a converter, compatibility branch,
or silent rewrite is out of scope.

## 5. Live documentation references

The schema inventory and each live schema's `$id` are the only source of truth
for authorable identifiers.  A documentation gate scans normative
`docs/specification` files for YAML `version:` declarations and contract
literals.  Each occurrence is explicitly classified as one of:

* **current** — it MUST resolve to a live schema identifier/version; or
* **historical** — it MUST state its successor or archival status and cannot be
  presented as authorable input.

The gate rejects an unclassified occurrence and a current reference that has
no live schema.  `docs/archive` is excluded because it is historical by path;
current specifications are not exempted merely because they describe an older
decision.  This removes drift without pretending historical design records are
current contracts.

## 6. Evidence and migration gates

Implementation requires:

1. annotation-lint failures for missing description/example and an all-live
   positive run;
2. focused invalid Project, View, Theme, Layout, and nested union fixtures
   proving pointer, expected values/forms, and stable one-error selection;
3. Project v0.6 point/span/scheduled/rollup fixtures proving schedule and
   public CLI JSON equivalence in semantic content after migration;
4. negative v0.5 fixture proving no compatibility acceptance;
5. documentation-gate tests for current, historical, missing, and stale
   contract references; and
6. full tests, public materializers, generated SVG diff review, and installed
   package checks.

The schema and prose changes are accepted only together.  Passing a schema
lint while an author receives a generic error, or adding a helpful error while
leaving a live unannotated schema, is incomplete.
