# Terse Plan Syntax

**Status:** Proposed; implemented by `chrona compile` (#148, slice 1), the draft dispatch of section 7.1 (slice 3), the documentation check of section 10 (slice 4), the derived gate of S3 and section 4 (#788, slice 2) and the `deadline` clause of S3 and section 4 (#822, I822-1).
**Owns:** the grammar of the terse plan (`terse 0.1`), its mapping to a `timeline/v0.7` Project, the id rules for
compiled objects and relations, the compiler diagnostic fields and codes, the stream and exit-code rules of
`chrona compile`, and the determinism contract of the compiler's YAML.
**Does not own:** Project meaning (Spec 05 and Core validation own every semantic rule), scheduling (Spec 04),
presentation (the draft render consumes the compiled Project unchanged), the guided authoring workspace (Spec 51), or
any agent skill that teaches the syntax.
**One-page summary for authors and agents:** [`docs/guides/terse-plan.md`](../guides/terse-plan.md).
Design rationale, measurements and alternatives:
[`docs/design/issue-148-terse-draft-syntax-design-2026-10-01.md`](../design/issue-148-terse-draft-syntax-design-2026-10-01.md).

## 1. Purpose and boundary

The terse plan is a small line-oriented text syntax for the first draft of a plan: identity, title, kind,
hierarchy, schedule, constraints, calendars, dependencies and a deadline. It **compiles to** a Project; it never replaces
one. The compiler is a pure function from text to either a Project (as deterministic YAML bytes) or a list of
positioned diagnostics. It does not read files, schedule, or know about presentation, and it repeats no Core
rule: Core validation is the only owner of Project meaning, and a plan the compiler accepts is validated by Core
before any YAML is produced.

Compilation is one-way. `chrona compile plan.chrona -o project.yaml` writes a Project; from then on the YAML is
the only authority and the terse file is retired. There is no decompiler, no regeneration, no id map and no
embedded source hash. Contexts, snapshots, baselines and Stores never see terse text: `chrona.terse` imports
only `chrona.core`, and only `chrona.usecases` may import it.

A Project may be compiled from this syntax; the Project remains the authority (Spec 05 section 3). The syntax is
a different thing from the guided authoring workspace of Spec 51: that is a YAML source with presentation
binding and Actuals; this is a text syntax for the Project only. Neither normaliser calls the other.

### 1.1 Scope rule

A construct belongs in the grammar if and only if (1) it determines identity, hierarchy, dates or dependencies,
or is the title of the thing it names, or is a date the plan states about the thing it names (a deadline, which
determines no placement); (2) its value is a scalar, a date, an amount or a short list, never a
free-form map, prose or a reference to another top-level section; and (3) it has one unambiguous one-line
spelling that maps to exactly one Project construct. Everything else (`fields`, `entities`, `annotations`,
`scenarios`, `extensions`, `link`, `wbsCode`, `plannedProgress`, `attachesTo`, `fiscalStartMonth`,
endpoints other than `start`/`at` on the successor, `mo`/`y` lags) stays in YAML.

`chrona.terse.ledger.LEDGER` classifies every authorable property path of `schemas/project-v0.7.schema.yaml`
(and every top-level section) as `mapped` or `yaml-only` with a reason. A test walks the live schema and fails
until a newly added property is classified, so the grammar cannot grow silently. Adding a property to the schema
forces a decision; it does not force a construct.

## 2. Lexical rules

- **L1 Encoding.** UTF-8, optional BOM (ignored). Invalid bytes: `E_TERSE_ENCODING`, positioned at the first bad byte.
- **L2 Lines.** LF or CRLF separate lines; a final newline is optional; a lone CR is `E_TERSE_CONTROL_CHARACTER`.
  Lines and columns are 1-based; a column counts Unicode code points of the line (BOM excluded); `endColumn` is
  exclusive.
- **L3 Characters.** Control characters (U+0000-U+001F, U+007F) are rejected everywhere, including strings and
  comments: a tab is `E_TERSE_TAB`, any other is `E_TERSE_CONTROL_CHARACTER`. The only token separator is
  U+0020; any other whitespace (for example U+00A0) is an ordinary word character, and a diagnostic quoting such
  a word names its code point.
- **L4 Indentation.** Leading spaces only, an even count (`E_TERSE_INDENT`); meaning in section 3.2.
- **L5 Comments.** `#` starts a comment when it is the first character of a token (line start or after a space)
  and outside a string; it runs to the end of the line. `a#b` is one word. A blank or comment-only line is ignored.
- **L6 Strings.** `"` ... `"` with the escapes `\"` and `\\` only (`E_TERSE_STRING_ESCAPE`), no raw newline
  (`E_TERSE_STRING_UNTERMINATED` at the opening quote), any other non-control Unicode allowed. A string must be
  preceded and followed by a space or comma. An empty title is `E_TERSE_TITLE_EMPTY`. A string is the only way to
  write a space, a `#`, a comma or non-ASCII text.
- **L7 Words and commas.** A word is a maximal run of characters other than space, `"` and `,`. `,` is its own
  token, so `after a,b` and `after a, b` are the same.
- **L8 Case.** Keywords are lower case and case-sensitive.
- **L9 Reserved words.** `terse project calendar task gate group after from until in except work start end at`
  are never names (`E_TERSE_NAME_RESERVED`). The set is larger than version 0.1 needs so that later versions can
  add forms without renaming anyone. `deadline` is deliberately not in the set: it is a contextual keyword (S10).

## 3. Grammar (terse 0.1)

### 3.1 Statements

```text
file        = { line } ;                     (blank and comment lines ignored)
line        = indent statement ;
statement   = terse | project | calendar | object ;

terse       = "terse" VERSION ;              (optional; if present it is the first statement; VERSION = 0.1)
project     = "project" ID [ STRING ] [ "calendar" CAL ] ;
calendar    = "calendar" CAL days [ off ] [ on ] | "calendar" CAL days [ on ] [ off ] ;
days        = dayitem { "," dayitem } ;      (dayitem = DAY | DAY "-" DAY, e.g. mon-fri, mon-wed,fri)
off         = "except" date { [ "," ] date } ;
on          = "work"   date { [ "," ] date } ;

object      = NAME [ STRING ] KIND [ schedule ] [ "calendar" CAL ] [ after ] [ deadline ] ;
schedule    = DATE                           (fixed point)
            | DATE ".." DATE                 (fixed span, no spaces around "..", end exclusive)
            | AMOUNT [ anchor ] { bound }    (scheduled span)
            | pointbound { pointbound }      (derived point: a gate, with an after clause)
            | (nothing)                      (derived point: a gate, with an after clause) ;
anchor      = "from" DATE | "until" DATE ;
bound       = ( "start" | "end" ) ( ">=" | "<=" ) DATE ;   (each of the four at most once)
pointbound  = "at" ( ">=" | "<=" ) DATE ;                  (each of the two at most once)
after       = "after" dep { "," dep } ;
deadline    = "deadline" DATE ;                (the last clause of an object line, every kind; a promise, never a bound)
dep         = REF [ LAG [ "in" CAL ] ] ;
REF         = NAME [ "." ENDPOINT ] ;        (ENDPOINT = start | end | at)

NAME, CAL   : slug  = [a-z][a-z0-9-]*
ID          : any word that is not a reserved word (a slug such as halcyon-1, or HALCYON-1)
KIND        : task | gate | group
DATE        : [0-9]{4}-[0-9]{2}-[0-9]{2}, and a real calendar date
AMOUNT      : [1-9][0-9]*(d|w|wd)
LAG         : [+-]?(0|[1-9][0-9]*)(d|w|wd)   (the sign is attached: "+1wd", never "+ 1wd")
DAY         : mon | tue | wed | thu | fri | sat | sun
```

`NAME` and `CAL` are exactly the `slug` pattern of `schemas/common-v0.1.schema.yaml`; a test asserts the equality.

### 3.2 Semantics

- **S1 Project statement.** Exactly one, before every calendar and object (`E_TERSE_PROJECT_REQUIRED`,
  `E_TERSE_DIRECTIVE_ORDER`). `terse` is optional; absent means 0.1 forever: an incompatible grammar will be a new
  explicit `terse 0.2` that a 0.1 compiler refuses (`E_TERSE_VERSION_UNSUPPORTED`), so a file in git compiles to the
  same Project next quarter.
- **S2 Hierarchy.** Only a `group` has children. A line indented two spaces deeper than the nearest preceding
  `group` is its child; indentation may increase by at most two per line and may drop to any open level. A child
  of a non-group is `E_TERSE_CHILDREN_NOT_ALLOWED`; an indent that matches no open group is `E_TERSE_INDENT`. A
  group takes no schedule, no `calendar` and no `after` (each is `E_TERSE_TOKEN_UNEXPECTED`); it compiles to a
  rollup and may be a predecessor. An empty group is accepted by the compiler and rejected by Core
  (`E_ROLLUP_EMPTY`, positioned at the group line).
- **S3 Schedule requirement.** `task` and `gate` require a schedule (`E_TERSE_SCHEDULE_REQUIRED`). The kind does not
  constrain a form that names a date or a duration (the Project `type` is a free label), so `gate 2027-05-07` is the
  common case, not a rule. One form is the kind's own, the first place the kind selects the form (normalisation N7): a
  `gate` with no schedule words and an `after` clause is a **derived point**, `launch "Launch" gate after qa +2wd`; its
  date is the earliest the relations allow and the scheduler computes it (Spec 04 section 20.4), never the compiler.
  `at >= D` is its floor and `at <= D` its cap; they sit in the schedule slot, before `calendar` and `after`, and each is
  given at most once (`E_TERSE_CLAUSE_DUPLICATE`). `E_TERSE_SCHEDULE_REQUIRED` remains for a `task` with no schedule
  (also when it has an `after` clause: there is no derived span), for a `gate` with neither a date nor `after`, and for a
  `gate` with bounds but no `after` (a floor alone is a fixed date: write `gate DATE`). `at` bounds on anything but a
  schedule-less gate are `E_TERSE_TOKEN_UNEXPECTED` or `E_TERSE_AMOUNT_INVALID`.
- **S4 Spans.** `D1..D2` is half-open like the Project's `fixed-span`: `2026-10-01..2026-10-31` ends before the
  31st. Core owns `start < end` (`E_INVALID_SPAN`).
- **S5 Calendars.** A calendar name is unique among calendars (`E_TERSE_NAME_DUPLICATE`). A day range increases
  within mon..sun and a day may appear once after expansion (`E_TERSE_DAYS_INVALID`). The emitted `working_days`
  order is always mon..sun. A statement carries each of `except` and `work` at most once, in either order, each with
  one or more dates (`E_TERSE_CLAUSE_DUPLICATE`); one date is one exception record; a date range is
  `E_TERSE_UNSUPPORTED`.
- **S6 Default calendar.** `project ... calendar CAL` sets `project.calendar`. If it is omitted and exactly one
  calendar is declared, that calendar is the project default (normalisation N1, the only implicit mapping). With
  two or more calendars and no clause the compiler adds nothing; a working-day amount or lag with no calendar is
  Core's `E_CALENDAR_REQUIRED`, positioned at the amount. An unknown calendar name anywhere is
  `E_TERSE_CALENDAR_UNKNOWN`.
- **S7 Anchors and bounds.** `from D` is `anchor.start`, `until D` is `anchor.end`; at most one anchor; both and the
  bounds are legal only after a duration. Bounds are the inclusive `constraints` minimum/maximum. Whether they
  conflict is the scheduler's (`E_CONTRADICTORY_BOUNDS`), not the compiler's.
- **S8 Order.** Objects are emitted in document order (parent before its children, depth first); relations in
  statement order, then dependency order.
- **S9 References.** Names resolve over the whole file after it is read, so forward references are legal
  (`E_TERSE_REFERENCE_UNKNOWN` for a name defined nowhere). The compiler never computes a date, a cycle or a float.
  A cycle is `E_UNSUPPORTED_CYCLE`, reported by `validate` and `schedule`.
- **S10 Deadline.** `deadline D` is the last clause of an object line, after `calendar` and `after`, on a task, a gate or a
  group (a rollup is judged by its `end`). It is the Project's `deadline` (Spec 05 section 9): a promise the scheduler
  never reads, so it moves no placement and changes no verdict, and `chrona schedule` lists a `W_DEADLINE` for an
  object planned to finish after it (Spec 04 section 10). A second `deadline` is `E_TERSE_CLAUSE_DUPLICATE`, a missing
  date `E_TERSE_LINE_INCOMPLETE`, a date that is not a calendar date `E_TERSE_DATE_INVALID`, a clause before `calendar`
  or `after` `E_TERSE_TOKEN_UNEXPECTED`, and a `gate` or `task` with a deadline but no schedule
  `E_TERSE_SCHEDULE_REQUIRED`. `deadline` is a **contextual keyword**, not a reserved word (L9): it is read only where an
  object line can continue after its last clause, so an object may still be named `deadline` and a dependency may still
  name it (`after deadline deadline 2027-09-01`). The grammar change is therefore additive: every plan that compiled before
  compiles to the same Project, and `terse 0.1` stays.

### 3.3 Default endpoints

A `dep` names a **predecessor**; the dependent is the statement's own object.

| Predecessor | `after X` | `after X.start` / `.end` / `.at` |
| --- | --- | --- |
| span (duration, `D..D`) or group | `X.end` | that endpoint |
| fixed point (`DATE`) or derived point (a gate with no date) | `X.at` | that endpoint (`.start`/`.end` is Core's `E_ENDPOINT_MODE_MISMATCH`) |

The successor endpoint is `start` for a span or `at` for a fixed or derived point. Other successor endpoints are YAML.

### 3.4 Kinds

`KIND` is the Project `type` verbatim, restricted to `task`, `gate` and `group`. An unknown kind is
`E_TERSE_KIND_UNKNOWN` with the nearest kind in the hint; other types are written in YAML.

## 4. Mapping

| Terse | Compiles to (`timeline/v0.7`) |
| --- | --- |
| `terse 0.1` | nothing (a grammar pin) |
| `project ID` | `version: timeline/v0.7`; `project.id: ID` |
| `"Title"` on `project` | `project.title` |
| `project ... calendar C` | `project.calendar: C` |
| `calendar C days` | `calendars.C.working_days` (mon..sun order) |
| `except D ...` | one `calendars.C.exceptions[]` `{date: D, working: false}` per date |
| `work D ...` | one `calendars.C.exceptions[]` `{date: D, working: true}` per date |
| `NAME ... KIND` | key `objects.NAME`, `type: KIND` |
| `"Title"` after the name | `objects.NAME.title` |
| indentation under a `group` | `objects.NAME.parent: <group>` |
| `group` | `type: group`, `schedule: {mode: rollup}` |
| `DATE` | `schedule: {mode: fixed-point, at: DATE}` |
| `D1..D2` | `schedule: {mode: fixed-span, start: D1, end: D2}` (end exclusive) |
| a `gate` with no schedule words, with `after` | `schedule: {mode: scheduled-point}` |
| `at >= D`, `at <= D` on such a gate | `schedule.constraints.at.min`, `.at.max` |
| `AMOUNT` | `schedule: {mode: scheduled, amount: AMOUNT}` |
| `AMOUNT from D` / `until D` | `schedule.anchor: {start: D}` / `{end: D}` |
| `start >= D`, `start <= D`, `end >= D`, `end <= D` | `schedule.constraints.start.min`, `.start.max`, `.end.min`, `.end.max` |
| `calendar C` on an object | `objects.NAME.calendar: C` |
| `deadline D` | `objects.NAME.deadline: D` (the last key of the object) |
| `after X` (each comma item) | one `relations[]` entry `{id, type: dependency, from, to, lag}` |
| `X`, `X.start`, `X.end`, `X.at` | `from: {object: X, endpoint: ...}` (section 3.3) |
| the dependent object | `to: {object: NAME, endpoint: start or at}` |
| `+1wd` / `-2d` | `lag: 1wd` / `lag: -2d` (a `+` is dropped; no lag emits `lag: 0d`) |
| `+1wd in C` | `lag: {value: 1wd, calendar: C}` |
| `# comment` | nothing |

Normalisations (the only implicit steps): **N1** single-calendar project default (S6); **N2** default endpoints
(3.3); **N3** an omitted lag is `0d`; **N4** relation ids (section 5); **N5** document order for objects,
calendars and relations; **N6** a leading `+` on a lag is dropped; **N7** a schedule-less `gate` with `after` is a
`scheduled-point` (the kind selects the form, S3). The `deadline` clause adds no normalisation: its date is emitted verbatim (S10).

The compiler emits no `entities`, `annotations`, `scenarios`, `extensions`, `fields`, `wbsCode`,
`plannedProgress`, `attachesTo` or `link`, and never an empty section; it emits `deadline` only for a `deadline` clause.

## 5. Identity

**Object and calendar ids.** A terse `NAME` is the Project object id, verbatim, and must be a `slug`, a subset of
every id alphabet in use (Store address segments, Scene row ids, Actual Set `projectObjectId`, View selectors,
command targets). A non-slug is `E_TERSE_NAME_INVALID` with a suggested name in the hint; the suggestion is never
applied. Unicode and upper-case ids remain possible in YAML. The title is a separate quoted string and never
derives an id. Object and calendar names live in separate namespaces; a duplicate is `E_TERSE_NAME_DUPLICATE`,
positioned at the second occurrence and naming the first line.

**Project id.** Any non-reserved word, taken verbatim with no derivation (`HALCYON-1` stays `HALCYON-1`).

**Relation ids.** Each dependency gets the id `FROM-TO` (the two object names), chosen in statement order. If the
id is already assigned (the same pair twice, or two pairs that concatenate to the same text), the compiler appends
`-2`, `-3`, ... until the id is free among the ids already assigned. Renaming an object renames its relation ids.

Compilation is stateless and there is no id stability layer: renaming a name changes the id exactly as renaming a
YAML key would.

## 6. Diagnostics

### 6.1 Shape

The shape of every other command, extended additively and only for compile findings:

```json
{"status": "rejected", "diagnostics": [{
  "code": "E_TERSE_AMOUNT_INVALID", "severity": "error", "component": "terse",
  "sourceRef": "/", "revisionRefs": [],
  "message": "'20' has no unit; write 20d (calendar days), 20w (weeks) or 20wd (working days)",
  "source": "plan.chrona",
  "sourceRange": {"line": 6, "column": 33, "endLine": 6, "endColumn": 35},
  "hint": "write 20d for calendar days; 20wd needs a `calendar` statement"}]}
```

`sourceRef` is the JSON pointer into the compiled Project when the finding has one and `/` otherwise.
`component` is `terse` for compiler codes and `core` for a Core finding that gained a position. New fields:
`source` (the path as the author gave it, `-` for standard input), `sourceRange` (`{line, column, endLine,
endColumn}`, 1-based code points, end exclusive, `endLine` equal to `line`, `endColumn` greater than `column`),
and an optional one-sentence `hint`. Codes are stable; messages and hints may be improved without a version
change. No terse diagnostic is a bare code. In code, `chrona.terse.TerseDiagnostic` subclasses
`chrona.core.diagnostics.Diagnostic`. A Core finding may also carry an optional `details` object, reported after
`message`, that a Core code documents (for example `E_FIXED_TARGET_VIOLATION`); a diagnostic without details has no
`details` key.

### 6.2 Compiler codes (stable)

- Lexical: `E_TERSE_ENCODING`, `E_TERSE_TAB`, `E_TERSE_CONTROL_CHARACTER`, `E_TERSE_STRING_UNTERMINATED`,
  `E_TERSE_STRING_ESCAPE`, `E_TERSE_TITLE_EMPTY`.
- Structure: `E_TERSE_INDENT`, `E_TERSE_CHILDREN_NOT_ALLOWED`, `E_TERSE_TOKEN_UNEXPECTED`, `E_TERSE_LINE_INCOMPLETE`,
  `E_TERSE_TITLE_UNQUOTED`, `E_TERSE_PROJECT_REQUIRED`, `E_TERSE_DIRECTIVE_ORDER`, `E_TERSE_VERSION_UNSUPPORTED`,
  `E_TERSE_UNSUPPORTED` (a recognised construct this release does not implement, and the word reserved for future
  forms), `E_TERSE_TOO_MANY_ERRORS`.
- Names: `E_TERSE_NAME_INVALID`, `E_TERSE_NAME_RESERVED`, `E_TERSE_NAME_DUPLICATE`, `E_TERSE_KIND_UNKNOWN`,
  `E_TERSE_REFERENCE_UNKNOWN`, `E_TERSE_CALENDAR_UNKNOWN`.
- Values: `E_TERSE_DATE_INVALID`, `E_TERSE_AMOUNT_INVALID`, `E_TERSE_LAG_INVALID`, `E_TERSE_DAYS_INVALID`,
  `E_TERSE_SCHEDULE_REQUIRED`, `E_TERSE_CLAUSE_DUPLICATE`.
- CLI and I/O: `E_TERSE_OUTPUT_EXISTS`, `E_TERSE_INPUT_IO`.
- Defect: `E_TERSE_COMPILER_DEFECT` (the emitted Project failed structural validation; exit 2; a property test
  asserts it is unreachable).
- Reserved, not produced: `E_TERSE_OVERLAY_CONFLICT`, `E_TERSE_OVERLAY_UNKNOWN_OBJECT`.

Semantic findings keep their **Core code** and gain a position through the source map (`E_INVALID_SPAN`,
`E_CALENDAR_REQUIRED`, `E_ROLLUP_EMPTY`, `E_ENDPOINT_MODE_MISMATCH`, and every other `validate_project` code). Hints
for Core codes live in `chrona.usecases.terse_compile`, not in Core.

### 6.3 All errors, one pass, never partial

The compiler returns one value. `project` is absent whenever any diagnostic exists; the CLI writes output only
from a complete successful result. Errors are collected per line (a bad statement does not stop the next line;
the slug name on a bad line still registers, so later references do not cascade), ordered by line then column,
capped at 50 (`E_TERSE_TOO_MANY_ERRORS` follows the 50th, positioned at the first unlisted error).

### 6.4 Source map

The compiler also returns a map from JSON pointer to the best source span: `/objects/NAME` to the name,
`/objects/NAME/schedule` and `.../amount` to the schedule words (the kind word for a derived point without bounds, the
`at` clauses when there are bounds, and `.../constraints/at/min` and `.../max` to their own clause), `/objects/NAME/calendar` to the clause, `/objects/NAME/deadline` to the clause (the keyword and the date),
`/calendars/C` to the calendar line, and `/relations/N`, `/relations/N/lag`, `/relations/N/from/object` to the
dependency item and its parts. Relations are keyed both by index (what `validate_project` reports) and by id (what
the scheduler reports for `E_FIXED_TARGET_VIOLATION`). A pointer without an entry falls back to its nearest
ancestor, and `/` always resolves.

## 7. `chrona compile`

```text
chrona compile PLAN [--output FILE | -o FILE]
```

`PLAN` is a path or `-` (standard input); the suffix is not checked. Without `-o` the Project YAML goes to
standard output. `-o` writes without ever replacing an existing file (`E_TERSE_OUTPUT_EXISTS`); a re-compile
cannot erase hand edits, and deleting the file first is the explicit act.

**Stream rule.** Diagnostics JSON goes to the stream that does not carry the YAML: standard output when the
Project goes to `-o FILE` (as for every other command), standard error when it would go to standard output.
`chrona compile plan.chrona > project.yaml` is therefore safe: on failure the redirected file is empty and the JSON
is on the terminal.

**Exit codes.** 0 success (nothing on standard error); 1 rejected (diagnostics); 2 command syntax, unreadable
input (`E_TERSE_INPUT_IO`), an existing output (`E_TERSE_OUTPUT_EXISTS`), or a compiler defect.

`compile` validates through Core only; it does not schedule. Run `chrona validate` and `chrona schedule` on the
result, or on the plan itself (section 7.1).

### 7.1 Draft dispatch: `render`, `validate`, `schedule`

These three commands accept a plan where they accept a raw Draft Project path. The CLI adapter decides by the
suffix of that one path argument: it ends in `.chrona` (case-insensitive) and has a stem, so the Store directory
`.chrona/` and a file named `.chrona` are not plans. Nothing else is inspected, and `--snapshot-reference` is never
dispatched (it is read as YAML). The adapter compiles through the use case, then:

- `validate` and `schedule` load the compiler's YAML bytes exactly as they would load that file, so their output equals
  `compile` followed by the same command.
- `render` writes the compiler's bytes as `project.yaml` into a temporary directory (the pattern `--preset <builtin id>`
  uses), renders that file with every other flag unchanged and removes the directory on every exit path. The draft
  closure's Project is therefore the compile output, and rendering `plan.chrona` is byte-identical to compiling and
  then rendering the YAML. No temporary path appears in any output.
- A plan that does not compile is reported with the compiler's diagnostics (the shape of section 6.1, with `source`,
  `sourceRange` and `hint`) on standard output and exit code 1 (2 for an unreadable file or a compiler defect); nothing
  is scheduled or rendered and no output file is written.
