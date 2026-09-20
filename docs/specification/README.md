# Specification Reading Guide

Specification numbers are stable identifiers, not a required reading sequence. Choose
the shortest path for the task. Normative ownership comes from each document's `Owns`
line and explicit successor statements, never from the highest number alone.

## Core project and scheduling

Read `00` Vision, `01` Concepts, `02` Domain Model, `03` Temporal Model, `04`
Scheduling Model, `05` Project Format, and `12` Quality/Invariants. The Core diagnostics
and semantic supplements refine this path.

## Presentation and review output

Read `01` presentation vocabulary, `06` View, `07` Style/Theme, `13` Presentation
Format, `29` Presentation Settings, `27` Layout, `30` Shared Foundation, and `08` Scene.
Documents `24`–`26` and `28` are focused normative surface/detail contracts whose
historical milestone names do not change their ownership.

## Application, commands, storage, and extensions

Read `09` Application Architecture, `10` Command Model, `11` Extension Model, `15`
Revision Store Adapters, `16` Federation, and `32` Repository Layout. Supplemental
runtime reactivity and adapter-output documents refine these boundaries.

## Opt-in successor capabilities

Read `18` DateTime/DST, `19` Resource/Capacity, `20` Collaboration, `21` Extension
Lifecycle, `22` Output/Release, and `23` Review SVG as independent opt-in successors.
Their library evidence does not imply CLI reachability.

## Catalog and product status

Read `14` Use Case Catalog for separate design/library and user-product status. `17`
defines the normative implementation-delivery profile. Planning and gate history lives
under `docs/planning/` and `docs/archive/`, not in this normative reading order.
