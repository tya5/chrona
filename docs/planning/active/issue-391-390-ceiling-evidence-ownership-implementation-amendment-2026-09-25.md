# Implementation Amendment: Ceiling and evidence ownership (#391, #390)

**Status:** Accepted.

## Trigger

I391-2 named a generated capability-ceiling document while I390-2 named a
generated prior-art matrix derived from the same registry.  Two generated
authorities over the same ceiling would permit drift and contradict the
one-owner rule adopted by #391.

## Amendment

I391 owns only the typed registry, its runtime/profile consumers, and
registry-completeness/substitution-guard tests.  The accepted #391 design is
the explanatory design authority for ownership and substitution semantics.

I390 owns the sole generated human-readable evidence artifact: the prior-art
matrix, including the complete capability ceiling rows and external-reference
columns.  I390's generator/check is therefore the only synchronization gate for
published capability rows.

## Unchanged boundaries

This does not alter capability dispositions, Scene/Profile behavior, fidelity,
or any public schema.  It removes duplicated documentation ownership only.
