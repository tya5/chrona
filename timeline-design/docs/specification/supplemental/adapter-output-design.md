# Adapter and Output Design

**Status:** Proposed  
**Owns:** Scene-to-target fidelity, target capability negotiation, adapter projection,
gesture translation boundary, and output acceptance evidence.

## 1. Common adapter contract

An adapter consumes a completed Scene and declared target capabilities. It returns an
artifact plus diagnostics; it cannot load Project data, infer missing roles, or mutate
canonical state. Required source metadata, semantic/explanatory distinction, labels,
markers, clipping, and text alternatives are checked before output.

Unsupported required capability is a diagnostic, not a silent approximation. Target
defaults are allowed only when expressed as declared Theme, Scene profile, or metrics
input.

## 2. SVG acceptance

The SVG adapter preserves stable `sceneId` and source metadata, deterministic paint
order, declared token values, text alternatives, clipping, and semantic versus
explanatory arrow distinction. Golden SVG artifacts compare normalized structure rather
than incidental serialization whitespace.

## 3. Interactive adapter

Projection applies SceneDelta by stable `sceneId`; it does not recreate unrelated nodes.
Interaction translation maps a gesture to a previewable Command proposal with stable
source ID and base revision. Editing arbitrary canvas geometry, imported SVG, or
renderer-private composites never edits canonical data automatically.

## 4. Future targets

Canvas/tldraw and PPTX adapters have the same common contract. They may declare lower
capabilities, in which case the coordinator reports degraded or rejected distinctions.
Their stores/files are artifacts, not a second persistence model.
