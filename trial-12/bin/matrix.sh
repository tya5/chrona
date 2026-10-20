T=/Users/yasudatetsuya/Workspace/chrona_dev/reviewer/.claude/worktrees/agent-a1c9f5eaa0d4d70c5/.trial12
rm -rf $T/out
mkdir -p $T/out
for p in default target-b mission-light yuya; do
  ( $T/venv/bin/python $T/bin/render.py 0,1,2,3 all $p en-US,ja-JP --png > $T/out/log.$p.txt 2>&1 ) &
done
wait
echo done
