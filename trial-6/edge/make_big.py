"""Write a 200-task terse plan (10 groups, chain plus cross-links) for the large-plan timing check."""
import random

random.seed(7)
lines = ['project big "Two hundred tasks"', "calendar standard mon-fri", 'k "Kickoff" gate 2027-01-04']
ids = []
for g in range(10):
    lines.append(f'g{g} "Workstream {g}" group')
    for t in range(20):
        tid = f"t{g}-{t}"
        deps = ["k"] if not ids else [ids[-1]] if t else [f"t{g-1}-0"]
        if len(ids) > 25 and random.random() < 0.15:
            deps.append(random.choice(ids[-25:-2]))
        lines.append(f'  {tid} "Task {g}.{t}" task {random.randint(2, 8)}wd after {", ".join(dict.fromkeys(deps))}')
        ids.append(tid)
lines.append(f'finish "Finish" gate after {", ".join(f"t{g}-19" for g in range(10))}')
open("big.chrona", "w").write("\n".join(lines) + "\n")
