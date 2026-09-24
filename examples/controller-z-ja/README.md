# Controller Z Japanese translation register

This is a translated presentation register for Controller Z, not a different
schedule or semantic model. It pins the optional `chrona-fonts-noto-cjk`
provider and `ja-JP` locale so the long Japanese title, table labels, timeline
labels, and axis formatting are reproducible from declared metrics. SVG is the
portable committed evidence; PNG/PDF require the same optional provider and
are exercised by the CJK target tests and CI matrix.
