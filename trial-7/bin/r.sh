#!/bin/bash
# usage: r.sh OUTBASE [render args...]  -> runs chrona render, writes OUTBASE.json, prints summary + time
R=/Users/yasudatetsuya/Workspace/chrona_dev/reviewer/.claude/worktrees/agent-a7fe068d9bc0209b1/.venv/bin/chrona
out=$1; shift
s=$(python3 -c 'import time;print(time.time())')
"$R" render "$@" > "$out.json" 2> "$out.err"
rc=$?
e=$(python3 -c 'import time;print(time.time())')
python3 - "$out" "$rc" "$s" "$e" <<'EOF'
import json,sys
out,rc,s,e=sys.argv[1],sys.argv[2],float(sys.argv[3]),float(sys.argv[4])
try:
    d=json.load(open(out+'.json'))
except Exception as ex:
    print(out,'rc',rc,'unparsable',open(out+'.json').read()[:500]); sys.exit()
ws=d.get('warnings',[])
from collections import Counter
print(f"{out} rc={rc} status={d.get('status')} {e-s:.1f}s warnings={len(ws)} {dict(Counter(w['code'] for w in ws))}")
for w in ws[:8]: print('   ',w['code'],w.get('message','')[:200])
for x in d.get('diagnostics',[])[:8]: print('  D',x.get('code'),x.get('message','')[:300])
EOF
