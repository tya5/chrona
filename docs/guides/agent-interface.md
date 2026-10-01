# Using chrona from an AI coding agent

Chrona ships an agent skill: a short, tested guide that teaches an AI coding agent
(Claude Code and any host that reads the same `SKILL.md` layout) how to plan with
chrona. It is for a user who wants an agent to draft or revise a project plan and
render it, with the dates computed by the `chrona` command and not by the model.

## What the skill is for

- It teaches the authoring model (the Project is the semantic truth, a View selects, a
  Theme paints, a Layout composes, the CLI renders), the draft path that exists today
  (`chrona init`, edit `project.yaml`, `chrona render` with a preset) and the working
  loop (`validate`, `schedule`, `render`, read the diagnostics).
- It lists the diagnostic codes an agent meets and what to change for each, and says when
  Mermaid or a hand-drawn picture is the better tool.
- It does not replace the specification, and it does not add behaviour: it only uses the
  commands the CLI already has.

The skill lives in the repository at [`skills/chrona/`](../../skills/chrona/SKILL.md)
and in the installed package, so it always matches the installed version. Every command
in it is run by the repository's documented-command check, and every diagnostic code it
names is checked against the source, so it cannot rot unnoticed.

## Install it

Copy the packaged skill into the skills directory your agent host reads. The target must
be empty or absent; the command never overwrites. For Claude Code, the project scope is
`.claude/skills/chrona` and the user scope is `~/.claude/skills/chrona`:

```bash
chrona skill copy --output my-agent-skill/chrona
```

## Refresh it after upgrading chrona

The command refuses a non-empty directory (`E_SKILL_OUTPUT_EXISTS`), so a refresh is a new
copy that you compare with the installed one and then move into place:

```bash
chrona skill copy --output my-agent-skill/refreshed
```

Compare `my-agent-skill/chrona` with `my-agent-skill/refreshed` with your usual directory
diff (`diff -r` on macOS and Linux), keep any local edits you want, and replace the old
directory with the new one.
