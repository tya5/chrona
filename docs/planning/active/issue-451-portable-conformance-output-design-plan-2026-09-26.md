# Design Plan — Portable Conformance Output (#451)

Windows CI proves that the #451 runner captures UTF-8 child output but writes
its own aggregate report through the host CP1252 stdout.  Complete the stated
platform-neutral report contract by defining an explicit UTF-8 runner transport
boundary, with no changes to check status, capture, ordering, or tool facts.
