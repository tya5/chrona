# Issue902 / consolidated814 — real agent-host transcript

Observed 2026-10-20. Host: Codex CLI0.163.0, macOS26.3.1 arm64;
Chrona0.1.0a0 at public `6c97f8d00d40cde8d39737917d54b9f841121b91`,
MCP SDK2.3.0, resvg-py0.5.0, project format timeline/v0.7.
[Published plan](https://github.com/tya5/chrona/issues/902#issuecomment-6284120793).
No product, schema or user configuration was changed. All trial writes were
inside newly created synthetic scratch directories, not the repository/corpus.

Setup: own worktree venv installed with `.[dev,render,mcp]` and the CJK provider.
`codex -a never exec --ignore-user-config --ephemeral --skip-git-repo-check
--sandbox workspace-write --json -C <scratch>` read the committed
[prompt](assets-902-agent-host-2026-10-20/host-prompt.md).
Per-run `-c` overrides (no persistent config):

```toml
[mcp_servers.chrona]
command = "/absolute/worktree/.venv/bin/python"
args = ["-m", "chrona", "mcp", "--workspace", "/absolute/scratch", "--allow-write"]
required = true
[mcp_servers.chrona.tools.create_workspace]
approval_mode = "approve"
[mcp_servers.chrona.tools.apply_authoring_command]
approval_mode = "approve"
```

These are documented [MCP host settings](https://learn.chatgpt.com/docs/extend/mcp?surface=cli),
with [JSONL host event output](https://learn.chatgpt.com/docs/non-interactive-mode).
The initial run without per-tool approval stopped before server mutation;
[preflight events](assets-902-agent-host-2026-10-20/host-preflight.jsonl.gz)
preserve that refusal. The fresh-directory completed run below is preserved
unaltered in [raw host events](assets-902-agent-host-2026-10-20/host-completed.jsonl.gz),
including MCP image bytes, schema errors and the host's final answer. Extract
with `gzip -dc`; no SDK/raw-pipe client supplied these calls.

## Actual host report

Completed through MCP; all four returned PNGs were actually viewed.

Ordered trial calls:

1. `validate_project(project.yaml)` → **rejected**, `E_UNSUPPORTED_CYCLE`, source `/relations/build -> design`; diagnostic named design/build.
2. `apply_patch` → removed only relation `cycle-back`.
3. `validate_project` → **ok**.
4. `schedule_project` → **ok**. Placements (end exclusive): Kickoff `2026-11-02`; Design `2026-11-02`–`2026-11-05`; Build `2026-11-05`–`2026-11-09`.
5. `render_draft` → **ok**. Viewed task table, Design/Build bars, Kickoff diamond and dependency arrows.
6. `create_workspace(guided, default preset)` → **ok**, with requested project and tasks.
7. `validate_workspace`, then `workspace_revision` → **ok**, revision R0 below.
8. `render_workspace` → **ok**. Viewed “Guided host trial,” Design `03 Nov–05 Nov`, Build `09 Nov–12 Nov`, two bars.
9. `apply_authoring_command(host-edit)` → two schema failures before acceptance: target path required filename `workspace.yaml`; version required `chrona/authoring-command/v0.1`. Corrected inline request → **ok/accepted**, R0 → R1.
10. `render_workspace` → **ok**. Viewed “Build extended,” `09 Nov–15 Nov`, longer bar and rescaled axis.
11. `apply_authoring_command(host-inverse)` using returned R1 → **ok/accepted**, restoring original task and R0.
12. `validate_workspace`, then `render_workspace` → **ok**. Viewed original guided appearance again.

Observed revisions:

```text
R0 sha256:43395fcd9e6f8c0710a22012bbf02945373f513df93c3526c03b9fcca737ef9c
R1 sha256:64e1f018d881bcb31717b80a432b93ccf8d48a8a83aa25822a39732ca05c5a42
```

All renders used PNG/image, `1000xauto`:

| Render | contentIdentity | byteLength |
|---|---|---:|
| Draft | `sha256:2476a1c7149ed62648972a36c481cddf9b448c9b1c1ee27b6a0ce0bdb2704e4a` | 23565 |
| Guided initial | `sha256:60d77177bf967553e20200f989c20d12f889a27be2c9455590941ef221e55746` | 16945 |
| Extended | `sha256:4de874bb3250523b5118c9e287a7b058b843446ca43e6d9fbe0338c723878dfb` | 18886 |
| Reverted | `sha256:60d77177bf967553e20200f989c20d12f889a27be2c9455590941ef221e55746` | 16945 |

**Initial and reverted identity and length both match exactly.**

Extended rendering reported `W_LAYOUT_AXIS_LABEL_THINNED` and `W_LAYOUT_AXIS_DENSITY`. Suspected usability defect: its Build label appeared to the left of the bar, crowded against the Plan column. Tool documentation also abbreviated the required command version, causing one failed attempt. No confirmed functional defect; nothing filed or published.

## Coordinator verification and literal acceptance

The coordinator independently viewed the actual extracted images, checked each
PNG hash/length against its MCP envelope, and byte-compared initial/reverted PNGs.
The edited label is clearly separated from the Plan table; the host's crowding
suspicion is **not confirmed** as a defect. The wrong version was copied from
abbreviated tool prose: the canonical schema was correct. Confirmed metadata
usability follow-up: [issue1807](https://github.com/tya5/chrona/issues/1807).
Both malformed requests were refused; the subsequent accepted edit used R0 and
the inverse used returned R1. Restoring content does not delete durable receipts.

| Literal requirement | Status | Evidence |
| --- | --- | --- |
| A transcript (host, version, steps, the rendered image) committed under docs or attached. | met; published | Environment and actual report above; raw host events and extracted PNGs below. [PR1808](https://github.com/tya5/chrona/pull/1808) merged at `f90696d329135a86a49ed2fe4592eea1b2518abb` after applicable docsCI39375967957 passed. |
| Any defect it finds filed separately. | met | Confirmed prose/version mismatch is issue1807; host policy refusal and unconfirmed visual suspicion are explicitly distinguished. |
| Validate a plan, fix a cycle, render, view the image, apply a guided authoring edit, revert it, and render again. | met | Completed host events item2–item21; actual images and observed CAS revisions above. |

Images (directly extracted from completed MCP image blocks, not re-rendered):
[draft](assets-902-agent-host-2026-10-20/draft.png),
[initial](assets-902-agent-host-2026-10-20/guided-initial.png),
[edited](assets-902-agent-host-2026-10-20/guided-edited.png),
[reverted](assets-902-agent-host-2026-10-20/guided-reverted.png).
Input: [cycle](assets-902-agent-host-2026-10-20/input-cycle.yaml);
actual host output: [fixed Project](assets-902-agent-host-2026-10-20/fixed-project.yaml).
Parent902 stays open for separately parked requirements; this records only the
reviewer-assigned consolidated814 slice. All applicable docsCI passed and the
transcript is published. The next updated-review-containing main release is
tracked with the1807 metadata correction; it does not unpark902 item4 or815.
