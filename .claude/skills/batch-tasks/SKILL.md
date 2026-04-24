---
name: batch-tasks
description: Run all tasks in a folder sequentially — for each task, load the ## Skills, ## Agents, and ## Commands declared in the task file, invoke the named agent with that context, run /verify, run /wrapup, then /clear before starting the next task.
---

# Batch Tasks

Execute every task in a tasks folder in sequence, with full quality gates and context reset between each task. Each task's declared skills, agents, and commands are loaded and passed into the agent invocation — the agent executes using exactly the tools the task specifies.

---

## 1. Locate the Tasks

Accept a folder path or file path as the argument. Default: `.spec/tasks/`.

| Input | How to read tasks |
|---|---|
| Folder of `.md` files | Sort files by name (`task-001.md`, `task-002.md`, ...) — each file is one task |
| Single `tasks.md` file | Each `- [ ] N.` checkbox block is one task |
| No argument | Use `.spec/tasks/` if it exists, else look for `.spec/tasks.md` |

**Rule:** If neither location exists, stop and tell the user — do not silently proceed.

---

## 2. Parse Each Task

For each task file, extract all of the following:

| Field | Where to find it | Default |
|---|---|---|
| Title | `# Task NNN: <title>` heading | `Task N` |
| Agent | `## Agents` section — first `@<agent-slug>` entry | `software-developer-expert` |
| Skills | `## Skills` section — all `- .kit/skills/...` lines | none |
| Commands | `## Commands` section — all `- /<command>` lines | none |
| Acceptance Criteria | `## Acceptance Criteria` section | — |
| Steps | `## Steps` section | — |
| Status | `Status: COMPLETE` in frontmatter or appended at end | incomplete |

**Rule:** Always read `## Skills`, `## Agents`, and `## Commands` from the task file itself. Never assume skills or agents from the previous task carry over — each task is self-contained.

---

## 3. Execution Loop

Process tasks in sorted order. For each task:

### 3a. Skip if complete

If the task has `Status: COMPLETE` in its frontmatter or appended at end, print:
```
[SKIP] Task N — Title (already complete)
```
Advance to the next task.

### 3b. Print task header

```
════════════════════════════════════════
TASK N / TOTAL: Title
Agent : <agent-slug>
Skills: <count> loaded
Commands: <list>
════════════════════════════════════════
```

### 3c. Load skills into context

Before invoking the agent, read every skill file listed in `## Skills`:

```
For each path in task's ## Skills:
  Read the SKILL.md file at that path
  Hold its content in context — the agent will use it
```

This is the same as loading skills via `@import` — the agent operates under the constraints and patterns defined in those skill files.

### 3d. Invoke the agent

Dispatch the primary agent from `## Agents` as a subagent. Pass the full task content, all loaded skill content, AND the mandatory post-task sequence inline so the agent executes it without relying on slash commands:

```markdown
## Loaded Skills
<concatenated content of all skill files from ## Skills>

## Task
<full task file content>

## Instructions
You are executing this task as @<agent-slug>.

Load and follow ALL skills listed above — they govern how you write code,
structure output, and enforce quality standards for this task.

Complete every step. Meet every acceptance criterion.
Do not ask questions — make decisions and document them.

## Mandatory Post-Task Sequence (execute in order — do not skip any step)

### Step A — Verify NotebookLM CLI
```bash
export PATH="$HOME/bin:$PATH"
notebooklm --help > /dev/null 2>&1 && echo "CLI OK" || echo "CLI MISSING"
notebooklm auth check
```
If CLI missing or auth fails: skip Steps B–E, continue from Step F.

### Step B — Find or create AI Brain notebook
```bash
REPO=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")")
notebooklm list --json
```
Find notebook named `${REPO} AI Brain`. If not found:
```bash
notebooklm create "${REPO} AI Brain" --json
```
Save the notebook ID to `memory/reference_brain_notebook.md` and update `MEMORY.md`.

### Step C — Write task summary file
Write `/tmp/task-summary-<NNN>.md` with this content:
```
# Task <NNN> Summary — <YYYY-MM-DD>

## Task
<title of this task>

## What Was Built
<bullet list of every file created or modified>

## Decisions Made
<key decisions and reasoning from this task>

