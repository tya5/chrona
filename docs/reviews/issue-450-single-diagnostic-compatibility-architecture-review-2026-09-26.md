# Architecture Review — Single Schema Diagnostic Compatibility (#450)

**Decision:** accept.  Two explicit APIs preserve two distinct contracts:
stable concise ingress explanation and complete aggregation.  This avoids a
hidden compatibility regression while keeping aggregation at its new boundary.
