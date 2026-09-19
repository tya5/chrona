# Presentation Productization Analysis and Delivery Plan — 2026-09-19

**Status:** Planned — analysis complete; implementation is not authorized by this document.  
**Authority:** This document owns the productization analysis, layering decision, and
delivery order for M15–M18. It does not amend Project, scheduling, Actual, View, Style,
Theme, Scene, or Output semantics. A numbered owning specification and a design-closure
review are required before each implementation milestone begins.

## 1. Decision and evidence

Chrona should grow from M14's decision-correct review SVG into a presentation system
that can produce the two desired visual directions: a light, table-led executive
timeline and a dark delivery-control dashboard. The generated images are exploratory
visual references, not a data contract and not an acceptance artifact. They MUST NOT be
encoded as Python layout branches, image-specific IDs, or renderer defaults; they are
reproducible only as user-editable View/Profile/Style/Theme resources. Their useful
properties are: a semantic table beside the timeline, a hierarchical calendar,
meaningful group surfaces, planned/Actual comparison, and optional read-only decision
summary panels.

The design rule remains unchanged: **Project/Schedule/Actual own truth; View selects
facts; Profile specifies composition; Style/Theme expresses them; Scene and Output
render them.** No visual feature may invent progress, risk, a forecast, or a schedule.

The reusable base mechanisms are deliberately part of Chrona: closed semantic columns,
calendar levels, group modes, routed connectors, bounded metrics, and role/token
resolution. The visual concepts themselves remain data supplied by users.

## 2. Gap analysis and layer ownership

| Visual capability | User value | Existing state | Owning layer(s) | Required design change |
|---|---|---|---|---|
| Semantic table beside timeline | Scan owner, workstream, status, and variance without losing time context. | M14 has labels only. | View → table-timeline profile → Scene/adapter | Extend the View's declarative projection with closed `tableColumns`; define a profile-owned column geometry and cell roles. |
| Hierarchical calendar | Read quarter/month/week structure and distinguish major from minor time boundaries. | M14 fixes weekly grid and month labels. | View window + profile axis policy → Scene/adapter | Add a versioned calendar-axis profile with explicit levels, grid roles, locale supplied by Render Context, and deterministic tick algorithm. |
| Group treatment catalog | Make ownership/workstream grouping visually obvious and user-selectable. | M14 selects groups; profile declares modes, but the implementation must be checked against every declared mode. | View grouping + profile + Style/Theme → Scene/adapter | Specify exact semantics for `none`, `separator`, `band`, and `header-and-separator`; correct M14 behavior before reuse. |
| Plan/Actual visual language | Compare plan and observation at a glance without turning Actual into forecast. | M14 has dual bars, variance, missing/unmatched states. | View comparison + Style/Theme | Retain current semantics; add role catalog and density rules only. No new actual/schedule meaning. |
| Dependency and callout routing | Keep relation arrows and annotations legible when a table and groups consume space. | Semantic relations and annotation intent exist; M14 geometry is narrow. | View visibility/intent → profile → Scene/adapter | Define obstacle-aware, deterministic routing and collision diagnostics; never write routes to Project or View. |
| Delivery-health / risk panel | Offer a slide-ready decision summary without fabricated KPIs. | No summary projection contract. | New read-only summary View/Profile → Scene/adapter | Define a closed metric catalog, availability/unknown state, provenance, and panel composition. Forecasts remain out of scope. |
| Theme families | Allow light executive and dark control-room expression over the same facts. | Theme tokens exist; M14 resolves only a small renderer subset. | Style/Theme + profile roles → adapter | Define role/token coverage, contrast requirements, and sample gallery; geometry stays in the profile. |
| Accessible, export-ready composition | Preserve source identity and text alternatives in dense layouts. | M14 SVG metadata/accessibility baseline exists. | Scene/Output | Extend semantic cell/panel relationships and capability declarations; SVG remains the reference target. |

## 3. Boundary decisions

1. **View remains declarative and semantic.** It may choose the columns, their order,
   their closed data sources, grouping, comparison facets, and temporal window. It may
   not contain pixels, SVG fragments, executable formatters, inferred workflow state, or
   arbitrary field traversal.
2. **A table-timeline profile owns geometry.** Column widths, panel slots, axis levels,
   row metrics, group treatment, and routing exclusion zones are renderer policy. This
   permits the same View to render compactly in an engineering review or spaciously on a
   slide without forking project facts.
3. **Theme is visual only.** It provides colour, typography, line, fill, and contrast
   tokens for declared roles. It does not select data or decide layout.
4. **Summary panels are derived, read-only projections.** Every displayed number needs a
   named definition and source set. For example, a health ratio may be shown only after
   its numerator, denominator, and unknown/partial-data treatment are specified.
5. **Render Context supplies environment.** Locale, explicit as-of date, viewport, and
   target capability are inputs. The renderer must not use a local clock, a hidden
   default locale, or a current branch.

## 4. Existing-design changes required before implementation