## Open Threads
<anything unresolved or deferred>
```

### Step D — Push summary to AI Brain
```bash
notebooklm use <BRAIN_NOTEBOOK_ID>
notebooklm source add /tmp/task-summary-<NNN>.md --notebook <BRAIN_NOTEBOOK_ID>
```
Wait for confirmation before continuing.

### Step E — Save memories
Check `memory/MEMORY.md`. For each item below, update the existing memory file if it exists, or create a new one:
- Any project decisions made in this task → `memory/project_<slug>.md` (type: project)
- Any non-obvious implementation choices → `memory/feedback_<slug>.md` (type: feedback)
Do not create duplicate entries.

### Step F — Mark task complete
Append to the task file:
```
Status: COMPLETE
Completed: <ISO timestamp>
```

### Step G — Output completion signal
Output exactly: `TASK COMPLETE — <one-line summary of what was built>`
```

Wait for the agent to finish and confirm "TASK COMPLETE" before continuing.

### 3e. Verify output

Run the test suite or lint checks appropriate to the task (e.g. `pytest`, `ruff check`).

- **PASS** → continue to 3f
- **FAIL** → re-invoke the same agent with the errors appended (one retry)
  - **Still failing** → mark task BLOCKED at the bottom of the task file and continue:
    ```
    Status: BLOCKED — verify failed after retry
    Errors: <paste output>
    ```

### 3f. Confirm NotebookLM push

After the agent outputs "TASK COMPLETE", confirm the NotebookLM push happened:
```bash
notebooklm source list --json | grep "task-summary"
```
If the summary source is missing, run Steps A–D from the agent's post-task sequence above directly now before advancing.

### 3g. Clear context (mandatory before next task)

Add this as the final step inside the agent dispatch prompt in 3d, after Step G:

```
### Step H — Clear context
You have completed this task. Before this agent session ends, output the following
exactly so the batch runner knows to clear context:

CONTEXT CLEAR — next task: <NNN>

Then stop. Do not read any more files. Do not continue to the next task.
The batch runner will start a fresh agent for the next task.
```

When the batch runner receives "CONTEXT CLEAR — next task: NNN":
1. Terminate the current agent session entirely.
2. Start a new agent session (new context window — no carry-over from previous task).
3. In the new session, re-read this batch-tasks SKILL.md from disk.
4. Re-read task-NNN.md from disk.
5. Resume the execution loop from step 3a for task NNN.

---

## 4. Final Summary

After all tasks are processed:

```
════════════════════════════════════════
BATCH COMPLETE
════════════════════════════════════════
Total   : N
Done    : X
Skipped : Y  (already complete)
Blocked : Z  (verify failed after retry)

Blocked tasks:
- Task 3 — Title (see task file for errors)

Next: open the first blocked task file to diagnose.
```

---

## 5. Rules

**Rule:** Tasks always run sequentially — never in parallel. Each task's output is the codebase the next task builds on.

**Rule:** Never skip /verify. A task is not complete until verification passes (or is explicitly marked BLOCKED after retry).

**Rule:** Never skip wrapup (Steps A–G in the agent prompt). All steps must complete — CLI check, brain notebook, summary file, NotebookLM push, memory saves, task marked complete. These are inlined in the agent dispatch so the agent cannot return without executing them.

**Rule:** Never skip clear (Step H in the agent prompt). The agent must output "CONTEXT CLEAR — next task: NNN" as its final line. The batch runner terminates the agent on this signal and starts a fresh agent for the next task. Context from a previous task must never bleed into the next.

**Rule:** Load `## Skills` from the task file before invoking the agent — the agent must operate under those skill constraints, not generic defaults.

**Rule:** The primary agent to invoke is the first entry in the task's `## Agents` section. If the task lists multiple agents (e.g., `@ai-ml-expert` + `@technical-writer-expert`), the first is the executor; the rest are reviewers — invoke them after the primary agent completes, before /verify.

**Rule:** `--from N` starts the loop at task N, skipping earlier tasks regardless of status. `--only N` runs exactly one task.

**Rule:** If `## Skills`, `## Agents`, or `## Commands` sections are missing from a task file, stop and warn — do not proceed with that task until the sections are present.
