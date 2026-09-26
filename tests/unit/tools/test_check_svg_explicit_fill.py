from tools.check_svg_explicit_fill import implicit_fills


def test_svg_checker_skips_clip_geometry_and_rejects_implicit_drawable_fill():
    svg = ('<svg xmlns="http://www.w3.org/2000/svg">'
           '<defs><clipPath id="c"><rect width="2" height="2"/></clipPath></defs>'
           '<rect data-scene-id="bad" width="2" height="2" stroke="#aaa"/>'
           '<path data-scene-id="good" d="M0 0L2 2" fill="none" stroke="#aaa"/>'
           '</svg>')
    assert implicit_fills(svg) == ("bad",)
