# Design Plan: Windows Portability (#359)

## Objective

Make every supported Chrona command and reproducible corpus workflow portable to
Windows without weakening immutable identity, atomic publication, or the
semantic opacity of revision tokens.

## Design questions

1. Define one filesystem representation for opaque local snapshot tokens.
2. Preserve exclusive result and baseline publication without POSIX hard links.
3. Define cross-platform advisory aggregate locking without an unconditional
   platform import.
4. Make all production/tool/conformance text I/O explicitly UTF-8 and enforce
   that rule structurally.
5. Prevent Git line-ending conversion from changing identity-pinned repository
   resources, and continuously prove the result on Windows.

## Required outputs

- approved architecture review and implementation plan;
- `.gitattributes`, UTF-8 checker, Windows matrix, and Windows-only clone
  reproduction evidence;
- focused tests for token codec, lock adapters, no-hard-link publication,
  explicit encodings, module entry point, and captured-baseline materialization;
- full conformance, parallel test suite, wheel/install/smoke, and public
  release review before closing #359.