- A finding of the scheduler or of the presentation stage's scheduling on a compiled plan (for example
  `E_FIXED_TARGET_VIOLATION`, `E_UNSUPPORTED_CYCLE`, `E_CONTRADICTORY_BOUNDS`) is positioned through the source map and
  gets the compiler's `source`, `sourceRange` and a hint, with its own code and component. A YAML Project keeps
  the legacy diagnostic shape, except that its Core validation findings (`E_SCHEMA`, `E_REFERENCE`, `E_PARENT_NOT_FOUND`, ...) carry the
  node's `sourceRange` (Spec 56 section 3.3).

Every other command (`render-review`, `render-review-gallery`, `materialize`, `review`, `baseline-*`, `command-*`,
`actual-*`, `workspace`, `render-workspace`, `authoring-command-apply`) reads YAML only. A `.chrona` path cannot become
a closure member, a snapshot or a baseline: nothing in `storage`, `operational` or `presentation` can import the
compiler, and a Render Context references YAML.

## 8. Determinism and the emitter

The result is a pure function of the source bytes and the grammar version: no clock, locale, environment, host
path, hash seed or random source, and nothing about the source (path or hash) in the output beyond a fixed header
comment (`# generated by chrona compile (terse 0.1); once edited, this file is the authority`).

The YAML is written by a hand-written emitter, not `yaml.safe_dump`, so the bytes cannot move with a PyYAML
release. Format: LF only, UTF-8 without BOM, a final newline, two-space block mappings, one-line flow `schedule`,
weekday list and relation entries, fixed key order (`version`, `project`, `calendars`, `objects`, `relations`;
per object `type`, `title`, `parent`, `calendar`, `schedule`, `deadline`; per relation `id`, `type`, `from`, `to`, `lag`).
Dates are always single quoted. A scalar is plain only when it matches `[A-Za-z][A-Za-z0-9 _-]*` (no trailing
space) and is not a YAML 1.1 special word (`y n yes no true false on off null`, any case), or is an amount or lag
(`-?(0|[1-9][0-9]*)(d|w|wd)`) or the Project version; every other scalar is single quoted with `''` escaping and
written literally in UTF-8, except a string containing a character PyYAML cannot read or folds (C1 controls, U+0085,
U+2028, U+2029, non-characters), which is double quoted with `\x`, `\u` or `\U` escapes. This applies to
mapping keys: an object named `on`, `no`, `yes`, `off`, `true`, `false` or `null` is emitted as `'on':` because
`safe_load` would otherwise read a boolean or `None` key.

