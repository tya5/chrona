# Quality Goals and Architectural Invariants

**Status:** Stable
**Core v0.1 invariant subset:** Proposed
**Scope:** Core Specification v0.1 and cross-layer architecture
**Cross-cuts:** `00`–`11`

## 1. Purpose

This document defines reviewable system qualities and invariants that cut across the
Core, Presentation, Application, Command, and Extension specifications. It does not
replace the owner of any semantic rule; it provides the testable properties used to
detect when a design or implementation violates those rules.

An implementation change that fails an invariant is a specification-review event. It
must not silently redefine the model to fit an implementation shortcut.

## 2. Reviewable serialization and Revision Store quality

These identifiers retain their historical `Q-GIT` names because Git remains an
important review adapter. They are requirements for canonical serialization and
immutable evaluation, not a requirement that the runtime has Git installed.

### Q-GIT-1 Meaningful diff

A simple semantic schedule edit SHOULD produce a small diff focused on the changed
semantic value.

Moving a milestone must not require updating renderer coordinates, unrelated objects,
or generated caches.

### Q-GIT-2 Stable identity

Renaming an object SHOULD NOT require changing its identifier or references unless the
user explicitly chooses to rename the identifier.

### Q-GIT-3 Derived-state exclusion

Deterministically derived scene and renderer state MUST NOT be required in the
semantic project source.

### Q-GIT-4 Explicit revision inputs

Project, Snapshot, Actual, View, Style, Theme, and extension-package references that
influence an evaluation MUST be explicit and identifiable. A consumer MUST NOT silently
select “latest”, a working-tree tip, current branch, or a local default as an
authoritative input.

### Q-GIT-5 Federated ownership and pinning

A parent Federation Plan MUST consume a subproject only through a declared immutable
timeline export reference. It MUST NOT silently follow a child branch, copy child canonical
objects into its own source, or mutate a child Project. A closure manifest MUST record
the child export's Store/provider identity, address, project ID, revision, content identity, and
federation namespace.

## 3. Determinism

### Q-DET-1 Scheduling

The same Project, profiles, calendars, and explicit scheduling context MUST produce
the same resolved schedule.

### Q-DET-2 Rendering boundary

The same resolved semantic project plus View, Style, Theme, Scene profile, viewport,
layout metrics, and explicit RenderContext MUST produce equivalent Scene output and
diagnostics.

Dynamic values such as `today` must be explicit context when reproducibility is
required.

### Q-DET-3 Cache equivalence

A derived-state cache hit MUST be observationally equivalent to recomputing the
declared inputs. It must not conceal diagnostics or mix artifacts from different input
revisions.

### Q-DET-4 Stable scene provenance

Every renderable Scene node MUST retain stable Scene identity, source reference, source
kind, and visual-role metadata. Paint order, renderer element IDs, or array position
are not substitutes for this provenance.

### Q-DET-5 Incremental interactive updates

After a canonical change, an interactive adapter MUST reconcile the completed Scene by
stable `sceneId` and apply only the affected `SceneDelta` operations. A local change
MUST NOT default to destroying and recreating every UI node.

A full-Scene replacement is allowed only for a declared global invalidation domain, such
as an all-node View/Style/Theme/viewport/scale change or a dependency closure that
actually reaches every displayed object. The Runtime Coordinator MUST report that
invalidation reason and preserve atomic evaluation identity during reconciliation.

## 4. Semantic isolation

### Q-SEM-1 Presentation independence

View, Style, Theme, Scene, and renderer state MUST NOT alter project scheduling
semantics.

### Q-SEM-2 Renderer independence

Domain data MUST remain usable without tldraw or any other renderer.

### Q-SEM-3 Serialization independence

YAML shorthand MUST normalize into the semantic model; shorthand syntax MUST NOT
introduce semantics that do not exist in the model.

### Q-SEM-4 Relation and annotation distinction

A semantic dependency and a presentation-only explanatory arrow MUST remain distinct
through View, Style, Scene, and renderer adaptation. An explanatory arrow MUST NOT
create a scheduling constraint.

