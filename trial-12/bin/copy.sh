T=/Users/yasudatetsuya/Workspace/chrona_dev/reviewer/.claude/worktrees/agent-a1c9f5eaa0d4d70c5/.trial12
export PATH=$T/venv/bin:$PATH
for p in target-b yuya mission-light chrona-default-draft marquee; do
  chrona preset copy $p --output $T/looks/$p >/dev/null
done
