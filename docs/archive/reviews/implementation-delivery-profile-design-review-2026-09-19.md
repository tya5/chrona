# Implementation-Delivery Profile Design Review

**Date:** 2026-09-19  
**Disposition:** IDP-6 complete; self-hosting design gate satisfied.

## Result

The standard `implementation-delivery` profile has one owner for vocabulary and field
shape (`17`), uses Core temporal/scheduling semantics unchanged (`02`, `04`), resolves
immutable evidence through the Revision Store (`15`), and permits canonical changes
only through the Command Model (`10`). Project Format (`05`), Extension Model (`11`),
Quality (`12`), and the self-hosted roadmap fixture provide the matching structural,
semantic, and acceptance evidence.

## Boundary check

Workflow state, assignment metadata, reuse classification, and evidence references do
not grant authorization, create a transition engine, alter Actual, add resource
capacity, or change scheduling. Mutable evidence, mismatched evidence kinds, and
unresolved package fields have stable diagnostics. The profile is reusable by projects
other than Chrona itself.

## Deferred work

Profile UX, access control, notifications, estimation, capacity, cost, ticketing, and
automatic transitions are distinct capability work. They are not implied by this
profile and require their own owning-specification change before implementation.
