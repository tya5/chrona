# ADR-0003: Model Dependencies by Endpoints

**Status:** Accepted for Core v0.1

## Context

Traditional project tools expose FS, SS, FF, and SF dependency types.

## Decision

The semantic primitive is an endpoint-to-endpoint dependency:

```text
target.endpoint >= advance(source.endpoint, lag)
```

FS/SS/FF/SF are aliases for endpoint pairs.

## Consequences

Point-to-span, span-to-point, and point-to-point dependencies use the same model.
Compatibility import/export can translate traditional dependency labels.
