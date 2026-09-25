# Design Correction — Portable Scene Report Encoding (#446)

`check_scene_perceptibility.py` publishes Scene identifiers; they are Unicode
data, not terminal-local text.  It therefore reconfigures its stdout transport
to UTF-8 before rendering either report form.  The evaluator and report model
remain pure Unicode values.  No identifier is escaped, dropped, or made
platform-specific; CI receives the same UTF-8 report on every OS.
