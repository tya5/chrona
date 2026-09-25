# I1 Implementation Amendment — View v0.17 (#405, #406, #407, #408, #400)

Replace I1's v0.16 target with v0.17. Create the new schema and runtime
binding, remove v0.16 ingress, migrate every View and Context closure in the
same implementation release, and update inventory/package/negative tests.
The typed tier implementation and failure registry remain the subsequent I1–I3
work; no legacy axis field is retained merely to ease migration.
