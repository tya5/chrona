# Schema Authoring and Diagnostics

**Status:** Accepted (amended 2026-09-23; annotation-applicator correction)
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
schema inventory. It traverses every reachable schema applicator, including
every `allOf` branch and nested `if`, `then`, `else`, and `not`; it never treats
an implementation container such as `properties` as a schema node. A pattern,
format, conditional form, or `allOf` wrapper with a local assertion is
non-obvious and MUST carry a valid example. A pure `$ref` reuse branch remains
exempt; a `$ref` combined with a local constraint is not pure reuse. The lint
validates every example in its enclosing schema context and reports a
schema-location pointer for defects.

An `allOf` branch that only carries a structural composition into its parent is
traversed but is not a second author-facing node: its ordinary property prose
belongs to the owner schema rather than being duplicated under the composition
carrier. This exemption never suppresses a nested applicator or a local
reference constraint; those are discovered and checked at their own branch.
It is run in conformance and before generated reference publication. Generated
reference may consume this metadata, but tutorials remain independently
authored.

## 3. Structured validation explanation

All schema ingress boundaries use the same immutable internal value before
mapping to their existing public error types. An ingress supplies its known
resource kind and identity; identity is absent when malformed input cannot
safely establish one:

```text
SchemaViolation {
  resourceKind: string | absent
  resourceIdentity: ClosureIdentity | absent
  instancePointer: RFC6901 pointer
  rule: enum | const | required | additionalProperties | type | range | pattern | format | union
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
messages name the declared bound or format.  A `format` failure (for example
`date`) reports `expected` as a description of the format, such as
`YYYY-MM-DD calendar date`, and never the offending value.  No raw value is echoed when it may
contain large or sensitive user content.

The selection algorithm is deterministic:

1. collect JSON Schema errors;
2. recursively reduce branch contexts;
3. if an input has a declared discriminator, select its matching branch and
   report that branch's most specific violation; an unknown tag reports the
   allowed tags once;
4. for key-shape unions, report the most-specific matching form or a compact
   ordered list of valid forms; do not invent a tag. A union branch that only
   references a shared schema part (`urn:chrona:` `$ref`) is described by the
   part's definition, so moving a form into a part does not change the message;
5. rank remaining errors by deepest instance pointer, keyword specificity,
   schema order, then message; and
6. construct `SchemaViolation` from the selected error.

Presentation contract parsing maps this value to `SchemaContractError` and
then the existing `E_<KIND>_SCHEMA` / `sourceRef` CLI surface.  Core Project
validation maps it to `Diagnostic("E_SCHEMA", message, pointer)`.  Both retain
their existing semantic validation phase; this shared helper performs no
semantic normalization and is not imported by View, Layout, Scene, or renderer
code.

Operational resource, command, and authoring ingress boundaries use the same
reducer before mapping to their stable existing error codes. They may retain a
smaller public error record, but must not expose raw `jsonschema` wording.

### 3.1 Unsupported presentation resource versions (#489)

For any resource kind registered by the presentation contract schema registry whose declared string `version` is not
registered, ingress MUST refuse the resource with `E_RESOURCE_VERSION_UNSUPPORTED`,
resource-local `sourceRef: /version`, and an author-facing message naming the
resource kind, established id when available, found complete version, and all currently supported complete
versions in stable order. The supported set comes from the contract schema
registry. Missing and non-string versions retain their existing malformed-envelope
diagnostic; they are not labeled as unsupported historical versions in this
change. Unsupported kinds and supported-version body schema faults also keep
their separate diagnostics. No stale version is silently
upgraded or rendered with a fallback contract.

For a declared member of a locally copied builtin preset, the CLI additionally
names the catalogue preset id and instructs a new `chrona preset copy <id>` into
a new directory followed by re-applying edits. This command-specific remedy
belongs to the CLI and only applies when member provenance is established; a
stale explicit override or standalone resource does not inherit it. The
contract and closure layers preserve typed version evidence and the pointer,
including in multi-resource ingress findings, without carrying command text.

### 3.2 Schema version evolution (#591)

For View, Layout Profile, and Project schemas, an additive optional property
MUST be added to the current schema version in place, without a version bump,
when omitting it preserves the resource's prior behavior. A schema-level
`default` annotation does not set a runtime value; the owning consumer MUST
provide and test the behavior that omission requires. Theme schema additions
follow the same rule.

A version bump is reserved for an incompatible contract change: removing,
renaming, or retyping an existing field; changing an existing field's default
behavior; adding a required field; or another change that makes an existing
resource invalid or changes its behavior. When a bump is required, batch the
pending incompatible changes into that version. Do not silently upgrade a
stale resource; the unsupported-version behavior in §3.1 remains in force.

Conformance compares newly introduced schema-inventory predecessor/successor
pairs for View, Layout Profile, and Project. Transitions already published when
this rule was adopted (through View v0.28, Layout Profile v0.9, and Project
v0.7) are historical and are not retroactively rejected; Project v0.6→v0.7,
for example, contains optional additions. It MUST fail a new version bump
when, after normalizing the corresponding version strings at `$id`,
versioned `title`, version `const`, and only the root schema
`examples[*].version` values equal to those version strings, the entire schema change consists
of one or more insertions of optional property declarations under object
`properties` maps, with no other example, title, or identity
change is normalized. Each inserted property name MUST be absent from the
containing object's `required` list; that list and all existing schema nodes
must remain unchanged. Each new property subtree may define its own
constraints, but no existing assertion may change. The comparison is structural,
not a proof of runtime behavior; omission behavior remains the responsibility
of focused consumer tests. If a composition or conditional requirement makes
optional status ambiguous, conformance MUST report the comparison as
unsupported or fail closed rather than classify the change as additive. A
version bump containing an incompatible schema change is outside this
additive-only failure rule.

Schemas check the shape of a date, not the calendar. Every ISO date field is
declared with a pattern (`^\d{4}-\d{2}-\d{2}$`, the `isoDate` definition of the
common schema part) and no schema asserts `format: date`; the validator factory
installs no format checker. A string of the right shape that is not a calendar
date (for example `2026-02-30`) is refused later by the consumer that reads it (Project
reports `E_SCHEMA` "Expected ISO Date"), not by the schema. The `format` rule in
§3 stays implemented for a schema that asserts a format. Making a schema refuse
impossible dates, or narrowing the pattern (ASCII digits, no trailing newline), changes
which inputs a schema accepts and moves a code, a stage and a message, so it follows the version bump
rule above. The decision and its revisit condition are recorded in the #662 design (D2, D3).

Adding a value to an existing `enum` is an in-place widening when every existing resource
stays valid and behaves the same and the consuming code handles the new value. It is not an
optional-property insertion, so the mechanical predecessor/successor check above does not apply; the equivalence gate
lists it as a deliberate delta. View v0.28's annotation anchor `endpoint` gained `end` this way: `end` is the
canonical spelling of a span's end (as in a Project `endpointRef`) and `finish` its alias, and Layout normalises `end`
to `finish` before any identifier is built, so the two spellings produce the same Scene.

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