**Round-trip contract:** `safe_load(emitted)` equals the in-memory Project for every Project the compiler can
produce. A test enforces it on every fixture and on the seeded fuzz.

## 9. Proof obligations

Golden pairs (`tests/fixtures/terse/*.chrona` with `*.project.yaml`, including a plan of derived gates); the 32-line HALCYON-1 schedule core compiles
to a Project that validates and schedules identically to the hand-written example (placements, dependency edges
modulo relation ids, critical set), compared through the scheduler; a seeded mutation fuzz (never raises, every
diagnostic positioned inside the text, no partial Project, accepted implies Core-valid, byte-stable); one negative
fixture per compiler code, with the ten likeliest mistakes as literal fixtures; the ledger test; the layering
check; the determinism check under other hash seeds and locales.

## 10. Documentation check and hand-over

`tools/check_documented_commands.py` compiles every fenced block whose info string is `chrona` in `README.md`, the
guides and the agent skill; such a fence is a plan and is never scanned for CLI commands, so an object named `chrona`
is not read as an invocation. Markers on the line before a fence refine the check: `<!-- chrona:doc-check skip:
REASON -->` leaves the plan unchecked; `<!-- chrona:doc-check expect-error: CODE -->` requires the plan to be rejected
with `CODE`; `<!-- chrona:doc-check expect-yaml: next -->` requires the next fence of the document to be a `yaml` fence
equal to the emitted Project without its header comment line. A plan on the card ([`terse-plan.md`](../guides/terse-plan.md))
must also validate and schedule, and the card stays within 120 lines; [`terse-plan-mapping.md`](../guides/terse-plan-mapping.md)
holds the executable plan and YAML pairs.

