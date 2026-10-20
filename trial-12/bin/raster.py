import sys, resvg_py
for svg in sys.argv[1:]:
    data = resvg_py.svg_to_bytes(svg_path=svg)
    open(svg[:-4] + ".png", "wb").write(bytes(data))
    print(svg[:-4] + ".png")
