"""SVG formatting for a completed portable visual SceneSurface."""
from __future__ import annotations

from html import escape
from hashlib import sha256
from base64 import b64encode

from chrona.core.ports import RenderArtifact
from chrona.presentation.scene.model import (
    BOX_FOLLOWS_TEXT, TEXT_FOLLOWS_BOX, ImageFill, ScenePaint, ScenePrimitive, SceneSurface,
)


def _failure(code: str, detail: str) -> ValueError:
    return ValueError(f"{code}: {detail}")


def _brief(value: object) -> str:
    if isinstance(value, str):
        clipped = value[:64]
        return repr(clipped + ("…" if len(value) > len(clipped) else ""))
    if value is None or isinstance(value, (bool, int, float)):
        return repr(value)
    return f"<{type(value).__name__}>"


def render_v05_svg(surface: SceneSurface, *, viewer_fit: bool = True) -> str:
    """Serialize completed primitives only; Theme and Scheme are not renderer inputs.

    ``viewer_fit`` writes the completed viewer-fit facts of a box role (#1050): ``textLength`` on each line of a
    ``text-follows-box`` text and a filter group for a ``box-follows-text`` box. A fixed-font output (PNG, PDF) is
    produced with it off, and then every Scene fact is ignored: the result is the ``raw`` serialization.
    """
    if surface.canvas_paint is None or surface.canvas_paint.fill is None:
        raise _failure("E_PRESENTATION_PAINT_INVALID", "canvasPaint.fill is required for the SVG canvas background")
    if surface.canvas_bounds is None:
        raise _failure("E_PRESENTATION_RENDER_INPUT", "SceneSurface.canvasBounds is required for SVG viewBox and viewport")
    canvas_inline, canvas_block, width, height = surface.canvas_bounds
    def number(value: float) -> str: return f"{value:.3f}".rstrip("0").rstrip(".")
    def completed(node: ScenePrimitive) -> ScenePaint:
        if node.paint is None: raise _failure("E_PRESENTATION_PAINT_INVALID", f"scene_id={node.scene_id!r} has no completed paint")
        return node.paint
    def path_data(node: ScenePrimitive) -> str:
        if not node.path_commands: return "M" + "L".join(f"{number(px)} {number(py)}" for px, py in node.points)
        parts: list[str] = []
        for command in node.path_commands:
            if command.kind == "move": parts.append("M" + " ".join(number(value) for value in command.points[0]))
            elif command.kind == "line": parts.append("L" + " ".join(number(value) for value in command.points[0]))
            elif command.kind == "quadratic": parts.append("Q" + " ".join(number(value) for point in command.points for value in point))
            else: raise _failure("E_PRESENTATION_PRIMITIVE_INVALID", f"scene_id={node.scene_id!r} path command={command.kind!r}; expected move, line, or quadratic")
        return "".join(parts)
    def polyline_data(points: tuple[tuple[float, float], ...]) -> str:
        return "M" + "L".join(f"{number(px)} {number(py)}" for px, py in points)
    def attrs(paint: ScenePaint, *, fill: bool, stroke: bool,
              fill_override: str | None = None, opacity: bool = True,
              effects: bool = True) -> str:
        result = [f'opacity="{number(paint.opacity)}"'] if opacity else []
        if fill:
            if paint.fill is None: raise _failure("E_PRESENTATION_PAINT_INVALID", "SVG fill serialization was requested but completed paint.fill is absent")
            value = paint.fill
            if paint.gradient is not None:
                value = f"url(#{gradient_id(paint)})"
            if paint.radial_gradient is not None:
                value = f"url(#{radial_gradient_id(paint)})"
        else:
            value = fill_override if fill_override is not None else "none"
        result.append(f'fill="{escape(value, quote=True)}"')
        if stroke:
            if paint.stroke is None or paint.stroke_width is None: raise _failure("E_PRESENTATION_PAINT_INVALID", f"SVG stroke serialization requires paint.stroke and paint.stroke_width; received stroke={_brief(paint.stroke)}, stroke_width={_brief(paint.stroke_width)}")
            result.extend((f'stroke="{escape(paint.stroke, quote=True)}"', f'stroke-width="{number(paint.stroke_width)}"'))
            if paint.dash: result.append(f'stroke-dasharray="{" ".join(number(value) for value in paint.dash)}"')
            if paint.stroke_finish is not None:
                result.extend((f'stroke-linecap="{paint.stroke_finish.line_cap}"', f'stroke-linejoin="{paint.stroke_finish.line_join}"'))
        if effects and paint.shadow is not None:
            result.append(f'filter="url(#{shadow_id(paint)})"')
        if effects and paint.glow is not None:
            result.append(f'filter="url(#{glow_id(paint)})"')
        return " ".join(result)
    def stop_opacity(gradient: object, index: int) -> str:
        opacities = gradient.stop_opacities
        return "" if opacities is None else f' stop-opacity="{number(opacities[index])}"'
    def gradient_id(paint: ScenePaint) -> str:
        assert paint.gradient is not None
        identity = (paint.gradient.start, paint.gradient.end, paint.gradient.stops)
        if paint.gradient.stop_opacities is not None: identity += (paint.gradient.stop_opacities,)
        payload = repr(identity).encode()
        return "gradient-" + sha256(payload).hexdigest()[:12]
    def radial_gradient_id(paint: ScenePaint) -> str:
        assert paint.radial_gradient is not None
        return "radial-gradient-" + sha256(repr(paint.radial_gradient).encode()).hexdigest()[:12]
    def canvas_overlay_clip_id() -> str:
        return "canvas-overlay-clip-" + sha256(repr(surface.canvas_bounds).encode()).hexdigest()[:12]
    def shadow_id(paint: ScenePaint) -> str:
        assert paint.shadow is not None
        return "shadow-" + sha256(repr(paint.shadow).encode()).hexdigest()[:12]
    def glow_id(paint: ScenePaint) -> str:
        assert paint.glow is not None
        return "glow-" + sha256(repr(paint.glow).encode()).hexdigest()[:12]
    def fit_filter_id(paint: ScenePaint) -> str:
        return "fit-" + sha256(repr((paint.fill, paint.opacity)).encode()).hexdigest()[:12]
    def stroke_clip_id(node: ScenePrimitive) -> str:
        return "stroke-clip-" + sha256(repr((node.scene_id, node.stroke_clip)).encode()).hexdigest()[:12]
    def commands_data(commands: tuple[object, ...]) -> str:
        parts: list[str] = []
        for command in commands:
            if command.kind == "move": parts.append("M" + " ".join(number(value) for value in command.points[0]))
            elif command.kind == "line": parts.append("L" + " ".join(number(value) for value in command.points[0]))
            elif command.kind == "quadratic": parts.append("Q" + " ".join(number(value) for point in command.points for value in point))
            else: raise _failure("E_PRESENTATION_PRIMITIVE_INVALID", f"Scene path command={command.kind!r}; expected move, line, or quadratic")
        return "".join(parts)
    def marker_id(color: str, geometry: object) -> str:
        identity = ((color, geometry) if geometry.angle_degrees is None
                    else (color, geometry, geometry.angle_degrees))
        if geometry.physical_units:
            identity = (*identity, "userSpaceOnUse", geometry.stroke_width)
        return "marker-" + sha256(repr(identity).encode()).hexdigest()[:12]
    def pattern_id(geometry: object, paint: ScenePaint) -> str:
        if geometry.primitives:
            payload = repr((geometry, paint.stroke, paint.fill, paint.opacity))
        else:
            # Preserve the v0.6 identifier byte-for-byte even though the typed
            # PatternGeometry now also carries optional v0.7 fields.
            legacy = (f"PatternGeometry(tile_inline_size={geometry.tile_inline_size!r}, "
                      f"tile_block_size={geometry.tile_block_size!r}, "
                      f"angle_degrees={geometry.angle_degrees!r}, strokes={geometry.strokes!r})")
            payload = f"({legacy}, {paint.stroke!r}, {paint.opacity!r})"
        return "pattern-" + sha256(payload.encode()).hexdigest()[:12]
    def catalog_pattern_body(pattern: object, paint: ScenePaint) -> str:
        if paint.stroke is None or (paint.fill is not None and paint.opacity != 1):
            raise _failure("E_PRESENTATION_PAINT_INVALID", f"catalogue pattern requires a stroke color and opaque substrate when fill is present; stroke={_brief(paint.stroke)}, fill_present={paint.fill is not None}, opacity={_brief(paint.opacity)}")
        ink = escape(paint.stroke, quote=True)
        parts = []
        if paint.fill is not None:
            substrate = escape(paint.fill, quote=True)
            parts.append(f'<rect x="0" y="0" width="{number(pattern.tile_inline_size)}" height="{number(pattern.tile_block_size)}" fill="{substrate}"/>')
        for item in pattern.primitives:
            if item.kind == "circle":
                channel = item.fill_channel or "ink"
                if channel == "ink":
                    fill = ink
                elif channel == "substrate":
                    if paint.fill is None:
                        raise ValueError(
                            f"E_PRESENTATION_PAINT_INVALID: pattern circle at ({number(item.cx)}, {number(item.cy)}) "
                            "requests fillChannel='substrate' but its completed ScenePaint has no fill; bind a role fill"
                        )
                    fill = escape(paint.fill, quote=True)
                elif channel == "none":
                    fill = "none"
                else:
                    raise ValueError(
                        f"E_PRESENTATION_PRIMITIVE_INVALID: pattern circle at ({number(item.cx)}, {number(item.cy)}) "
                        f"has unsupported fillChannel {channel!r}; expected 'ink', 'substrate', or 'none'"
                    )
                appearance = f'fill="{fill}"'
                if item.stroke_width is not None:
                    if paint.stroke is None:
                        raise ValueError(
                            f"E_PRESENTATION_PAINT_INVALID: pattern circle at ({number(item.cx)}, {number(item.cy)}) "
                            f"has strokeWidth={number(item.stroke_width)} but its completed ScenePaint has no stroke; "
                            "bind a role stroke or omit strokeWidth"
                        )
                    appearance += (f' stroke="{ink}" stroke-width="{number(item.stroke_width)}"')
                parts.append(f'<circle cx="{number(item.cx)}" cy="{number(item.cy)}" r="{number(item.radius)}" {appearance}/>')
            elif item.kind == "rect":
                parts.append(f'<rect x="{number(item.x)}" y="{number(item.y)}" width="{number(item.inline_size)}" height="{number(item.block_size)}" fill="{ink}"/>')
            elif item.kind == "path":
                commands = []
                for command in item.commands:
                    if command.kind == "close":
                        commands.append("Z")
                    elif command.kind in {"move", "line"}:
                        commands.append(("M" if command.kind == "move" else "L") +
                                        " ".join(number(value) for value in command.points[0]))
                    elif command.kind == "quadratic":
                        commands.append("Q" + " ".join(number(value) for point in command.points for value in point))
                    else:
                        raise _failure("E_PRESENTATION_PRIMITIVE_INVALID", f"catalogue pattern path command={command.kind!r}; expected close, move, line, or quadratic")
                shape = f'd="{"".join(commands)}"'
                if item.paint == "fill":
                    parts.append(f'<path {shape} fill="{ink}"/>')
                elif item.paint == "stroke":
                    parts.append(f'<path {shape} fill="none" stroke="{ink}" stroke-width="{number(item.stroke_width)}" stroke-linecap="{item.line_cap}" stroke-linejoin="{item.line_join}"/>')
                else:
                    raise _failure("E_PRESENTATION_PRIMITIVE_INVALID", f"catalogue pattern path paint={_brief(item.paint)}; expected 'fill' or 'stroke'")
            else:
                raise _failure("E_PRESENTATION_PRIMITIVE_INVALID", f"catalogue pattern primitive kind={item.kind!r}; expected circle, rect, or path")
        return "".join(parts)
    marker_pairs = {(completed(node).stroke, marker) for node in surface.primitives if node.kind == "Path"
                    for marker in (node.marker_start, node.marker_end) if marker}
    patterns = {(node.pattern, completed(node)) for node in surface.primitives if node.pattern}
    radial_gradients = {radial_gradient_id(completed(node)): completed(node).radial_gradient
                        for node in surface.primitives if completed(node).radial_gradient is not None}
    canvas_overlay_nodes = tuple(node for node in surface.primitives
                                 if node.visual_role in {"canvas-overlay", "canvas-overlay-gradient"})
    has_links = any(node.href is not None for node in surface.primitives)
    ns = ' xmlns:xlink="http://www.w3.org/1999/xlink"' if has_links else ""
    view_box = f"{number(canvas_inline)} {number(canvas_block)} {number(width)} {number(height)}"
    canvas_origin = (f' x="{number(canvas_inline)}" y="{number(canvas_block)}"'
                     if canvas_inline or canvas_block else "")
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg"{ns} width="{number(width)}" height="{number(height)}" viewBox="{view_box}" role="img">',
             f'<rect{canvas_origin} width="{number(width)}" height="{number(height)}" {attrs(surface.canvas_paint, fill=True, stroke=False)}/>']
    paints = (surface.canvas_paint, *(completed(node) for node in surface.primitives))
    gradients = {gradient_id(paint): paint.gradient for paint in paints if paint.gradient}
    shadows = {shadow_id(paint): paint.shadow for paint in paints if paint.shadow}
    glows = {glow_id(paint): paint.glow for paint in paints if paint.glow}
    stroke_clip_nodes = {stroke_clip_id(node): node for node in surface.primitives if node.stroke_clip is not None}
    clip_hosts = {node.scene_id: node for node in surface.primitives
                  if any(item.clip_source_id == node.scene_id for item in surface.primitives)}
    # A box that follows its text (#1050) is painted by one flood filter per distinct fill, over the group's
    # bounding box; its text is serialised inside that group, in the box's own paint position.
    followed_by = ({node.text_layout.fit.box_id: node for node in surface.primitives
                    if node.text_layout is not None and node.text_layout.fit is not None
                    and node.text_layout.fit.mode == BOX_FOLLOWS_TEXT} if viewer_fit else {})
    fit_floods = {fit_filter_id(completed(node)): completed(node) for node in surface.primitives
                  if viewer_fit and node.viewer_fit == BOX_FOLLOWS_TEXT and completed(node).fill is not None}
    if (marker_pairs or patterns or gradients or radial_gradients or shadows or glows
            or clip_hosts or fit_floods or stroke_clip_nodes or canvas_overlay_nodes):
        definitions: list[str] = []
        if canvas_overlay_nodes:
            x, y, w, h = surface.canvas_bounds
            definitions.append(f'<clipPath id="{canvas_overlay_clip_id()}" clipPathUnits="userSpaceOnUse"><rect x="{number(x)}" y="{number(y)}" width="{number(w)}" height="{number(h)}"/></clipPath>')
        for color, marker in sorted(marker_pairs, key=lambda pair: (
                repr(pair), pair[1].angle_degrees is not None, pair[1].angle_degrees or 0.0,
                pair[1].physical_units, pair[1].stroke_width or 0.0)):
            if color is None or marker is None: raise _failure("E_PRESENTATION_PRIMITIVE_INVALID", f"Path marker requires completed stroke color and marker geometry; color={color!r}, marker_present={marker is not None}")
            appearance = (f'fill="{escape(color, quote=True)}"' if marker.paint_mode == "fill"
                          else f'fill="none" stroke="{escape(color, quote=True)}"')
            units = ''
            if marker.physical_units:
                units = ' markerUnits="userSpaceOnUse" overflow="visible"'
                if marker.paint_mode == "stroke":
                    appearance += (f' stroke-width="{number(marker.stroke_width)}"'
                                   ' stroke-linecap="butt" stroke-linejoin="miter" stroke-miterlimit="4"')
            axis_value = "auto" if marker.angle_degrees is None else number(marker.angle_degrees)
            definitions.append(f'<marker id="{marker_id(color, marker)}" viewBox="0 0 {number(marker.head_length)} {number(marker.head_width)}" refX="{number(marker.head_length - marker.attachment_offset)}" refY="{number(marker.head_width / 2)}" markerWidth="{number(marker.head_length)}" markerHeight="{number(marker.head_width)}" orient="{axis_value}"{units}><path d="{commands_data(marker.outline)}" {appearance}/></marker>')
        for pattern, paint in sorted(patterns, key=repr):
            if pattern.primitives:
                if pattern.origin is None or pattern.clip_bounds is None:
                    raise _failure("E_PRESENTATION_PRIMITIVE_INVALID", "catalogue pattern requires completed origin and clip_bounds")
                transform = (f'translate({number(pattern.origin[0])} {number(pattern.origin[1])}) '
                             f'rotate({number(pattern.angle_degrees)} '
                             f'{number(pattern.tile_inline_size / 2)} {number(pattern.tile_block_size / 2)})')
                definitions.append(f'<pattern id="{pattern_id(pattern, paint)}" patternUnits="userSpaceOnUse" x="0" y="0" width="{number(pattern.tile_inline_size)}" height="{number(pattern.tile_block_size)}" patternTransform="{transform}">{catalog_pattern_body(pattern, paint)}</pattern>')
            else:
                if paint.stroke is None or paint.stroke_width is None: raise _failure("E_PRESENTATION_PAINT_INVALID", f"legacy line pattern requires paint.stroke and paint.stroke_width; received stroke={_brief(paint.stroke)}, stroke_width={_brief(paint.stroke_width)}")
                strokes = "".join(f'<line x1="{number(stroke.start[0])}" y1="{number(stroke.start[1])}" x2="{number(stroke.end[0])}" y2="{number(stroke.end[1])}" opacity="{number(paint.opacity)}" fill="none" stroke="{escape(paint.stroke, quote=True)}" stroke-width="{number(stroke.width)}"/>' for stroke in pattern.strokes)
                definitions.append(f'<pattern id="{pattern_id(pattern, paint)}" patternUnits="userSpaceOnUse" width="{number(pattern.tile_inline_size)}" height="{number(pattern.tile_block_size)}" patternTransform="rotate({number(pattern.angle_degrees)})">{strokes}</pattern>')
        for identifier, gradient in sorted(gradients.items()):
            assert gradient is not None
            definitions.append(f'<linearGradient id="{identifier}" gradientUnits="userSpaceOnUse" x1="{number(gradient.start[0])}" y1="{number(gradient.start[1])}" x2="{number(gradient.end[0])}" y2="{number(gradient.end[1])}">' + "".join(f'<stop offset="{number(position * 100)}%" stop-color="{escape(color, quote=True)}"{stop_opacity(gradient, index)}/>' for index, (position, color) in enumerate(gradient.stops)) + '</linearGradient>')
        for identifier, radial in sorted(radial_gradients.items()):
            assert radial is not None
            cx, cy = radial.center
            rx, ry = radial.radii
            transform = f'translate({number(cx)} {number(cy)}) scale({number(rx)} {number(ry)})'
            stops = "".join(f'<stop offset="{number(stop.offset * 100)}%" stop-color="{escape(stop.color, quote=True)}" stop-opacity="{number(stop.opacity)}"/>' for stop in radial.stops)
            definitions.append(f'<radialGradient id="{identifier}" gradientUnits="userSpaceOnUse" cx="0" cy="0" r="1" gradientTransform="{transform}">{stops}</radialGradient>')
        for identifier, shadow in sorted(shadows.items()):
            assert shadow is not None
            definitions.append(f'<filter id="{identifier}"><feDropShadow dx="{number(shadow.offset_x)}" dy="{number(shadow.offset_y)}" stdDeviation="{number(shadow.blur)}" flood-color="{escape(shadow.color, quote=True)}" flood-opacity="{number(shadow.opacity)}"/></filter>')
        for identifier, glow in sorted(glows.items()):
            assert glow is not None
            x, y, w, h = glow.region
            definitions.append(
                f'<filter id="{identifier}" filterUnits="userSpaceOnUse" x="{number(x)}" y="{number(y)}" '
                f'width="{number(w)}" height="{number(h)}"><feGaussianBlur in="SourceAlpha" stdDeviation="{number(glow.blur)}" result="halo-blur"/>'
                f'<feFlood flood-color="{escape(glow.color, quote=True)}" flood-opacity="{number(glow.opacity)}"/>'
                '<feComposite in2="halo-blur" operator="in" result="halo"/>'
                '<feMerge><feMergeNode in="halo"/><feMergeNode in="halo"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
        for identifier, node in sorted(stroke_clip_nodes.items()):
            clip = node.stroke_clip
            assert clip is not None
            rx = f' rx="{number(node.corner_radius)}" ry="{number(node.corner_radius)}"' if node.corner_radius else ""
            if node.kind == "Rect":
                x, y, w, h = node.bounds
                contour = f'<rect x="{number(x)}" y="{number(y)}" width="{number(w)}" height="{number(h)}"{rx}/>'
            else:
                if not clip.outline:
                    raise ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: aligned {node.kind} {node.scene_id!r} requires a completed contour")
                contour = f'<path d="{commands_data(clip.outline)}"/>'
            background = "black" if not clip.outside else "white"
            foreground = "white" if not clip.outside else "black"
            x, y, w, h = clip.region
            definitions.append(
                f'<mask id="{identifier}" maskUnits="userSpaceOnUse" maskContentUnits="userSpaceOnUse" '
                f'x="{number(x)}" y="{number(y)}" width="{number(w)}" height="{number(h)}" mask-type="luminance">'
                f'<rect x="{number(x)}" y="{number(y)}" width="{number(w)}" height="{number(h)}" fill="{background}"/>'
                f'{contour[:-2]} fill="{foreground}"/></mask>')
        for identifier, paint in sorted(fit_floods.items()):
            definitions.append(
                f'<filter id="{identifier}" x="0" y="0" width="1" height="1"><feFlood flood-color="{escape(paint.fill, quote=True)}" '
                f'flood-opacity="{number(paint.opacity)}" result="bg"/>'
                '<feMerge><feMergeNode in="bg"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
        for identifier, host in sorted(clip_hosts.items()):
            if host.kind not in {"Rect", "Symbol"}:
                raise _failure("E_PRESENTATION_PRIMITIVE_INVALID", f"clip host scene_id={host.scene_id!r} kind={host.kind!r}; expected Rect or Symbol")
            if host.kind == "Rect":
                x, y, w, h = host.bounds
                radius = f' rx="{number(host.corner_radius)}" ry="{number(host.corner_radius)}"' if host.corner_radius else ""
                clip_content = f'<rect x="{number(x)}" y="{number(y)}" width="{number(w)}" height="{number(h)}"{radius}/>'
            else:
                if host.symbol is None:
                    raise _failure("E_PRESENTATION_PRIMITIVE_INVALID", f"clip host scene_id={host.scene_id!r} has no completed Symbol geometry")
                clip_content = f'<path d="{commands_data(host.symbol.outline)}"/>'
            definitions.append(f'<clipPath id="clip-{escape(identifier, quote=True)}">{clip_content}</clipPath>')
        parts.append("<defs>" + "".join(definitions) + "</defs>")
    rendered: list[tuple[ScenePrimitive, str]] = []
    def append(node: ScenePrimitive, content: str) -> None:
        rendered.append((node, content))
    def link(node: ScenePrimitive, content: str) -> str:
        if node.href is None:
            return content
        title = f' xlink:title="{escape(node.link_title, quote=True)}"' if node.link_title is not None else ""
        return f'<a href="{escape(node.href, quote=True)}" target="_top"{title}>{content}</a>'
    def icon_path(path: object) -> str:
        values: list[str] = []
        for kind, points in path.commands:
            glyph = {"move": "M", "line": "L", "quadratic": "Q", "cubic": "C", "close": "Z"}.get(kind)
            if glyph is None: raise _failure("E_PRESENTATION_PRIMITIVE_INVALID", f"icon path command={kind!r}; expected move, line, quadratic, cubic, or close")
            values.append(glyph if glyph == "Z" else glyph + " ".join(f"{number(px)} {number(py)}" for px, py in points))
        return "".join(values)

    def icon_appearance(path: object) -> str:
        if path.fill is not None and path.stroke is None:
            return f'fill="{escape(path.fill, quote=True)}" opacity="{number(path.opacity)}"'
        if path.fill is None and path.stroke is not None and path.stroke_width is not None:
            return (f'fill="none" opacity="{number(path.opacity)}" stroke="{escape(path.stroke, quote=True)}" '
                    f'stroke-width="{number(path.stroke_width)}" stroke-linecap="{path.line_cap}" stroke-linejoin="{path.line_join}"')
        raise _failure("E_PRESENTATION_PRIMITIVE_INVALID", f"icon path requires fill-only or stroke-plus-width paint; fill_present={path.fill is not None}, stroke_present={path.stroke is not None}, stroke_width={_brief(path.stroke_width)}")

    def image_tiles_markup(node: ScenePrimitive, image: ImageFill) -> str:
        """One nested clipping ``<svg>`` per completed nine-slice tile (#465).

        Each tile's source rect becomes that nested viewport's ``viewBox``;
        its destination rect becomes the nested viewport's own position and
        size. ``preserveAspectRatio="none"`` makes the stretch exact, and the
        inner ``<image>`` is drawn at the asset's own native pixel size so the
        viewBox coordinates match the source rect one-to-one. No tile
        boundary, crop, or stretch ratio is computed here -- every number is
        already resolved by Layout/Scene.
        """
        encoded = b64encode(image.payload).decode("ascii")
        view_width, view_height = image.viewport
        tiles = []
        for tile in image.tiles:
            sx, sy, sw, sh = tile.source
            dx, dy, dw, dh = tile.destination
            tiles.append(
                f'<svg x="{number(dx)}" y="{number(dy)}" width="{number(dw)}" height="{number(dh)}" '
                f'viewBox="{number(sx)} {number(sy)} {number(sw)} {number(sh)}" preserveAspectRatio="none">'
                f'<image x="0" y="0" width="{number(view_width)}" height="{number(view_height)}" '
                f'href="data:image/png;base64,{encoded}"/></svg>')
        return (f'<g data-scene-id="{escape(node.scene_id)}-image" '
                f'data-asset-identity="{escape(image.asset_identity, quote=True)}">' + "".join(tiles) + "</g>")

    def text_markup(node: ScenePrimitive) -> str:
        assert node.text_layout is not None and node.baseline is not None
        paint, common = completed(node), (f'data-scene-id="{escape(node.scene_id)}" data-source-ref="{escape(node.source_ref)}" '
                                          f'data-purpose="{escape(node.purpose)}"')
        layout = node.text_layout
        fit = layout.fit if viewer_fit else None
        lines = layout.lines
        # `textLength` lives in the text's own, pre-transform frame; the measured size already contains the compression.
        fitted = ([f' textLength="{number(size / layout.horizontal_scale)}" lengthAdjust="{fit.adjust}"'
                   for size in fit.line_inline_sizes]
                  if fit is not None and fit.mode == TEXT_FOLLOWS_BOX else [""] * len(lines))
        pad = " " * fit.end_pad_spaces if fit is not None and fit.mode == BOX_FOLLOWS_TEXT else ""
        body = (escape(lines[0]) + pad if len(lines) == 1 else "".join(
            f'<tspan x="{number(node.baseline[0])}" dy="{0 if index == 0 else number(layout.font_size * layout.line_height)}"'
            f'{fitted[index]}>{escape(line)}{pad}</tspan>' for index, line in enumerate(lines)))
        single = fitted[0] if len(lines) == 1 else ""
        preserve = ' xml:space="preserve"' if pad else ""
        treatment = " ".join(part for part in (
            (f'letter-spacing="{number(layout.letter_spacing)}"' if layout.letter_spacing != 0 else ""),
            (f'font-variant-numeric="{layout.numeric_spacing}-nums"'),
        ) if part)
        treatment = f" {treatment}" if treatment else ""
        # Compression acts in the text's own frame (about the baseline start), so it is composed after the
        # rotation in the list and applies first (#585).
        steps = ([f"rotate({number(layout.rotation_degrees)} {number(node.baseline[0])} {number(node.baseline[1])})"]
                 if layout.rotation_degrees else [])
        if layout.horizontal_scale != 1:
            scale = layout.horizontal_scale
            steps.append(f"matrix({number(scale)} 0 0 1 {number(node.baseline[0] * (1 - scale))} 0)")
        transform = f' transform="{" ".join(steps)}"' if steps else ""
        markup = (f'<text {common} x="{number(node.baseline[0])}" y="{number(node.baseline[1])}" font-family="{escape(layout.family, quote=True)}" '
                f'font-weight="{layout.weight}" font-size="{number(layout.font_size)}"{transform}{treatment}{single}{preserve} '
                f'{attrs(paint, fill=True, stroke=False, effects=paint.glow is None)}>{body}</text>')
        # Glow.region is already in completed surface coordinates. A filter on the
        # transformed text would transform that region (and the blur) a second time.
        return f'<g filter="url(#{glow_id(paint)})">{markup}</g>' if paint.glow is not None else markup

    for node in (node for _, node in sorted(enumerate(surface.primitives), key=lambda item: (item[1].paint_order, item[0]))):
        overlay_attrs = ""
        if node.visual_role in {"canvas-overlay", "canvas-overlay-gradient"}:
            if node.kind != "Rect" or node.bounds != surface.canvas_bounds:
                raise ValueError(
                    f"E_PRESENTATION_PRIMITIVE_INVALID: canvas overlay {node.scene_id!r} requires kind='Rect' and "
                    f"bounds equal to completed canvasBounds={surface.canvas_bounds!r}; received "
                    f"kind={node.kind!r}, bounds={node.bounds!r}")
            overlay_attrs = f' pointer-events="none" clip-path="url(#{canvas_overlay_clip_id()})"'
        common = (f'data-scene-id="{escape(node.scene_id)}" data-source-ref="{escape(node.source_ref)}" '
                  f'data-purpose="{escape(node.purpose)}"{overlay_attrs}')
        paint, (x, y, w, h) = completed(node), node.bounds
        if node.stroke_clip is not None:
            if (node.kind not in {"Rect", "Symbol", "Path"} or node.viewer_fit == BOX_FOLLOWS_TEXT
                    or paint.wobble is not None or paint.stroke is None or paint.stroke_width is None
                    or paint.stroke_width != node.stroke_clip.stroke_width
                    or node.marker_start is not None or node.marker_end is not None):
                raise ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: aligned {node.scene_id!r} requires Rect/Symbol/Path, matching completed stroke width, and no wobble, box-follows-text or markers")
            clip_attr = (f' clip-path="url(#clip-{escape(node.clip_source_id, quote=True)})"'
                         if node.clip_source_id else "")
            common_group = f'<g {common} opacity="{number(paint.opacity)}"{clip_attr}>'
            content = ""
            if node.kind == "Rect":
                radius = f' rx="{number(node.corner_radius)}" ry="{number(node.corner_radius)}"' if node.corner_radius else ""
                fill_override = f"url(#{pattern_id(node.pattern, paint)})" if node.pattern is not None else None
                if node.pattern is not None and node.pattern.primitives:
                    if (node.pattern.region_bounds != node.bounds or node.pattern.clip_bounds != node.bounds
                            or node.pattern.corner_radius != (node.corner_radius or 0.0)):
                        raise ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: aligned rectangle {node.scene_id!r} pattern bounds/radius must match the completed contour")
                    fill_override = f"url(#{pattern_id(node.pattern, paint)})"
                fill_attr = attrs(paint, fill=paint.fill is not None and fill_override is None,
                                  stroke=False, fill_override=fill_override, opacity=False, effects=False)
                if paint.fill is not None or fill_override is not None:
                    content += (f'<rect x="{number(x)}" y="{number(y)}" width="{number(w)}" height="{number(h)}"'
                                f'{radius} {fill_attr}/>' )
                if paint.image is not None:
                    content += image_tiles_markup(node, paint.image)
                stroke_attrs = attrs(paint, fill=False, stroke=True, opacity=False, effects=False)
                stroke_mask = stroke_clip_id(node)
                content += (f'<rect x="{number(x)}" y="{number(y)}" width="{number(w)}" height="{number(h)}"'
                            f'{radius} mask="url(#{stroke_mask})" {stroke_attrs}/>' )
            else:
                if node.kind == "Symbol":
                    if node.symbol is None or paint.image is not None:
                        raise ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: aligned symbol {node.scene_id!r} requires completed symbol geometry and no image paint")
                    source_data = commands_data(node.symbol.outline)
                else:
                    source_data = path_data(node)
                if paint.fill is not None:
                    fill_attrs = attrs(paint, fill=True, stroke=False, opacity=False, effects=False)
                    content += f'<path d="{source_data}" {fill_attrs}/>'
                stroke_attrs = attrs(paint, fill=False, stroke=True, opacity=False, effects=False)
                contour_data = commands_data(node.stroke_clip.outline) if node.stroke_clip.outline else source_data
                content += (f'<path d="{contour_data}" mask="url(#{stroke_clip_id(node)})" '
                            f'{stroke_attrs}/>' )
            # Keep paint effects on the complete primitive, so fill and stroke receive them once.
            if paint.shadow is not None:
                content = f'<g filter="url(#{shadow_id(paint)})">{content}</g>'
            if paint.glow is not None:
                content = f'<g filter="url(#{glow_id(paint)})">{content}</g>'
            append(node, common_group + content + '</g>')
        elif node.kind == "Rect" and viewer_fit and node.viewer_fit == BOX_FOLLOWS_TEXT:
            text_node = followed_by.get(node.scene_id)
            if text_node is None or text_node.baseline is None:
                raise _failure("E_PRESENTATION_PRIMITIVE_INVALID", f"box-follows-text Rect scene_id={node.scene_id!r} has no linked Text baseline")
            # The invisible rect pins the start, top and bottom to the measured box; the viewer's own text advance and
            # the trailing spaces of every line set the end edge (the filter region is the group's bounding box).
            pin = (f'<rect data-scene-id="{escape(node.scene_id)}-extent" x="{number(x)}" y="{number(y)}" '
                   f'width="{number(max(text_node.baseline[0] - x, 1.0))}" height="{number(h)}" fill="none"/>')
            flood = f' filter="url(#{fit_filter_id(paint)})"' if paint.fill is not None else ""
            append(node, f'<g {common} data-viewer-fit="{BOX_FOLLOWS_TEXT}"{flood}>{pin}{text_markup(text_node)}</g>')
        elif node.kind == "Rect":
            if node.pattern is not None and node.pattern.primitives:
                if (node.pattern.region_bounds != node.bounds or node.pattern.clip_bounds != node.bounds
                        or node.pattern.corner_radius != (node.corner_radius or 0.0)):
                    raise _failure("E_PRESENTATION_PRIMITIVE_INVALID", f"Rect scene_id={node.scene_id!r} catalogue pattern region/clip/radius must match bounds={node.bounds!r}, radius={node.corner_radius!r}")
            appearance = (attrs(paint, fill=False, stroke=not bool(node.pattern.primitives),
                                fill_override=f"url(#{pattern_id(node.pattern, paint)})")
                          if node.pattern is not None else attrs(paint, fill=paint.fill is not None or paint.radial_gradient is not None, stroke=paint.stroke is not None))
            radius = f' rx="{number(node.corner_radius)}" ry="{number(node.corner_radius)}"' if node.corner_radius else ""
            clip = f' clip-path="url(#clip-{escape(node.clip_source_id, quote=True)})"' if node.clip_source_id else ""
            if paint.wobble is not None and paint.wobble.outline:
                # A completed hand-wobble (#588): the outline is drawn verbatim as one closed path.
                if node.pattern is not None or paint.image is not None or node.clip_source_id or not paint.wobble.closed:
                    raise _failure("E_PRESENTATION_PRIMITIVE_INVALID", f"wobbled Rect scene_id={node.scene_id!r} requires a closed outline and no pattern, image, clip, or open outline")
                rect_markup = f'<path {common} d="{polyline_data(paint.wobble.outline[0])}Z" {appearance}/>'
            else:
                rect_markup = f'<rect {common} x="{number(x)}" y="{number(y)}" width="{number(w)}" height="{number(h)}"{radius}{clip} {appearance}/>'
            if paint.image is not None:
                append(node, rect_markup + image_tiles_markup(node, paint.image))
            else:
                append(node, rect_markup)
        elif node.kind == "Text":
            if node.text is None or node.text_layout is None or node.baseline is None: raise _failure("E_PRESENTATION_PRIMITIVE_INVALID", f"Text scene_id={node.scene_id!r} requires text, text_layout, and baseline")
            if viewer_fit and node.text_layout.fit is not None and node.text_layout.fit.mode == BOX_FOLLOWS_TEXT:
                continue  # serialised inside its box's group, above
            append(node, text_markup(node))
        elif node.kind == "Symbol":
            if node.symbol is None or paint.image is not None: raise _failure("E_PRESENTATION_PRIMITIVE_INVALID", f"Symbol scene_id={node.scene_id!r} requires completed symbol geometry and no image paint")
            appearance = attrs(paint, fill=paint.fill is not None, stroke=paint.stroke is not None)
            append(node, f'<path {common} d="{commands_data(node.symbol.outline)}" {appearance}/>')
        elif node.kind == "Path":
            if len(node.points) < 2 or paint.stroke is None: raise _failure("E_PRESENTATION_PRIMITIVE_INVALID", f"Path scene_id={node.scene_id!r} requires at least two points and completed stroke; points={len(node.points)}, stroke_present={paint.stroke is not None}")
            start = f' marker-start="url(#{marker_id(paint.stroke, node.marker_start)})"' if node.marker_start else ""
            end = f' marker-end="url(#{marker_id(paint.stroke, node.marker_end)})"' if node.marker_end else ""
            data = ("".join(polyline_data(polyline) for polyline in paint.wobble.outline)
                    if paint.wobble is not None and paint.wobble.outline else path_data(node))
            append(node, f'<path {common} d="{data}" {attrs(paint, fill=False, stroke=True)}{start}{end}/>')
        elif node.kind == "Icon":
            if node.icon_kind not in {"vector", "raster"} or node.icon_asset_identity is None:
                raise _failure("E_PRESENTATION_PRIMITIVE_INVALID", f"Icon scene_id={node.scene_id!r} requires kind vector/raster and asset identity; kind={node.icon_kind!r}, identity_present={node.icon_asset_identity is not None}")
            accessible = " aria-hidden=\"true\"" if node.icon_decorative else f' role="img" aria-label="{escape(node.icon_alternative or "", quote=True)}"'
            if not node.icon_decorative and not node.icon_alternative: raise _failure("E_PRESENTATION_PRIMITIVE_INVALID", f"Icon scene_id={node.scene_id!r} is non-decorative but has no alternative text")
            if node.icon_kind == "vector":
                if not node.icon_paths: raise _failure("E_PRESENTATION_PRIMITIVE_INVALID", f"vector Icon scene_id={node.scene_id!r} requires at least one completed icon path")
                paths = "".join(f'<path d="{icon_path(path)}" {icon_appearance(path)}/>' for path in node.icon_paths)
                append(node, f'<g {common}{accessible} data-asset-identity="{escape(node.icon_asset_identity, quote=True)}">{paths}</g>')
            else:
                if node.icon_raster is None: raise _failure("E_PRESENTATION_PRIMITIVE_INVALID", f"raster Icon scene_id={node.scene_id!r} requires PNG bytes")
                encoded = b64encode(node.icon_raster).decode("ascii")
                append(node, f'<image {common}{accessible} data-asset-identity="{escape(node.icon_asset_identity, quote=True)}" x="{number(x)}" y="{number(y)}" width="{number(w)}" height="{number(h)}" href="data:image/png;base64,{encoded}"/>')
        else: raise _failure("E_PRESENTATION_PRIMITIVE_INVALID", f"scene_id={node.scene_id!r} has unsupported primitive kind={node.kind!r}")
    for node, content in rendered:
        parts.append(link(node, content))
    mark_purposes = {"planned", "actual", "snapshot", "missingActual", "progress-fill", "icon-mark"}
    interactions = []
    for node, _ in rendered:
        if node.purpose not in mark_purposes or node.href is None:
            continue
        x, y, w, h = node.bounds
        title = f'<title>{escape(node.link_title)}</title>' if node.link_title else ""
        interactions.append(f'<a href="{escape(node.href, quote=True)}" target="_top" data-scene-id="{escape(node.scene_id)}" data-source-ref="{escape(node.source_ref)}" data-purpose="{escape(node.purpose)}"><rect x="{number(x)}" y="{number(y)}" width="{number(w)}" height="{number(h)}" fill="transparent" pointer-events="all"/>{title}</a>')
    if interactions:
        parts.append('<g data-layer="mark-interaction">' + "".join(interactions) + '</g>')
    return "\n".join((*parts, "</svg>")) + "\n"


class V05SvgRenderer:
    target_kind = "svg"

    def __init__(self, *, viewer_fit: bool = True) -> None:
        # Off for a fixed-font output that draws this SVG (PNG, PDF): it is then the `raw` serialization (#1050).
        self._viewer_fit = viewer_fit

    def render(self, surface: object) -> RenderArtifact:
        if not isinstance(surface, SceneSurface): raise _failure("E_PRESENTATION_RENDER_INPUT", f"SVG renderer requires SceneSurface; received {type(surface).__name__}")
        return RenderArtifact("svg", "image/svg+xml", render_v05_svg(surface, viewer_fit=self._viewer_fit).encode("utf-8"),
                              "chrona-svg-v0.5")
