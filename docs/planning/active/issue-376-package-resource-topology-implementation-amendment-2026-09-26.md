# Implementation Amendment — Minimal Template Package Topology (#376)

Amend I376-1: do not add a wheel `force-include` entry for the package-tree
minimal template.  Build a wheel and assert an isolated installed interpreter
can call `minimal_template_resource()` and initialize/render the starter.
Retain the existing external HALCYON force-include unchanged.
