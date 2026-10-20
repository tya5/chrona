"""Generate a 150-task terse plan: 10 groups x 15 tasks, chains plus cross-group links."""
import random

random.seed(9)
lines = [
    "terse 0.1",
    'project big "Platform programme" calendar office',
    "calendar office mon-fri except 2026-12-25 2027-01-01",
    "",
    'kick "Kickoff" gate 2026-11-02',
]
names = []
for g in range(10):
    lines.append(f'grp{g} "Workstream {g + 1}" group')
    for t in range(15):
        n = f"w{g}t{t}"
        deps = []
        if t == 0:
            deps.append("kick" if g == 0 else f"w{g - 1}t{random.randint(2, 8)}")
        else:
            deps.append(f"w{g}t{t - 1}")
            if t > 3 and random.random() < 0.35:
                deps.append(f"w{g}t{random.randint(0, t - 2)}")
            if g > 0 and random.random() < 0.25:
                deps.append(f"w{random.randint(0, g - 1)}t{random.randint(0, 14)}")
        amt = random.randint(2, 9)
        lines.append(f'  {n} "Task {g + 1}.{t + 1} {random.choice(["design", "build", "review", "test", "integrate"])}" task {amt}wd after {", ".join(deps)}')
        names.append(n)
lines.append('golive "Go-live" gate after ' + ", ".join(f"w{g}t14" for g in range(10)))
open(__file__.rsplit("/", 1)[0] + "/big.chrona", "w").write("\n".join(lines) + "\n")
print(len(names), "tasks")
