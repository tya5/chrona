"""List visible texts with Latin letters in rendered SVGs (ignores authored plan titles)."""
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter

AUTHORED = {"API 設計", "CI/CD 整備"}


def texts(path):
    tree = ET.parse(path)
    out = []
    for el in tree.iter():
        if el.tag.endswith("}text") or el.tag == "text":
            s = "".join(el.itertext()).strip()
            if s:
                out.append(s)
    return out


if __name__ == "__main__":
  for path in sys.argv[1:]:
      ts = texts(path)
      latin = Counter(t for t in ts if re.search(r"[A-Za-z]", t) and t not in AUTHORED)
      print(f"== {path}: {len(ts)} texts")
      for t, n in sorted(latin.items()):
          print(f"   {n:3d}x {t!r}")
  