### Q-SEM-5 Plan, baseline, and actual distinction

Planned placement, Snapshot comparison, and Actual observation remain independently
identified. Recording an Actual MUST NOT implicitly reschedule planned work. A missing
or unmatched Actual MUST be diagnosed or represented as unknown, never fabricated as a
completion or forecast.

### Q-SEM-6 Annotation anchoring

Presentation annotations retain a stable semantic or View-local anchor and logical
placement intent. Collision resolution may change derived geometry only within declared
constraints; it must not silently detach the annotation.

### Q-SEM-7 Federated scheduling isolation

Federated child summaries are read-only presentation inputs. A parent-owned dependency
may use a published child interface milestone only as an external condition on
parent-owned work; it MUST NOT reschedule or modify the child. Aggregated child
progress is display-only unless a future scheduling specification explicitly defines
otherwise.

## 5. Temporal correctness

### Q-TIME-1 Type distinction

Date and DateTime MUST NOT be silently mixed.

ExactDuration, CalendarPeriod, and WorkPeriod MUST remain distinct.

### Q-TIME-2 Interval consistency

Resolved spans MUST use `[start, end)` semantics and MUST be non-empty.

### Q-TIME-3 No hidden day adjustment

Finish-to-Start zero lag MUST allow `predecessor.end == successor.start`.

### Q-TIME-4 Explicit calendar dependency

WorkPeriod arithmetic MUST NOT resolve without a calendar.

### Q-TIME-5 Scheduling-safe amount types

Calendar-month and calendar-year periods MUST NOT be accepted as scheduled span
amounts in Core v0.1. They remain valid temporal offsets.

## 6. Scheduling correctness

### Q-SCHED-1 Endpoint semantics

Dependencies MUST be reducible to endpoint bounds.

### Q-SCHED-2 Deadline distinction

A deadline MUST NOT silently become a scheduling constraint. Fixed placements and
explicit scheduled anchors MUST NOT be silently moved to satisfy a conflicting
dependency or bound.

### Q-SCHED-3 Conflict diagnostics

Unsatisfiable bounds, cycles, missing calendars, and invalid temporal types MUST
produce diagnostics rather than arbitrary schedule output.

## 7. Extensibility

### Q-EXT-1 Known base semantics

A declarative custom profile MUST inherit through a declared, acyclic chain from
exactly one known semantic primitive.

### Q-EXT-2 Fallback

A consumer that does not understand a custom profile SHOULD be able to fall back
through its inheritance chain where safe.

It MUST NOT claim scheduling or mutation conformance for an unknown specialization.

### Q-EXT-3 Typed fields

Extension fields MUST be schema-declared and type-checkable. A package affecting
interpretation MUST have an explicit version and resolved content identity; breaking
interpretation requires an explicit migration or validation failure.

### Q-EXT-4 Safe expressions

User-defined predicates and derived expressions MUST NOT permit arbitrary host-language
code execution, I/O, clock/random access, unconstrained graph traversal, or new
scheduling semantics.

### Q-EXT-5 Plugin separation

Semantic extensions are declarative data/schema. Renderer and editor plugins are
host-installed code and MUST NOT gain canonical mutation authority except through
ordinary Commands. Installing a plugin does not change Project meaning.

## 8. Command and mutation integrity

### Q-CMD-1 Shared semantic boundary

GUI, CLI, automation, and AI agents MUST submit canonical changes through the Command
Model. Dragging a rendered bar is a Command proposal, not a direct coordinate write.

### Q-CMD-2 Validation and atomicity

A rejected command or transaction MUST leave canonical state unchanged. An accepted
transaction MUST create one identifiable revision after owner-specification validation
and must invalidate affected derived outputs.

### Q-CMD-3 Concurrency and history

Canonical mutations MUST bind a base revision or equivalent compare-and-set
precondition. Stale writes MUST be rejected or explicitly merged; hidden
last-writer-wins behavior is prohibited. Undo and redo create new validated revisions
rather than rewriting shared history.

### Q-CMD-4 No derived-state bypass

