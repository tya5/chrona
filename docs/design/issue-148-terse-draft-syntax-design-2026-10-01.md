# Design — Terse draft syntax that compiles to Project YAML (#148)

**Status:** Proposed for architecture review
([review](../archive/reviews/issue-148-terse-draft-syntax-architecture-review-2026-10-01.md)).
**Plans:** [design plan](../archive/planning/issue-148-terse-draft-syntax-design-plan-2026-10-01.md),
[implementation plan](../archive/planning/issue-148-terse-draft-syntax-implementation-plan-2026-10-01.md).
**Normative home:** [`docs/specification/65-terse-plan-syntax.md`](../specification/65-terse-plan-syntax.md)
(landed with slice 1). Section 3 and the mapping table of section 4 are a pointer here (AGENTS.md: normative
behaviour lives in one living specification); this document keeps the rationale, measurements and alternatives.

## 1. Decision summary

Chrona gets a small, line-oriented text syntax (the "terse plan", file suffix `.chrona`, fence info string
`chrona`) that **compiles to** a `timeline/v0.7` Project and never replaces it.

- One statement per line. A project line, calendar lines, and one line per object. Dependencies are a clause
  on the dependent object's line (`after pdr +1wd`), so a plan reads in the order a person thinks it.
- The compiler is a pure function from text to either a Project (as deterministic YAML bytes) or a list of
  positioned diagnostics. It does not schedule, validate semantics itself, read files, or know about
  presentation. Core validation remains the only owner of Project meaning.
- The grammar's scope is stated by a rule (section 2.3): identity, title, kind, hierarchy, schedule,
  constraints, calendars and dependencies. Everything else in the Project (fields, deadline, planned
  progress, attachment, WBS code, link, entities, annotations, scenarios, extensions) is YAML.
  Leaving the syntax is a one-way hand-off: `chrona compile plan.chrona -o project.yaml`, then the YAML is
  the only authority.
- `chrona compile` ships first. Later the draft path (`render`, plus `validate` and `schedule`) accepts a
  `.chrona` path directly through the CLI adapter, by compiling into a temporary Project file, so
  presentation and storage never learn the syntax.
- No new dependency: hand-written lexer, parser and YAML emitter.
- Ids are never invented: a terse name is the Project id, verbatim, and must already be a valid `slug`.

Measured evidence for the shape (throwaway spike, section 13): a 32-line terse plan reproduces the entire
schedule of `examples/halcyon-1` (29 objects, 24 dependencies, 2 calendars) with identical placements and
critical set.

## 2. The case, re-derived

### 2.1 What the numbers say now

Issue comment 1 asked for the cost/benefit to be re-derived. Measured on `main` at `02a1c9b1`:

| Plan | Hand-written YAML | Terse |
| --- | --- | --- |
| Packaged minimal starter (`project.yaml`, 3 objects, 1 gate) | 7 lines (flow-style objects) | 4 lines |
| HALCYON-1 schedule core (29 objects, 24 dependencies, 2 calendars; no `fields`, WBS, links, annotations, scenarios) | 481 lines / 8.6 KB in block style (PyYAML dump of the same data) | 32 lines / 2.0 KB |
| HALCYON-1 as authored | 258 lines / 10.7 KB, flow-style objects, includes all of the above | not expressible in full |

Beginner cost is no longer the argument: #376 and #377 made the YAML starter seven lines with no
presentation files, and terse saves three lines there. The argument that survives (comment 2) is
**density for generated output and Markdown embedding**: dependency-heavy plans are about four times smaller
in bytes, a dependency costs a clause instead of a 150-190 character relation line, and an agent can emit and
repair the whole plan in one pass if errors are positioned (section 7).

### 2.2 What it costs

A new public grammar that must stay compatible: Spec 65, a hand-written parser and emitter of roughly 600
lines, about 30 error codes, a guide, and a doc-check extension. The cost is bounded by three decisions:
the scope rule (2.3), the ledger test that forces a conscious decision when the Project schema grows
(5.3), and one-way compilation.

### 2.3 The scope rule (answers comment 1)

The 80 Project properties are not the grammar's problem to chase. **A construct belongs in the grammar iff
all hold:**

1. it determines identity, hierarchy, dates or dependencies (what the scheduler consumes) or is the title
   of the thing being named;
2. its value is a scalar, a date, an amount or a short list, never a free-form map, prose or a reference
   to another top-level section;
3. it has an unambiguous one-line spelling that maps to exactly one Project construct.

