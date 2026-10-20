"""Print the y of chosen texts of an SVG, top to bottom: ytexts.py FILE TEXT..."""
import re, sys
svg = open(sys.argv[1], encoding="utf-8").read()
want = set(sys.argv[2:])
found = []
for attrs, body in re.findall(r"<text([^>]*)>(.*?)</text>", svg, flags=re.S):
    t = re.sub(r"<[^>]+>", "", body)
    if t in want:
        found.append((float(re.search(r'\by="([^"]*)"', attrs)[1]), t))
print("top to bottom:", " , ".join(f"{t} (y={y:g})" for y, t in sorted(found)))
