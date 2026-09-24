# Issue 367: authoring Unicode CAS identity design plan

## Problem

Authoring commands calculate `baseRevision` with a private JSON serialization
while the persistence adapter validates it with `content_identity`. The former
escapes non-ASCII JSON by default; the latter preserves UTF-8. A Japanese Draft
can therefore reject its own current revision without concurrency.

## Decision

`content_identity` is the sole canonical identity at the authoring command and
CAS boundary. Remove the duplicate command-local codec. Test ASCII and Japanese
workspaces, stale command rejection, and materialization identity continuity.