No command, plugin, importer, or AI client may treat a resolved schedule, Scene
coordinate, SVG element, or canvas shape as an authoritative semantic mutation without
translating it to validated canonical intent.

## 9. Accessibility and agent operability

### Q-ACC-1 Non-colour distinction

Required visual distinctions—including planned versus Actual, semantic dependency versus
explanatory arrow, and exceptional comparison state—MUST NOT rely on colour alone.

### Q-ACC-2 Fidelity reporting

A renderer or plugin that cannot preserve a required semantic distinction, source
reference, or accessible alternative MUST report the capability loss. It must not
silently erase meaning.

### Q-AI-1 Semantic mutation

A schedule edit SHOULD be expressible as a semantic command rather than a sequence of
pixel manipulations.

An AI agent MUST NOT turn an uncertain title or visual match into a stable object
reference without confirmation or an ambiguity diagnostic.

### Q-AI-2 Explainability

Validation, scheduling, View evaluation, style resolution, Scene construction, and
rendering SHOULD expose enough structured diagnostics to explain why a value or
appearance was produced.

### Q-AI-3 Discoverability

Schemas, profiles, and examples SHOULD provide sufficient structure for an agent to
discover valid operations without relying solely on prose documentation.

## 10. Scope discipline

Core design SHOULD reject features that require turning the system into:

- a resource optimizer;
- a timesheet system;
- a generic workflow engine;
- a generic graph database;
- an arbitrary programmable scheduler;
- a renderer-authoritative slideware clone.

Such features MAY be reconsidered only when they preserve these invariants, have an
identified owning specification, and do not obscure Chrona's time-axis-centered
semantic model.

## 11. Verification expectations

Each invariant should be backed by the most suitable evidence. The implementation plan
may add finer-grained cases, but it must not omit the following categories.

| Quality area | Minimum evidence |
|---|---|
| Core temporal/scheduling rules | Canonical YAML fixtures, validator/scheduler conformance tests, stable diagnostic assertions |
| Git quality and normalization | Canonicalization tests and focused before/after diff fixtures |
| View/Style/Theme/Scene | Deterministic projection fixtures with input manifests and provenance assertions |
| Interactive projection | Local-change SceneDelta fixture, no-unrelated-node-recreation assertion, global-invalidation reason assertion, and stale-result suppression test |
| Plan/Snapshot/Actual | Alignment, missing/unmatched, and no-implicit-rescheduling scenarios |
| Federated projects | Pinned-export resolution, independent-parent/child mutation, namespace collision, incompatible export, cycle, and stale-reference diagnostics |
| Commands | Accept/reject, transaction atomicity, stale-base conflict, undo/redo, and no-derived-write tests |
| Extensions | Inheritance/fallback, typed-field, version/migration, expression-safety, and plugin-boundary tests |
| Renderer adapters | Capability/fidelity and accessibility fixtures; generated output is checked as derived state |

## 12. Cross-layer review checklist

A design or implementation change is ready for focused review when it can answer all of
the following:

1. Which specification owns the changed meaning?
2. Is the changed state canonical, declarative presentation data, or derived output?
3. Are every input revision and evaluation context explicit?
4. Can the result be reproduced without renderer-local state?
5. Does it preserve plan/baseline/Actual and dependency/explanatory-arrow distinctions?
6. Does it preserve stable identity, meaningful Git diffs, and deterministic diagnostics?
7. Does it require an extension, schema, example, conformance fixture, or ADR update before implementation?
8. Does it accidentally expand Chrona into a generic PM system or arbitrary execution environment?

## 13. Core v0.1 review checklist

Core v0.1 is internally coherent when all of the following hold:

- every core primitive has one semantic definition;
- temporal arithmetic is type-distinct and deterministic;
- interval boundaries are unambiguous;
- dependency endpoint semantics and authority rules are unambiguous;
- zero-lag behavior is demonstrated by examples;
- calendar-day and working-day behavior are distinguishable;
- Project Format can represent all normative Core concepts;
- canonical examples satisfy the intended schema;
- major irreversible choices have ADRs;
- no normative Core rule depends on a renderer.
