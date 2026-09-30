# Archived schema files

These are historical JSON Schema files that the running product no longer reads.
They were moved here from `schemas/` by issue #662 (slices S5a to S5c) with
`git mv`, so `git log --follow` on any file shows its full history.

This folder is evidence, not a contract. Nothing under `src/`, `tools/`, `tests/`
or `conformance/` may read a file here, and the inventory
(`schemas/schema-inventory-v0.1.yaml`) does not list them. The folder sits outside
`schemas/` on purpose: the wheel ships `schemas/` recursively, so a file here adds
nothing to the package.

- A document that declares one of these versions is rejected by the runtime as an
  unsupported version; migrate it to the current version listed in
  `schemas/README.md`.
- To recover what an old version accepted, read the file here or check out the
  commit before it was archived. Git history is the record; this folder only keeps
  the files reachable for reading.
- Files that are still accepted at runtime or still have committed documents
  (for example View v0.26 and v0.27, Theme v0.11 and v0.12, icon-catalog v0.3, Scene v0.6)
  remain in `schemas/` until their own migration issues retire them. Theme v0.8 also
  remains: `conformance/declared-vocabulary-policy-v0.1.yaml` still pins it, and its
  live successor declares a wider marker shape set that the policy has not yet accepted.

A test (`tests/unit/tools/test_schema_archive.py`) fails if a file here is still
listed in the inventory, exists in `schemas/`, or is named by executable code.