The agent interface (#142) relies on exactly what this specification freezes: the grammar and the card, the code
catalogue (section 6.2), the diagnostic fields (`sourceRange`, `hint`, `source`), `chrona compile -` for standard input,
the exit codes and stream rule (section 7), the all-errors-in-one-pass behaviour, that a rejected plan never emits a
Project, the draft dispatch (section 7.1) and the hand-off rule (compile first, then edit the YAML for anything the
syntax cannot say). The skill and any MCP tool are specified by their own documents.

## 11. `chrona import`: a table as a front end (#1307)

`chrona import TABLE --output PROJECT [--actual-output ACTUAL]` reads a CSV or TSV table, one row per object, and writes the
Project YAML (and an Actual Set). The closed column vocabulary is `id`, `title`, `type`, `start`, `end` (exclusive) or `finish`
(inclusive), `duration`, `parent`, `predecessors` (the `after` grammar of section 3), `deadline`, `calendar`, `progress`,
`actual_start` and `actual_finish`; headers match case-insensitively, any other column becomes a text entry of the object's
`fields`, and `--columns` maps header names to the vocabulary. The importer turns the table into a terse plan and compiles it
with the compiler of section 4, so the Project is byte-identical to `chrona compile` of that plan; `fields` are added to the
compiled mapping and the emitter of section 8 writes it. `progress` (a fraction, or a percentage when above 1 or written with
`%`) and the `actual_*` dates become observations of an Actual Set (`--as-of` sets its date); `--actual-output` is required when
the table has them. Every finding of the compiler or of Core validation, and the importer's own (`E_IMPORT_ID_MISSING`,
`E_IMPORT_ID_DUPLICATE`, `E_IMPORT_PARENT_UNKNOWN`, `E_IMPORT_PARENT_CYCLE`, `E_IMPORT_COLUMN_MISSING`,
`E_IMPORT_COLUMN_DUPLICATE`, `E_IMPORT_COLUMN_CONFLICT`, `E_IMPORT_ROW_TOO_LONG`, `E_IMPORT_DATE_INVALID`,
`E_IMPORT_PROGRESS_INVALID`), is reported in one run with `cell: {row, column, header}` (row 1 is the header), exit code 1;
an unreadable table or an existing output is exit code 2, and nothing is overwritten.
