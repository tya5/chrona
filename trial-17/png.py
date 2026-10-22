import glob, pathlib, resvg_py, re
R='../t14/'
fd=[R+'src/chrona/resources/fonts', R+'packages/chrona-fonts-noto-cjk/src/chrona_fonts_noto_cjk/fonts']
for f in sorted(glob.glob('r/*/*.svg')):
    out=f[:-4]+'.png'
    pathlib.Path(out).write_bytes(bytes(resvg_py.svg_to_bytes(svg_path=f, font_dirs=fd, skip_system_fonts=True)))
    head=open(f).read(600)
    m=re.search(r'width="([\d.]+)"[^>]*height="([\d.]+)"',head)
    print(f, m.groups() if m else head[:200])
