T=/Users/yasudatetsuya/Workspace/chrona_dev/reviewer/.claude/worktrees/agent-a1c9f5eaa0d4d70c5/.trial12
C=$T/venv/bin/chrona
mkdir -p $T/out/serial
cd $T
echo "--- compare target-b w3 without previous-scene"
/usr/bin/time -p $C render w3/project.yaml --view views/compare.yaml --actual w3/actual.yaml --snapshot w0/project.yaml --forecast --preset target-b --output out/serial/cmp-tb-noprev.svg > /dev/null
echo "--- compare target-b w3 with previous-scene"
/usr/bin/time -p $C render w3/project.yaml --view views/compare.yaml --actual w3/actual.yaml --snapshot w0/project.yaml --forecast --preset target-b --previous-scene out/w2/compare.target-b.en-US.scene.json --output out/serial/cmp-tb-prev.svg > /dev/null
echo "--- compare target-b w3 without --forecast"
/usr/bin/time -p $C render w3/project.yaml --view views/compare.yaml --actual w3/actual.yaml --snapshot w0/project.yaml --preset target-b --output out/serial/cmp-tb-nofc.svg > /dev/null
echo "--- compare target-b w3 relations none"
/usr/bin/time -p $C render w3/project.yaml --view views/compare.yaml --actual w3/actual.yaml --snapshot w0/project.yaml --forecast --relations none --preset target-b --output out/serial/cmp-tb-norel.svg > /dev/null
echo "--- compare default w3"
/usr/bin/time -p $C render w3/project.yaml --view views/compare.yaml --actual w3/actual.yaml --snapshot w0/project.yaml --forecast --output out/serial/cmp-def.svg > /dev/null
