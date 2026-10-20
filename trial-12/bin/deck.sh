T=/Users/yasudatetsuya/Workspace/chrona_dev/reviewer/.claude/worktrees/agent-a1c9f5eaa0d4d70c5/.trial12
M=${1:-deck}
for s in exec focus network compare; do
  rm -rf $T/${M}out/$s; mkdir -p $T/${M}out/$s
  start=$(date +%s.%N 2>/dev/null || python3 -c 'import time;print(time.time())')
  /usr/bin/time -p $T/venv/bin/chrona materialize $T/$M/manifest.yaml --slide $s --output $T/${M}out/$s --write > $T/${M}out/$s.stdout 2> $T/${M}out/$s.stderr
  echo "$s exit=$? $(grep real $T/${M}out/$s.stderr) $(head -c 400 $T/${M}out/$s.stdout)"
done
