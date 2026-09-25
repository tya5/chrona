# I1 Implementation Amendment — Project v0.7 Fiscal Calendar (#405, #406, #407, #408, #400)

Create project-v0.7 with `fiscalStartMonth`, replace v0.6 runtime validation,
and migrate all public Project resources and their Context identities together
with View v0.17. Add schema and closure tests for absent/default, valid and
invalid months. Axis Layout consumption is I2; I1 records only the typed
calendar fact and does not introduce formatter fallback.