| Change | Existing authority affected | Why it is needed | Gate |
|---|---|---|---|
| Close M14 group-mode semantics and implementation conformance. | `23-review-svg-rendering-successor.md`, review-SVG profile, renderer tests. | The contract names four modes; each must have distinct, tested behavior before it becomes the grouping foundation for M15. | D15-1 |
| Add closed View table-column language. | `06-view-model.md`, presentation schema/fixtures. | User-controlled table expression needs a stable semantic projection without arbitrary code. | D15-2 |
| Add table-timeline / hierarchical-axis profile. | New owning specification and schema/fixtures. | Layout and calendar hierarchy must be reproducible and independent of View semantics. | D15-3 |
| Define Scene primitives for cells, group surfaces, axis bands, and routed relations. | `08-scene-and-rendering.md` plus profile specification. | Output needs source-linked visual primitives rather than adapter-private geometry. | D15-3 |
| Define summary metric and panel contract. | New owning specification/schema/fixtures and use-case traceability. | Dashboard claims must be deterministic and must distinguish unknown data from favourable data. | D16-1 |
| Extend style/theme role coverage and output accessibility. | `07-style-and-theme.md`, Output capability contract, fixtures. | The reference themes need explicit roles and dense-layout text alternatives. | D17-1 |

## 5. Delivery plan

### M15 — Table-timeline review surface

**Outcome:** A user can declare a table-led grouped review timeline with semantic
columns and a hierarchical Date axis, rendered deterministically to accessible SVG.

| Design gate | Deliverable and acceptance focus | Depends on |
|---|---|---|
| D15-1 | M14 group-mode correction design, tests, and review. `none` draws no group treatment; `separator`, `band`, and `header-and-separator` each have an explicit, independently tested result. | M14 |
| D15-2 | View table-column grammar: allowed sources (`id`, `title`, `objectType`, `entity`, declared typed field, and requested comparison facet), deterministic formatting, missing-value treatment, and ordering. | `06` View Model |
| D15-3 | Table-timeline profile and Scene contract: columns, axis levels, grid roles, group surfaces, row metrics, clipping, routing exclusion zones, capabilities, and fixtures. | D15-1, D15-2 |
| I15 | Implement projection and SVG adapter; add Controller Z light executive acceptance sample. | D15-1–D15-3 closure |

### M16 — Decision and risk surfaces

**Outcome:** A user can add a bounded, source-traceable summary panel to a review
composition, including unknown/partial-data states rather than invented health scores.

| Design gate | Deliverable and acceptance focus | Depends on |
|---|---|---|
| D16-1 | Summary metric catalog: counts, known plan/Actual variance aggregates, next scheduled milestone, data-coverage denominator, and no-forecast rule. | M15 projection vocabulary |
| D16-2 | Profile-owned panel composition, source references, accessibility, and diagnostics for unavailable metrics. | D16-1 |
| I16 | Implement deterministic summary projection and dark delivery-control acceptance sample. | D16-1–D16-2 closure |

### M17 — Presentation themes and expression

**Outcome:** The same semantic review can be rendered with an accessible light
executive or dark delivery-control theme, with consistent group, table, axis, relation,
comparison, and panel roles.

| Design gate | Deliverable and acceptance focus | Depends on |
|---|---|---|
| D17-1 | Role/token catalog, contrast and non-colour distinction rules, and profile-versus-theme boundary review. | M15, M16 |
| D17-2 | Sample-gallery and visual regression acceptance policy using declared semantic assertions in addition to inspected SVG. | D17-1 |
| I17 | Implement token resolution coverage and publish theme samples. | D17-1–D17-2 closure |

### M18 — Product presentation release

**Outcome:** Chrona has evidence that the table-led and dashboard-led compositions
reuse one semantic closure across grouped, comparison, annotation, and export cases.

**Exit evidence:** Full conformance inheritance; deterministic output; accessibility and
capability checks; cross-theme and cross-profile review; and a reuse review proving no
parallel schedule, Actual, or metric model was introduced.

## 6. Ordering and non-goals

M15 precedes M16 because a panel must summarize the same declared projection facts that
the table-timeline exposes. M17 follows once the role surface is known; otherwise a
theme catalog would prematurely encode geometry. M18 is a release gate, not a feature
bucket.

This program does not add ticket/workflow management, automatic progress inference,
automatic rescheduling, arbitrary renderer scripts, freeform coordinates, raster/PDF
claims, or live data lookups. Any such capability needs its own owning specification
and roadmap amendment.

## 7. Review checklist before each implementation gate

- Trace every new field to exactly one semantic owner and exactly one renderer consumer.
- Demonstrate that a View/Profile change cannot mutate Project, Schedule, Actual, or a
  federated child source.
- Define missing, invalid, and unavailable-data diagnostics before happy-path rendering.
- Add schema, semantic validation, fixture, conformance, adapter, and accessibility
  evidence; visual inspection alone is insufficient.
- Publish the approved design closure before beginning its corresponding implementation.
