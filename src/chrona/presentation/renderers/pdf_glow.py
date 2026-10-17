"""Private, exact-font raster lowering for completed PDF glow halos."""
from __future__ import annotations

from base64 import b64encode
from math import ceil, floor, isfinite
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Mapping

from chrona.presentation.model.font_metrics import FontFile
from chrona.presentation.renderers.pdf_fonts import PdfFontConversionError, pdf_raster_font_bytes
from chrona.presentation.scene.model import SceneSurface


PDF_GLOW_GRAMMAR = "pdf-resvg-completed-glow-v1"
_SVG_NS = "http://www.w3.org/2000/svg"
_NS = {"s": _SVG_NS}


def lower_pdf_glows(surface: SceneSurface, svg: bytes, files: tuple[FontFile, ...],
                    aliases: Mapping[tuple[str, str, int], str]) -> bytes:
    """Replace only completed glow filters with private alpha PNG halos.

    Geometry, region, source paint, text measurement and font choice come from
    Scene/its closed asset set. This routine only constructs a PDF-private SVG
    intermediate and gives resvg the exact closed faces needed to paint halos.
    """
    primitives = tuple(getattr(surface, "primitives", ()))
    glowing = [item for item in primitives if getattr(getattr(item, "paint", None), "glow", None) is not None]
    if not glowing:
        return svg
    try:
        from lxml import etree
        import resvg_py
    except ImportError as error:
        raise ValueError("E_RENDER_RASTERIZER_UNAVAILABLE: PDF glow requires lxml and resvg-py") from error

    root = etree.fromstring(svg)

    def tag(node):
        return node.tag.rsplit("}", 1)[-1]

    def fail(code: str, detail: str):
        raise ValueError(f"{code}: {detail}")

    def font_paths(primitive: object, directory: Path, cache: dict[tuple[str, int, str], str]) -> list[str]:
        layout = getattr(primitive, "text_layout", None)
        if layout is None:
            return []
        wanted = {(layout.asset_identity, layout.family.split(",", 1)[0].strip().strip("\"'").casefold(), layout.weight)}
        for line in layout.runs:
            for run in line:
                if run.asset_identity:
                    wanted.add((run.asset_identity, (run.family or layout.family).split(",", 1)[0].strip().strip("\"'").casefold(),
                                run.weight or layout.weight))
        by_key = {(item.content_identity, item.family.casefold(), item.weight): item for item in files}
        paths = []
        for identity, family, weight in sorted(wanted):
            item = by_key.get((identity, family, weight))
            alias = aliases.get((identity, family, weight))
            if item is None or not alias:
                fail("E_RENDER_FONT_CLOSURE", f"PDF glow text face is not closed: identity={identity!r}, family={family!r}, weight={weight!r}")
            cache_key = (item.content_identity, item.index, alias)
            if cache_key in cache:
                paths.append(cache[cache_key])
                continue
            try:
                payload = pdf_raster_font_bytes(item, alias)
            except PdfFontConversionError as error:
                fail("E_RENDER_FONT_CLOSURE", str(error))
            directory.mkdir(parents=True, exist_ok=True)
            extension = ".otf" if payload[:4] == b"OTTO" else ".ttf"
            path = directory / ("face-" + str(len(cache)) + extension)
            path.write_bytes(payload)
            cache[cache_key] = str(path)
            paths.append(cache[cache_key])
        return paths

    with TemporaryDirectory(prefix="chrona-pdf-glow-") as temporary:
        temp_root = Path(temporary)
        font_path_cache: dict[tuple[str, int, str], str] = {}
        for primitive in glowing:
            scene_id = getattr(primitive, "scene_id", None)
            nodes = root.xpath(".//*[@data-scene-id=$scene_id]", namespaces=_NS, scene_id=scene_id)
            if len(nodes) != 1:
                fail("E_PRESENTATION_PRIMITIVE_INVALID", f"PDF glow scene_id={scene_id!r} resolves to {len(nodes)} SVG nodes")
            source = nodes[0]
            related = [source, *source.iterancestors(), *source.xpath(".//*[@filter]")]
            unique_related = []
            seen_related = set()
            for candidate in related:
                if candidate not in seen_related:
                    unique_related.append(candidate)
                    seen_related.add(candidate)
            glow_owners = []
            glow_filters = {}
            for candidate in unique_related:
                ref = candidate.get("filter")
                if ref is None or not ref.startswith("url(#") or not ref.endswith(")"):
                    continue
                candidate_id = ref[5:-1]
                definitions = root.xpath(".//s:filter[@id=$filter_id]", namespaces=_NS,
                                         filter_id=candidate_id)
                if len(definitions) != 1:
                    continue
                definition = definitions[0]
                if (len(definition.xpath(".//s:feMergeNode[@in='SourceGraphic']", namespaces=_NS)) == 1
                        and len(definition.xpath(".//s:feMergeNode[@in='halo']", namespaces=_NS)) == 2):
                    glow_owners.append(candidate)
                    glow_filters[candidate] = (candidate_id, definition)
            if len(glow_owners) != 1:
                fail("E_PRESENTATION_PRIMITIVE_INVALID", f"PDF glow scene_id={scene_id!r} has {len(glow_owners)} completed glow filter owners")
            owner = glow_owners[0]
            # Most generated effects put a filtered group around the Scene
            # node (text), while aligned stroke puts the completed Scene group
            # around a filtered paint group. In both cases the outer completed
            # Scene node is the compositing owner for its overall alpha/clip.
            if owner is source or owner in source.iterancestors():
                composite_owner = owner
            elif source in owner.iterancestors():
                composite_owner = source
                between = []
                current = owner.getparent()
                while current is not None and current is not source:
                    between.append(current)
                    current = current.getparent()
                if current is not source or any(node.get("transform") is not None
                                                or node.get("opacity") is not None
                                                or node.get("clip-path") is not None
                                                for node in between):
                    fail("E_PRESENTATION_PRIMITIVE_INVALID", f"PDF glow scene_id={scene_id!r} has unsupported nested filter-owner effects")
                if owner.get("opacity") is not None or owner.get("clip-path") is not None:
                    fail("E_PRESENTATION_PRIMITIVE_INVALID", f"PDF glow scene_id={scene_id!r} has unsupported filter-owner effects")
            else:
                fail("E_PRESENTATION_PRIMITIVE_INVALID", f"PDF glow scene_id={scene_id!r} filter owner is outside its Scene node")
            # The Scene glow region is already in surface coordinates. In the
            # generated grammar transforms live inside its untransformed owner;
            # a transform on the filter owner itself would re-transform the
            # completed pixel grid and is therefore rejected rather than guessed.
            if owner.get("transform") is not None or (composite_owner is not owner
                                                       and composite_owner.get("transform") is not None):
                fail("E_PRESENTATION_PRIMITIVE_INVALID", f"PDF glow scene_id={scene_id!r} has a transformed filter owner")
            filter_id, filter_node = glow_filters[owner]
            source_graphic = filter_node.xpath(".//s:feMergeNode[@in='SourceGraphic']", namespaces=_NS)
            halo_nodes = filter_node.xpath(".//s:feMergeNode[@in='halo']", namespaces=_NS)
            if len(source_graphic) != 1 or len(halo_nodes) != 2:
                fail("E_PRESENTATION_PRIMITIVE_INVALID", f"PDF glow filter {filter_id!r} is not the completed double-halo grammar")

            glow = primitive.paint.glow
            x, y, width, height = glow.region
            if not all(isfinite(value) for value in (x, y, width, height)) or width <= 0 or height <= 0:
                fail("E_PRESENTATION_PRIMITIVE_INVALID", f"PDF glow scene_id={scene_id!r} has invalid completed region")
            x0, y0 = floor(x), floor(y)
            x1, y1 = ceil(x + width), ceil(y + height)
            if x1 <= x0 or y1 <= y0:
                fail("E_PRESENTATION_PRIMITIVE_INVALID", f"PDF glow scene_id={scene_id!r} has empty integer pixel cover")

            # Preserve every closed definition (notably pattern and clip data)
            # while removing only the source repaint from the halo filter.
            halo_root = etree.Element(f"{{{_SVG_NS}}}svg", nsmap={None: _SVG_NS})
            halo_root.set("width", str(x1 - x0))
            halo_root.set("height", str(y1 - y0))
            halo_root.set("viewBox", f"{x0} {y0} {x1 - x0} {y1 - y0}")
            for definition in root:
                if tag(definition) == "defs":
                    halo_root.append(etree.fromstring(etree.tostring(definition)))
            halo_filter = halo_root.xpath(".//s:filter[@id=$filter_id]", namespaces=_NS, filter_id=filter_id)
            if len(halo_filter) != 1:
                fail("E_PRESENTATION_PRIMITIVE_INVALID", f"PDF glow definitions do not close filter {filter_id!r}")
            halo_source = halo_filter[0].xpath(".//s:feMergeNode[@in='SourceGraphic']", namespaces=_NS)
            if len(halo_source) != 1:
                fail("E_PRESENTATION_PRIMITIVE_INVALID", f"PDF glow filter {filter_id!r} lost its SourceGraphic node")
            halo_source[0].getparent().remove(halo_source[0])

            halo_owner = etree.fromstring(etree.tostring(owner))
            halo_owner.attrib.pop("opacity", None)
            halo_owner.attrib.pop("clip-path", None)
            halo_root.append(halo_owner)
            font_files = font_paths(primitive, temp_root, font_path_cache) if getattr(primitive, "text_layout", None) is not None else []
            try:
                png = bytes(resvg_py.svg_to_bytes(svg_string=etree.tostring(halo_root, encoding="unicode"),
                                                  dpi=96, font_files=font_files,
                                                  skip_system_fonts=True))
            except Exception as error:
                fail("E_RENDER_RASTERIZER_IDENTITY", f"resvg-py could not rasterize closed PDF glow scene_id={scene_id!r}: {error}")

            # Move overall opacity and clip to a shared compositing wrapper;
            # descendant alpha remains in the halo source and original source.
            wrapper_attrib = {}
            for name in ("opacity", "clip-path"):
                value = composite_owner.attrib.pop(name, None)
                if value is not None:
                    wrapper_attrib[name] = value
            owner.attrib.pop("filter", None)
            parent = composite_owner.getparent()
            if parent is None:
                fail("E_PRESENTATION_PRIMITIVE_INVALID", f"PDF glow scene_id={scene_id!r} filter owner is the SVG root")
            position = parent.index(composite_owner)
            parent.remove(composite_owner)
            wrapper = etree.Element(f"{{{_SVG_NS}}}g", attrib=wrapper_attrib)
            parent.insert(position, wrapper)
            etree.SubElement(wrapper, f"{{{_SVG_NS}}}image", x=str(x0), y=str(y0),
                                     width=str(x1 - x0), height=str(y1 - y0),
                                     preserveAspectRatio="none",
                                     href="data:image/png;base64," + b64encode(png).decode("ascii"),
                                     **{"data-pdf-glow": str(scene_id)})
            wrapper.append(composite_owner)
    return etree.tostring(root, encoding="utf-8")
