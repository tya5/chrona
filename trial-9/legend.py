"""Print legend labels (source role -> text) of rendered SVGs."""
import sys
import xml.etree.ElementTree as ET

for path in sys.argv[1:]:
    rows = []
    for el in ET.parse(path).iter():
        if el.get("data-purpose") == "legend-label":
            rows.append(f"{el.get('data-source-ref','?').split(':')[0]}={''.join(el.itertext()).strip()}")
    print(path.split("/")[-1], "|", "; ".join(rows))
