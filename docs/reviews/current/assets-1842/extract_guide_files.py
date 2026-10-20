"""Write the files a guide marks with `<!-- chrona:doc-check file: NAME -->` into a directory.

usage: extract_guide_files.py GUIDE.md OUTDIR
"""
import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8")
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
for m in re.finditer(r"<!-- chrona:doc-check file: (?P<name>\S+) -->\s*```[^\n]*\n(?P<body>.*?)\n```", text, re.DOTALL):
    (out / m["name"]).write_text(m["body"] + "\n", encoding="utf-8")
    print("wrote", m["name"])
