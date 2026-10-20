"""Print SVG texts containing any of the given keys: grep_texts.py KEYS(comma) FILE..."""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import latin

keys = sys.argv[1].split(",")
for path in sys.argv[2:]:
    print("==", path, [t for t in latin.texts(path) if any(k in t for k in keys)])
