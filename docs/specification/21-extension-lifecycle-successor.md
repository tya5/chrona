# Extension Lifecycle and Registry Successor Design

**Status:** Proposed  
**Owns:** declarative extension package registry, acquisition, compatibility, lifecycle,
and missing/cyclic package policy.

## 1. Registry and acquisition

A registry maps a stable package identity and version range to immutable candidate
manifests. Resolution selects one manifest only from configured trusted sources and
records source/provider, exact package version, content identity, and compatibility
result in the evaluation closure. A package reference never means “latest”, a local
directory, or arbitrary code retrieval.

Package acquisition fetches declarations and optional static assets only. It validates
content identity, signature/trust policy where configured, package format, required
Chrona API/profile versions, and dependency closure before use. Failure leaves the
previous closure unchanged and diagnoses missing, untrusted, incompatible, or corrupt
packages.

## 2. Lifecycle and compatibility

States are `declared`, `resolved`, `verified`, `active`, `deprecated`, and `rejected`.
Only a verified, compatible declarative package is active for an explicit evaluation.
Deprecation is diagnostic metadata, not a silent upgrade. Upgrading is an explicit
Command-governed migration to a newly pinned identity; no resolver upgrades a Project
behind its back.

Dependencies are resolved with exact compatibility ranges and a deterministic
version-selection rule. Cycles, duplicate package IDs with different content identity,
and conflicting dependency ranges reject the closure. Profile inheritance cycles remain
separate semantic diagnostics; package acquisition does not attempt to repair them.

## 3. Code-plugin exclusion

Registry packages are data, not host code. Renderer/editor/importer code plugins use a
host installation registry, explicit API compatibility, and host trust/sandbox policy.
They receive typed derived inputs and may submit normal Commands, but cannot make their
installation a Project semantic dependency or execute from a package declaration.

## 4. Required evidence before implementation

- schema/fixtures for verified acquisition, incompatible version, missing package,
  dependency cycle, and code-plugin exclusion;
- Extension, Revision Store, and Application Architecture lifecycle updates plus ADR;
- review showing package resolution is pinned, reproducible, declarative, and distinct
  from profile inheritance and host code plugins.