Applying it: in are `project.id/title/calendar`, `calendars`, `type`, `title`, `parent`, `calendar`,
`schedule` (all four modes' authorable forms) and `constraints`, `relations` (endpoints and lag).
Out, with the reason: `fields` (free map), `entities`, `annotations`, `scenarios`, `extensions` (other
sections or prose), `link` (two shapes), `wbsCode` (derived order is the default), `deadline`,
`plannedProgress`, `attachesTo` (do not affect dates; presentation-adjacent metadata), `fiscalStartMonth`,
relation endpoints other than `start`/`at` on the successor, and `mo`/`y` lags.

Honest consequence, measured across `examples/*/project.yaml`: of 153 object properties in HALCYON-1, 101
are expressible; the 52 that are not are `fields` (26), `wbsCode` (16), `plannedProgress` (8),
`deadline` (1), `link` (1). Five of the six example Projects put `fields` on nearly every object because the Views
group by it. A plan that needs owner swimlanes therefore leaves the syntax. That is the intended trade: the
syntax makes the first draft fast, YAML is where a plan that needs a View grouping lives. Option B (inline
`key=value` string fields) is specified in 5.2 and is not recommended for v0.1 (187 of 194 corpus field values
are strings, so it would work, but it moves the escape hatch rather than removing it).

## 3. The grammar (terse 0.1)

The grammar (lexical rules, statements, semantics, default endpoints, kinds and name resolution) is normative in
[Spec 65](../specification/65-terse-plan-syntax.md) sections 2 and 3 as of slice 1 and is not repeated here. Only the
worked examples remain, as the source of the committed golden fixtures (`tests/fixtures/terse/`).

### 3.1 Examples

The issue's sketch, in grammar form (this exact text is a golden fixture; a title with spaces is quoted):

```text
terse 0.1
project halcyon-1 "HALCYON-1"
calendar engineering mon-fri except 2027-04-02

pdr "Preliminary design review" gate 2027-03-05
structure "Primary structure fabrication" task 20wd after pdr +1wd
avionics "Avionics integration" task 15wd after structure
cdr "Critical design review" gate 2027-05-07 after avionics.start
```

HALCYON-1's schedule core, including groups (nesting is two spaces), anchors, a bound, a per-object calendar and
a lag in another calendar:

```text
project halcyon-1 "HALCYON-1" calendar engineering
calendar engineering mon-fri except 2027-04-02 2027-05-31 2027-07-05 2027-09-06
calendar range mon-sat except 2027-10-09 2027-10-16

pdr "Preliminary design review" gate 2027-03-05
structure "Primary structure fabrication" task 20wd after pdr +1wd
avionics "Avionics integration" task 15wd after structure
eps "Power system qualification" task 12wd from 2027-03-22
bus-test "Bus functional test" task 10wd after eps, avionics +2wd
cdr "Critical design review" gate 2027-05-07 after avionics.start
optics "Imager optics alignment" task 18wd from 2027-03-08
detector "Detector calibration" task 10wd after optics +1wd
payload-tvac "Payload thermal-vacuum" task 8d after detector
payload-delivery "Payload delivered" gate 2027-07-02 after payload-tvac +2wd
launch-contract "Launch services confirmed" gate 2027-04-16
shipment "Ship to range" task 4wd after psr +2wd        # forward reference
campaign "Launch campaign" task 15wd calendar range after shipment +1wd in range
spacecraft-ait "Spacecraft AIT" group
  integration "Spacecraft integration" task 15wd after bus-test +1wd, payload-delivery +1wd
  vibration "Vibration and shock" task 5wd after integration +1wd
  tvac "System thermal-vacuum" task 14d after vibration +2wd
  emc "EMC and RF compatibility" task 5wd end <= 2027-09-08 after tvac +1wd
  psr "Pre-ship review" gate 2027-09-10 after emc
ground-segment "Ground segment readiness" group
  mcs "Mission control software" task 45wd from 2027-03-08
  station "Ground station upgrade" task 30wd from 2027-04-19
  comms-test "End-to-end link test" task 5wd after mcs, station
  rehearsals "Operations rehearsals" task 10wd from 2027-08-30 after comms-test
mission-closeout "Mission closeout" group
  frr "Flight readiness review" gate 2027-10-15 after campaign
  launch "Launch window opens" gate 2027-10-22 after frr +5d, rehearsals
  leop "LEOP and commissioning" task 21d after launch
  first-light "First light" gate 2027-11-19 after leop +5d
```

The minimal starter, terse:

```text
project my-first-plan "My first plan"
design "Design" task 2026-10-01..2026-10-31
build "Build" task 2026-11-03..2026-12-15
release "Release" gate 2026-12-18
```

## 4. Mapping: every construct to exactly one Project construct

The mapping table and the six normalisations (N1-N6: single-calendar default, default endpoints, omitted lag as `0d`,
relation ids, document order, dropped `+`) are normative in [Spec 65](../specification/65-terse-plan-syntax.md)
section 4.

The compiler emits no `entities`, `annotations`, `scenarios`, `extensions`, `fields`, `wbsCode`, `deadline`,
`plannedProgress`, `attachesTo` or `link`, and never emits an empty section.

## 5. What the syntax cannot say, and how the two compose

### 5.1 Shipped rule: hand-off, not merge

`chrona compile plan.chrona -o project.yaml` writes a Project. From that moment `project.yaml` is the
authority and the terse file is retired; nothing regenerates it. Two guards make that rule hold in practice:

- `-o` refuses to overwrite an existing file (`E_TERSE_OUTPUT_EXISTS`, D9). A re-compile cannot silently
  erase hand edits; deleting the file first is the explicit act.
- The output starts with one fixed comment, `# generated by chrona compile (terse 0.1); once edited, this
  file is the authority`, so a reader of the YAML knows its origin without a second authority claiming it.

Honest limit: after the hand-off a plan can no longer be edited in terse form. For the first-draft use case
that is the point; for a plan that keeps changing and also needs `fields` it is a real cost, which is why 5.2
exists.

### 5.2 Specified now, built only on the lead's go (D2): add-only overlay

`chrona compile plan.chrona --with extras.yaml` merges a Project-shaped YAML into the compile result under a
rule that keeps exactly one owner per property:

- `entities`, `annotations`, `scenarios`, `extensions`: owned wholly by the overlay (the compiler never emits
  them).
- `objects.ID`: `ID` must already exist in the terse plan (`E_TERSE_OVERLAY_UNKNOWN_OBJECT`); the overlay
  may add only `fields`, `link`, `deadline`, `plannedProgress`, `attachesTo`, `wbsCode`; any key the compiler
  emitted is `E_TERSE_OVERLAY_CONFLICT` (never overwrite).
- `calendars.C`: may add keys the compiler did not emit (`fiscalStartMonth`).
- `relations`: appended after the compiler's, each with an explicit unique `id`; a colliding id is a conflict.
- No other key is accepted. The result is validated as one Project.

Recommendation: do not build it in v0.1. Costs: positions for overlay errors need YAML source marks, two
files now co-own one object, diagnostics need two source maps, and `render` would need a flag it otherwise does
not have. Build it only if the hand-off proves insufficient in real use (the checkpoint in the implementation
plan). Option B (inline `key=value` string fields) is the cheaper alternative if the evidence says only
`fields` is missed; it would add one clause (`owner=bus`) mapping to `fields`, strings only.

### 5.3 The ledger: the grammar cannot drift silently

A unit test walks `schemas/project-v0.7.schema.yaml` and requires every authorable property path under
`project`, `calendar`, `object`, `schedule` (all four forms), `constraints`, `relation` and `endpointRef` to be
classified in one table in the compiler package as either **mapped** (to a named terse construct) or
**yaml-only** (with a one-line reason from 2.3). A property added to the schema (Spec 56 section 3.2 allows
additive in-place additions) fails the test until someone decides, which is the cheap form of "do not become a
second authority": the decision is forced, not the construct.

## 6. Identity

### 6.1 Object ids

A terse `NAME` **is** the Project object id, verbatim. It must match `slug` (`[a-z][a-z0-9-]*`):

- The Project schema puts no pattern on object keys, but ids travel: Scene row ids, Actual Set
  `projectObjectId`, View selectors, command targets, and (for Actual Set ids) adapter file names. `slug` is a
  subset of the Store address segment alphabet `[A-Za-z0-9._-]` (`src/chrona/core/store_address.py`), contains
  no `.` (the endpoint separator) and no case folding hazard, so a terse id is valid in every place an id is
  used. Spec 02 asks ids to stay stable across title changes: the title is a separate quoted string.
- A name that is not a slug is `E_TERSE_NAME_INVALID` with a *suggested* conforming name in the hint
  (lower-cased, runs of other characters turned into `-`); the suggestion is never applied.
- Unicode and upper-case ids remain possible in YAML (the `identifier` part allows them) and are simply out of
  the grammar. A Japanese title is fine (`"仕様策定"`), only the name is ASCII.
- The project id is a `slug` too, except that it may also be written the way the issue sketch writes it,
  `project HALCYON-1`, because Project ids have no pattern: any non-whitespace word of the `identifier`
  alphabet is accepted verbatim, with no derivation (`HALCYON-1` stays `HALCYON-1`; `halcyon-1 "HALCYON-1"` is
  the form the corpus uses).

### 6.2 Relation ids

Each dependency gets the id `FROM-TO` (the two object names), chosen in statement order. If that id is
already in use (the same pair twice, or two pairs that concatenate to the same text, such as `a`->`b-2` and
`a`->`b` twice), the compiler appends `-2`, `-3`, ... until the id is free in the set of ids already assigned.
It is a pure function of the file and fully deterministic. Relation ids matter only to YAML scenarios
(`relations.remove`) and the scheduler's `E_FIXED_TARGET_VIOLATION` pointer; renaming an object renames its
relation ids, which is why scenarios are written after the hand-off, not before.

### 6.3 Collisions

Duplicate object name or duplicate calendar name: `E_TERSE_NAME_DUPLICATE`, positioned at the second
occurrence, naming the line of the first. Object and calendar names live in separate namespaces. The compiler
never renames to resolve a collision.

### 6.4 Renames and one-way compilation

Compilation is stateless. Renaming a terse name changes the id; every Actual Set row, scenario or View
selector that used the old id now refers to nothing, exactly as renaming a YAML key would, and the render
reports it in the usual way. There is no id stability layer, no id map file and no title-derived id (D6:
rejected because the derivation algorithm would become a frozen part of the contract, and an agent that
rewords a title would silently rename the object). The compiler is **one-way by design**: there is no
`decompile`, no YAML-to-terse, no "update the terse file from the YAML". The only artefact that carries
meaning after compile is the Project.

## 7. Diagnostics

### 7.1 Shape

The same JSON shape as every other command, extended additively:

```json
{"status": "rejected", "diagnostics": [{
  "code": "E_TERSE_AMOUNT_INVALID", "severity": "error", "component": "terse",
  "sourceRef": "/", "revisionRefs": [],
  "message": "'20' has no unit; write 20d (calendar days), 20w (weeks) or 20wd (working days)",
  "source": "plan.chrona",
  "sourceRange": {"line": 6, "column": 33, "endLine": 6, "endColumn": 35},
  "hint": "write 20d for calendar days; 20wd needs a `calendar` statement"}]}
```

`code`, `severity`, `component` (`terse`), `sourceRef`, `revisionRefs`, `message` are today's fields.
`sourceRef` is the JSON pointer into the *compiled* Project when the finding has one (for example
`/objects/avionics/schedule`) and `/` otherwise. New, only on terse diagnostics: `source` (the path as the
author gave it, `-` for stdin), `sourceRange` (an object `{line, column, endLine, endColumn}`, 1-based code
points, end exclusive; `endLine` equals `line` for every token the compiler reports), and an
optional `hint` (one actionable sentence). `sourceRange` is the additive field the parallel agent-interface design
([#142 design](issue-142-agent-interface-design-2026-10-01.md), D2.5 and D1.5) reserves under that name; using one object keeps the CLI,
the skill and an MCP result on one shape. Codes are stable identifiers; messages and hints may be
improved without a version change. No terse diagnostic is a bare code (#371): each has a message.

In code, `chrona.terse.diagnostics.TerseDiagnostic` subclasses `core.diagnostics.Diagnostic`, so Core's own
`id/message/path` stay the shared base and a Core finding can be positioned without a second model.

### 7.2 Stream rule

Exit code 1 for rejected input, 2 for command syntax, as today. Diagnostics JSON goes to the stream that
does **not** carry the artefact: stdout when the Project goes to `-o FILE` (matching every other command),
stderr when the Project would go to stdout. This is what makes
`chrona compile plan.chrona > project.yaml` safe: on failure the redirected file is empty and the JSON is on
the terminal, never inside `project.yaml`. (D8.)

### 7.3 Catalogue of compiler-owned codes (stable)

Lexical: `E_TERSE_ENCODING`, `E_TERSE_TAB`, `E_TERSE_CONTROL_CHARACTER`, `E_TERSE_STRING_UNTERMINATED`,
`E_TERSE_STRING_ESCAPE`, `E_TERSE_TITLE_EMPTY`.
Structure: `E_TERSE_INDENT`, `E_TERSE_CHILDREN_NOT_ALLOWED`, `E_TERSE_TOKEN_UNEXPECTED`,
`E_TERSE_LINE_INCOMPLETE`, `E_TERSE_TITLE_UNQUOTED`, `E_TERSE_PROJECT_REQUIRED`, `E_TERSE_DIRECTIVE_ORDER`,
`E_TERSE_VERSION_UNSUPPORTED`, `E_TERSE_UNSUPPORTED` (a recognised construct this compiler release does not
implement yet; also the reserved word for future forms), `E_TERSE_TOO_MANY_ERRORS`.
Names and references: `E_TERSE_NAME_INVALID`, `E_TERSE_NAME_RESERVED`, `E_TERSE_NAME_DUPLICATE`,
`E_TERSE_KIND_UNKNOWN`, `E_TERSE_REFERENCE_UNKNOWN`, `E_TERSE_CALENDAR_UNKNOWN`.
Values: `E_TERSE_DATE_INVALID`, `E_TERSE_AMOUNT_INVALID`, `E_TERSE_LAG_INVALID`, `E_TERSE_DAYS_INVALID`,
`E_TERSE_SCHEDULE_REQUIRED`, `E_TERSE_CLAUSE_DUPLICATE`.
CLI/IO: `E_TERSE_OUTPUT_EXISTS`, `E_TERSE_INPUT_IO`.
Defect: `E_TERSE_COMPILER_DEFECT` (the emitted Project failed *structural* validation; exit 2; a property test
asserts it is unreachable, section 13).
Overlay (reserved, only if 5.2 is built): `E_TERSE_OVERLAY_CONFLICT`, `E_TERSE_OVERLAY_UNKNOWN_OBJECT`.

Semantic findings keep their **Core code** and gain a position; the compiler does not duplicate Core rules:
`E_INVALID_SPAN`, `E_CALENDAR_REQUIRED`, `E_ROLLUP_EMPTY`, `E_ENDPOINT_MODE_MISMATCH`,
`E_FIXED_TARGET_VIOLATION`, `E_UNSUPPORTED_CYCLE`, `E_CONTRADICTORY_BOUNDS`, `E_NON_WORKING_ANCHOR`,
`E_UNSATISFIABLE_DEPENDENCIES` and every other Core/scheduler code.

### 7.4 The ten most likely mistakes, and the error each gets

| # | Mistake | Code and position | Message and hint |
| --- | --- | --- | --- |
| 1 | Multi-word title without quotes: `design Build the thing task 5d` | `E_TERSE_TITLE_UNQUOTED` at `Build` | "a title with spaces needs quotes" / `design "Build the thing" task 5d` (chosen when a later token on the line is a kind word) |
| 2 | Misspelt or missing kind: `design tsak 5d` | `E_TERSE_KIND_UNKNOWN` at `tsak` | "unknown kind 'tsak'; known: task, gate, group" / "did you mean `task`?" (nearest by edit distance, ties by declaration order) |
| 3 | Kind first, Mermaid style: `task design 5d` | `E_TERSE_NAME_RESERVED` at `task` | "`task` is a kind, not a name; write the name first" / `design task 5d` |
| 4 | Name not a slug: `Build_Phase task 5d` | `E_TERSE_NAME_INVALID` at the name | "names are lower-case letters, digits and hyphens, starting with a letter" / "try `build-phase`" (a `version:` line adds: "this looks like Project YAML; compile reads terse plans") |
| 5 | Duplicate name | `E_TERSE_NAME_DUPLICATE` at the second | "'design' is already defined on line 4" |
| 6 | `after` names an unknown object (typo; forward references are fine) | `E_TERSE_REFERENCE_UNKNOWN` at the word | "no object named 'structur'" / "did you mean `structure`?" |
| 7 | Duration without or with a wrong unit: `20`, `3 days`, `2mo`, `1.5w` | `E_TERSE_AMOUNT_INVALID` at the word | "'20' has no unit; write 20d, 20w or 20wd" (`3 days` also points at the word after) |
| 8 | Date not ISO or not real: `2027-3-5`, `05/03/2027`, `2027-02-30` | `E_TERSE_DATE_INVALID` at the word | "write YYYY-MM-DD with zero padding" / "2027-02-30 is not a calendar date" |
| 9 | Gate or task with no schedule: `pdr gate` | `E_TERSE_SCHEDULE_REQUIRED` at end of line | "a gate needs a date (`pdr gate 2027-03-05`); a task needs a duration (`5d`) or `D..D`" |
| 10 | Working days with no calendar: `a task 5wd` | Core `E_CALENDAR_REQUIRED`, mapped to the object (or the amount word) | "working-day amounts need a calendar" / "add `calendar standard mon-fri` and, with one calendar, nothing else" |

Also precise, not in the ten: a tab (`E_TERSE_TAB` at the tab), an odd indent (`E_TERSE_INDENT`), a lag with a
space (`+ 1wd`, `E_TERSE_LAG_INVALID` hint "attach the sign: `+1wd`"), spaces around `..`
(`E_TERSE_TOKEN_UNEXPECTED` "no spaces around `..`"), an empty span `2026-10-01..2026-10-01` (Core
`E_INVALID_SPAN`, hint "the end date is exclusive"), a dependency cycle (Core `E_UNSUPPORTED_CYCLE`, mapped).

### 7.5 A compile error never emits a partial Project

The compiler returns one value: `CompileResult(project, diagnostics, source_map)`, where `project` is `None`
whenever `diagnostics` contains an error. The CLI writes the output file only from a complete successful
result, to a temporary sibling and then an atomic rename; on failure no file is created or touched and
stdout (in file mode) carries only the rejection JSON. The compiler collects errors per line (a bad statement
does not stop the next line; the name on a bad line is still registered so later references do not cascade),
ordered by line then column, capped at 50 (`E_TERSE_TOO_MANY_ERRORS` follows the 50th). An agent therefore
gets every fixable problem in one round trip.

### 7.6 Positioning Core and scheduler findings

The compiler returns a **source map** from JSON pointer to the best source span: `/objects/NAME` to the name
token, `/objects/NAME/schedule` and `.../amount` to the schedule words, `/objects/NAME/calendar` to the
clause, `/calendars/C` to the calendar line, `/relations/N` and `/relations/N/lag`, `/relations/N/from/object`
to the dep item and its parts. Relations are keyed **both** by index (what `validate_project` reports) and by
id (what the scheduler reports for `E_FIXED_TARGET_VIOLATION`, which writes `/relations/<id>`). A diagnostic
whose pointer has no entry falls back to its nearest ancestor pointer. The use case
`usecases.terse_compile` applies the map; the CLI's single rejection path (`_reject`) and its closure
failure path accept an optional map so a scheduler error raised later by `render` is positioned too. Hints
for Core codes live in a small table in the use case (keyed by Core code), not in Core.

## 8. Determinism and the emitter

The compile result is a pure function of the source bytes and the grammar version: no clock, locale,
environment, host path, hash seed or random source. Nothing about the source (not its path, not a hash) is
embedded in the output beyond the fixed header comment.

The YAML is written by a **small hand-written emitter**, not `yaml.safe_dump`, so the bytes cannot move with a
PyYAML release (CI runs the newest Python and three operating systems). Format: LF only, UTF-8 without BOM,
final newline, two-space block mappings, flow-style one-line `schedule` and relation entries as in the corpus,
fixed key order (`version`, `project`, `calendars`, `objects`, `relations`; per object `type`, `title`,
`parent`, `calendar`, `schedule`; per relation `id`, `type`, `from`, `to`, `lag`). Dates are always single
quoted (PyYAML would otherwise load an unquoted ISO date as a date object). Scalars are plain only when they
match `[A-Za-z][A-Za-z0-9 _-]*` (no trailing space) and are not a YAML 1.1 special word; everything else,
including every title with other characters, is single quoted with `''` escaping and written literally in
UTF-8. This matters for **keys** too: `safe_load` turns an object named `on`, `no`, `yes`, `off`, `true`,
`false` or `null` into a boolean or `None` key (verified against the repository's own `safe_load`), so such a
name is emitted as `'on':`. The contract the emitter must hold is exactly: `safe_load(emitted)` equals the
in-memory Project, for every input; a test enforces it on every fixture and every fuzz case.

## 9. CLI and layering

### 9.1 Package and dependency (D5)

A new package `src/chrona/terse/` (modules: `lexer`, `parser`, `compiler`, `emitter`, `diagnostics`,
`ledger`) imports only `chrona.core` (the Diagnostic base). It has no I/O: it takes `str`, returns a result.
`tools/check_import_direction.py` gains two rows: `"terse": {"core"}` and `terse` added to the `usecases`
set, with this issue as the stated reason (the tool's own rule: an edge is a deliberate edit). `app` reaches it
only through `usecases.terse_compile`; presentation, scheduling, storage, operational and release cannot
import it because the table does not allow it, which is the machine-checked statement of "a Context
references YAML always". The package is not `core` because the kernel owns Project meaning, not one of its
surface syntaxes; it is not `usecases` because it is a leaf with no pipeline.

No new dependency. A parser library would add a package to `dependencies` (today `PyYAML`, `jsonschema`,
`fonttools`) and the generic error positions of table-driven parsers are worse than hand-written messages
for a 25-production line grammar. Recommendation: hand-written. If the lead disagrees the alternative is
`lark` (pure Python, MIT) as an ordinary runtime dependency; the consequence is a wheel-size and supply-chain
line item and a second place where messages must be reworked into the catalogue.

### 9.2 Dispatch for the draft render (D4)

Slice 1 ships only `chrona compile`. Slice 3 adds suffix dispatch (`.chrona`) in the CLI adapter for the
three commands that take a raw Draft Project: `render`, `validate`, `schedule`.

- `validate` and `schedule` already load through one function (`_load_primary_project`); the dispatch is one
  branch there.
- `render` hands `resolve_draft_render` a `Path`. The adapter compiles `.chrona` through the use case, writes
  the emitted bytes into a `tempfile.TemporaryDirectory` as `project.yaml`, passes that path, and cleans up
  in `finally`. This is the pattern `--preset <builtin id>` already uses (`_resolve_preset_argument`).
  Consequence: the draft closure's project identity is the hash of the compile output, so rendering
  `plan.chrona` is byte-identical to compiling then rendering the YAML, by construction; a test asserts it.
- Rejected alternative: teach `resolve_draft_render` (presentation layer) to accept an in-memory source.
  It would pull either terse knowledge into presentation (forbidden by the import table) or a new
  in-memory-source type into the closure ingress for one caller.
- Alternative the lead may prefer (D4): do not dispatch at all; users pipe
  `chrona compile plan.chrona -o p.yaml && chrona render p.yaml -o plan.svg`. Consequence: simpler, one fewer
  surface, but the "first line to type" becomes two commands and diagnostics from `render` are not positioned.
  Recommendation: dispatch, because positioned scheduler errors on the file the author edits are most of the value.

### 9.3 Where it is not accepted

Only `compile`, `render`, `validate` and `schedule` take a path that may be terse. `render-review`,
`render-review-gallery`, `materialize`, `review`, `baseline-*`, `command-*`, `actual-*`, `workspace`,
`render-workspace` and every Store or snapshot read take references to immutable YAML; `storage` and
`operational` cannot import `terse`, so there is no code path by which a `.chrona` file becomes a closure
member, a snapshot or a baseline. `--snapshot-reference` with a `.chrona` path is read as YAML and fails, because no dispatch exists there.
A test names each command.

### 9.4 Markdown-fence form

The syntax is fence-safe: no statement can begin with three backticks or tildes, the file needs no leading
blank line, and indentation is spaces. The fence info string is `chrona`:

````text
```chrona
project my-first-plan "My first plan"
design "Design" task 2026-10-01..2026-10-31
```
````

The CLI does not read Markdown. The doc-check (section 13) extracts and compiles ```` ```chrona ```` fences in
README and guides. Note this forces a change in `tools/check_documented_commands.py`: a terse object named
`chrona` begins a line with `chrona`, which today's command scanner would treat as a CLI invocation, so fences
with the info string `chrona` must be excluded from command scanning and handed to the terse check instead.

### 9.5 File extension (D3)

Recommendation: `.chrona` (the issue's spelling). Consequence to accept: it shares a visual stem with the
`.chrona/` Store directory (`.chrona/store.yaml`); they never collide (a directory named `.chrona` versus a
file whose name ends in `.chrona`), and dispatch tests the suffix of the file argument only. Alternatives
`.chr` and `.plan` avoid the visual clash but lose the product name and `.plan` is generic. Editors will not
highlight it either way; a TextMate grammar is out of scope.

### 9.6 CLI contract

```text
chrona compile PLAN [--output FILE | -o FILE]
```

`PLAN` is a path or `-` (stdin). Without `-o` the Project YAML goes to stdout. `-o` writes atomically and
refuses an existing file (D9: init and `--emit-scene` already refuse to replace; no `--force` in v0.1).
Exit 0 success; 1 rejected (diagnostics, section 7); 2 command-syntax or input I/O (`E_TERSE_INPUT_IO`,
`E_COMMAND_SYNTAX`). Success writes nothing to stderr. `compile` does not require a `.chrona` suffix (the
author named the file explicitly) and does not validate beyond what section 7 describes. Every option appears
in a guide, because the doc-check requires both commands and options to be documented.

## 10. Specification home (D10)

Slice 1 adds `docs/specification/65-terse-plan-syntax.md` (Status: Proposed, then Stable with the release),
owning: the grammar (section 3 of this design), the mapping table (4), the id rules (6.1, 6.2), the
catalogue of codes and the diagnostic fields (7), the determinism contract (8). It lists itself in
`docs/specification/README.md` and adds one cross-reference sentence to Spec 05 section 3
("a Project may be compiled from the terse plan syntax of Spec 65; the Project remains the authority") and to
Spec 51 (section 11 below). No schema changes: the Project schema is untouched, and Spec 56 section 3.2 is
unaffected. (Number 65 is the next free; claim it in the slice-1 PR and check open PRs first.)

## 11. Neighbours: Spec 51 and #142

**Spec 51 (guided authoring workspace).** The repository already has a compact source: a YAML
`authoring-workspace` with tasks and presentation binding, normalised by
`presentation/model/authoring.py`, which calls itself "the sole reader of guided syntax". The terse plan is a
different thing with a different owner: a text syntax for **the Project only**, compiled at the adapter edge,
with no presentation binding, no Actuals, and richer scheduling (dependencies, calendars, groups). It does not
read, produce or extend `authoring-workspace`, and neither normaliser calls the other. The risk is user
confusion between two compact sources; the guide says in one sentence which is which, and Spec 65 states
that downstream components never read terse text (the same promise Spec 51 makes for its own syntax).

**#142 (agent skill and MCP, designed in parallel).** What it may rely on, all frozen by Spec 65: the grammar
and its one-page summary; the code catalogue; the diagnostic fields (`sourceRange`, `hint`,
`source`); `chrona compile -` for stdin; exit codes; the all-errors-in-one-pass behaviour; the stream rule
(7.2); that `compile` never partially emits; the hand-off rule (the skill should tell an agent to compile and
then edit YAML when it needs fields, scenarios or annotations). That design takes `project` as an opaque path and promises not to describe `chrona compile` before it exists; the
hand-over is slice 4, after which one added paragraph and one reference file in the skill are enough. What this design does not decide: the skill's
text, any MCP tool, or whether an MCP `compile_plan` returns positions as structured data (it can reuse the
use case result directly, which is why the position data lives in the use case and not only in the CLI).

## 12. Non-goals, confirmed

- Not a replacement for the Project format, and not accepted where an immutable closure is pinned (9.3).
- No presentation in the syntax: no view, theme, scheme, layout, colour, icon or label placement words.
- No scheduling in the compiler: it never computes a date, a float, a critical path or a cycle; it needs only
  each object's schedule form to resolve default endpoints.
- No second authority: no YAML-to-terse, no regeneration, no id map file, no embedded source hash, no
  overlay in v0.1, no semantic rule duplicated from Core.
- No Markdown reader in the CLI, no includes, no variables, no loops, no macros, no scenario syntax.
- No new dependency.

## 13. Proof strategy

1. **Golden pairs** (`tests/fixtures/terse/`): `*.chrona` next to a hand-written expected `*.project.yaml`.
   The compiler output must equal the expected bytes; the expected YAML must pass `validate_project`; schedule
   placements and critical set of the compiled and the expected Projects must be equal. Fixtures: the minimal
   starter; the issue sketch; groups; anchors and bounds; both calendar forms; forward references;
   `on`/`no`/`null` names.
2. **HALCYON equivalence.** The 32-line HALCYON core compiles to a Project that validates and schedules
   identically (placements, critical set, edges modulo relation ids) to `examples/halcyon-1/project.yaml`.
   Spike result: 29 placements, 24 edges and the critical set equal. A copy of the hand-written YAML is the
   synthetic twin in the PR path; the comparison with the live example is one test marked `corpus` (AGENTS.md:
   only together with the twin; corpus output is evidence, not an oracle, so a corpus edit never gets "fixed"
   by touching the fixture).
3. **Byte stability.** Compile twice, compile in a subprocess under different `PYTHONHASHSEED` and `LC_ALL`,
   and compare with the committed golden bytes; the three-OS matrix runs it, and `*.chrona` and the golden
   YAML are `text eol=lf` in `.gitattributes`.
4. **Round trip.** `safe_load(emitted)` equals the in-memory Project on every fixture and fuzz case.
5. **Positions, as a property.** No new dependency (the repository has no `hypothesis`): a seeded
   (`random.Random(148)`), deterministic mutation fuzz over the fixtures (delete, insert, swap, truncate
   characters and tokens, thousands of cases) asserting: (a) the compiler never raises; (b) if any
   diagnostic exists, `project is None`; (c) every diagnostic has `1 <= line <= number_of_lines + 1` and
   `1 <= column <= len(line) + 1` and `endColumn > column` (all inside `sourceRange`); (d) a successful compile always passes
   `validate_project` (this makes `E_TERSE_COMPILER_DEFECT` unreachable); (e) a second compile is byte-equal.
6. **Catalogue completeness.** One negative fixture per `E_TERSE_*` code, with an expected-diagnostics JSON
   (code, sourceRange, hint present); a test fails if a code in the catalogue has no fixture or a
   fixture names an unknown code. The ten mistakes of 7.4 are literal fixtures.
7. **Ledger test** (5.3).
8. **Layering.** `tools/check_import_direction.py` passes with the new rows; a test asserts `terse` imports
   nothing but `core`, and a negative test shows `storage` importing `terse` is flagged.
9. **Draft equivalence** (slice 3): rendering `plan.chrona` is byte-identical to compiling then rendering the
   YAML under identical flags, for SVG; positioned scheduler errors for a gate before its dependency, a
   cycle, and contradictory bounds.
10. **Docs.** Guides use ```` ```chrona ```` fences; `tools/check_documented_commands.py` compiles each one
    (and, with an expected-output marker, compares the emitted YAML to the adjacent ```` ```yaml ```` fence, so
    the mapping table in the guide is executable). Markers: the existing `skip: reason`, plus
    `expect-error: CODE` for a deliberately wrong example and `expect-yaml: next` for a compile-result pair.
    `chrona compile` and each of its options are documented, because the surface check requires it, and
    `docs/guides/cli-reference.md` is regenerated.
11. **Agent check** (go/no-go, implementation plan checkpoint): give an agent only the one-page grammar card and
    three prompts (a small plan, a plan with groups and calendars, a HALCYON-sized one); record how many
    compile attempts each needs. This is evidence for the issue, not a CI test.

## 14. Decisions for the lead

| ID | Decision | Recommendation | Consequence of the recommendation |
| --- | --- | --- | --- |
| D1 | Scope | Schedule-and-structure only (2.3) | `fields`, WBS, progress, deadline, links, annotations, scenarios need YAML; 5 of 6 example Projects leave the syntax at the point they need View grouping |
| D2 | Composition | Hand-off now; overlay (5.2) specified, built only on evidence; inline fields as the cheaper fallback | One authority at all times; plans that keep changing and need `fields` pay the hand-off |
| D3 | Extension | `.chrona`, fence `chrona` | Visual stem shared with the `.chrona/` directory; no collision in code |
| D4 | Draft dispatch | Suffix dispatch in the CLI adapter for `render`/`validate`/`schedule` via a temp file | Presentation untouched; render of terse equals render of its compile output; one more adapter branch |
| D5 | Dependency | None; hand-written lexer, parser, emitter | About 600 lines to own; best error messages; no wheel change |
| D6 | Ids | Explicit slug names only, no derived ids | Agents must name every object; a title edit never renames an object |
| D7 | Kinds | Closed: `task`, `gate`, `group` | `milestone`/`phase` need YAML or a one-line widening |
| D8 | Diagnostics | Additive fields `source`, `sourceRange`, `hint`; JSON to the stream not carrying the artefact | Redirect-safe `compile > project.yaml`; a rule agents must learn (one sentence) |
| D9 | Overwrite | `-o` refuses an existing file | No silent loss of hand edits; user deletes first |
| D10 | Spec home | New Spec 65 plus one-line cross-references in Spec 05 and 51 | One normative home; design section 3 becomes a pointer |
| D11 | Checkpoint | Go/no-go after slice 1 on the agent check (13.11) and a written bytes-and-retries record | Slices 2-4 are not started on momentum |
