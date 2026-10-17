"""PDF-only isolated opacity over completed vector paint, without rasterization."""
from __future__ import annotations

from copy import deepcopy
from io import BytesIO
from math import isfinite


PDF_OPACITY_GRAMMAR = "pdf-isolated-opacity-v2"
_NON_PAINT = frozenset({"defs", "title", "desc", "metadata", "style"})


def render_pdf_vector(svg: bytes, *, font_map: object, preserve_image_alpha: bool = False) -> bytes:
    """Serialize SVG's composed opacity using PDF transparency Form XObjects.

    svglib supports channel alpha but ignores overall opacity. Applying alpha
    to each child would double-paint overlaps. Forms isolate the completed group
    instead. Fragment wrappers retain the original transforms, styles and clips;
    no placement, font selection or measurement is performed here. The private
    glow path can request decoded RGBA images as PDF soft masks.
    """
    from lxml import etree
    from reportlab.graphics import renderPDF
    from reportlab.graphics.renderbase import renderScaledDrawing
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfdoc
    from reportlab.pdfgen.canvas import Canvas
    from svglib.svglib import svg2rlg

    root = etree.fromstring(svg)

    def tag(node):
        return node.tag.rsplit("}", 1)[-1]

    def alpha(node):
        value = float(node.get("opacity", "1"))
        if not isfinite(value) or not 0 <= value <= 1:
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID: PDF opacity requires a finite value in [0,1]")
        return value

    def translucent(node):
        return tag(node) not in _NON_PAINT and (alpha(node) != 1 or any(translucent(child) for child in node))

    drawing = svg2rlg(BytesIO(svg), font_map=font_map)
    has_transparency = any(translucent(child) for child in root)
    if not has_transparency and not preserve_image_alpha:
        return renderPDF.drawToString(drawing)

    output = BytesIO()
    canvas = Canvas(output, pagesize=(drawing.width, drawing.height), invariant=1)
    canvas.setTitle("")

    class _PdfImageAlphaRenderer(renderPDF._PDFRenderer):
        """Keep decoded RGBA images on ReportLab's soft-mask image path."""

        def drawImage(self, image):
            source = image.path
            if hasattr(source, "mode"):
                self._canvas.drawImage(ImageReader(source), image.x, image.y,
                                       image.width, image.height, mask="auto")
            else:
                super().drawImage(image)

    def draw_vector(converted):
        if preserve_image_alpha:
            _PdfImageAlphaRenderer().draw(renderScaledDrawing(converted), canvas, 0, 0)
        else:
            renderPDF.draw(converted, canvas, 0, 0)

    if not has_transparency:
        draw_vector(drawing)
        canvas.showPage()
        canvas.save()
        return output.getvalue()

    definitions = [child for child in root if tag(child) in _NON_PAINT]
    form_index = 0

    def wrapper(node):
        result = node.makeelement(node.tag, dict(node.attrib), nsmap=node.nsmap)
        for child in node:
            if tag(child) in _NON_PAINT:
                result.append(deepcopy(child))
        return result

    def emit(nodes, ancestors):
        if not nodes:
            return
        fragment = root.makeelement(root.tag, dict(root.attrib), nsmap=root.nsmap)
        for definition in definitions:
            fragment.append(deepcopy(definition))
        parent = fragment
        for ancestor in ancestors:
            child = deepcopy(ancestor)
            parent.append(child)
            parent = child
        for node in nodes:
            parent.append(deepcopy(node))
        converted = svg2rlg(BytesIO(etree.tostring(fragment)), font_map=font_map)
        draw_vector(converted)

    def sequence(nodes, ancestors=()):
        nonlocal form_index
        pending = []
        for node in nodes:
            if tag(node) in _NON_PAINT:
                continue
            opacity = alpha(node)
            if opacity != 1:
                emit(pending, ancestors)
                pending = []
                form_index += 1
                name = f"chrona-opacity-{form_index}"
                opaque = deepcopy(node)
                opaque.attrib.pop("opacity", None)
                canvas.beginForm(name, 0, 0, drawing.width, drawing.height)
                canvas.setFillAlpha(1)
                canvas.setStrokeAlpha(1)
                sequence((opaque,), ancestors)
                # endForm accepts a completed PDF stream. Supplying its Group
                # dictionary preserves isolated compositing via public form APIs.
                group = pdfdoc.PDFDictionary({"S": pdfdoc.PDFName("Transparency"),
                                              "I": pdfdoc.PDFtrue, "K": pdfdoc.PDFfalse})
                stream = pdfdoc.PDFStream(pdfdoc.PDFDictionary({"Group": group}),
                                          content=canvas.getCurrentPageContent())
                resources = pdfdoc.PDFResourceDictionary()
                resources.basicFonts()
                resources.allProcs()
                states = canvas._extgstate.getState()
                if states:
                    resources.ExtGState = states
                forms = canvas._doc.xobjDict(canvas._formsinuse)
                if forms:
                    resources.XObject = forms
                if canvas._colorsUsed:
                    resources.setColorSpace(canvas._colorsUsed)
                if canvas._shadingUsed:
                    resources.setShading(canvas._shadingUsed)
                canvas.endForm(Contents=stream, Resources=resources)
                canvas.saveState()
                canvas.setFillAlpha(opacity)
                canvas.setStrokeAlpha(opacity)
                canvas.doForm(name)
                canvas.restoreState()
            elif any(translucent(child) for child in node):
                emit(pending, ancestors)
                pending = []
                sequence(node, (*ancestors, wrapper(node)))
            else:
                pending.append(node)
        emit(pending, ancestors)

    sequence(root)
    canvas.showPage()
    canvas.save()
    return output.getvalue()
