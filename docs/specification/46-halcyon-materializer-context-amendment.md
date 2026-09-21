# Issue #46 materializer context amendment

Each manifest slide may declare `context`; materialization resolves that slide-local context, falling back to manifest `context` only for compatibility. This is selection metadata, not a renderer branch, and makes every declared HALCYON context an acceptance target.
