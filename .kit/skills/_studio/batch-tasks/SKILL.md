---
name: batch-tasks
description: Run all tasks in a folder sequentially — for each task, invoke the agent named in the task file, run /verify, run /wrapup, then /clear before starting the next task.
---

# Batch Tasks

Execute every task in a tasks folder (or tasks.md file) in sequence, with full quality gates and context reset between each task.

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

For each task block or file, extract:

| Field | Where to find it | Default |
|---|---|---|
| Title | Heading or checkbox text | `Task N` |
| Description | Body text | — |
| Agent | `_Agent: <slug>` line | `software-developer-expert` |
| Skills | `_Skills: /skill-name` line | none |
| AC | `**AC:**` line | — |
| Status | `- [x]` checkbox or `Status: COMPLETE` line | incomplete |

---

## 3. Execution Loop

Process tasks in sorted order. For each task:

### 3a. Skip if complete

If the task has `- [x]` or `Status: COMPLETE`, print:
```
[SKIP] Task N — Title (already complete)
```
Advance to the next task.

### 3b. Print task header

```
════════════════════════════════════════
TASK N / TOTAL: Title
Agent: <agent-slug>
════════════════════════════════════════
```

### 3c. Invoke the agent

Dispatch the named agent as a subagent with:

```markdown
## TASK
<full task content including AC>

## INSTRUCTIONS
Complete this task fully. Follow all acceptance criteria.
Do not ask questions — make decisions and document them.
When done, output: TASK COMPLETE — <one-line summary>
```

Wait for the agent to finish before continuing.

### 3d. Run /verify

- **PASS** → continue
- **FAIL** → re-invoke the same agent with the verification errors as context (one retry)
  - **Still failing** → mark task BLOCKED, record errors, continue to next task:
    ```
    Status: BLOCKED — verify failed after retry
    ```

### 3e. Mark task complete

- Checkbox list: change `- [ ]` → `- [x]`
- Individual file: append `Status: COMPLETE`

### 3f. Run /wrapup

Save session memories and push session log.

### 3g. Run /clear

Reset context window before the next task.

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
Blocked : Z  (verify failed)

Blocked tasks:
- Task 3 — Title (see task file for errors)
```

---

## 5. Rules

**Rule:** Tasks always run sequentially — never in parallel. Each task's output affects the codebase the next task builds on.

**Rule:** Never skip /verify. A task is not complete until verification passes (or is explicitly marked BLOCKED after retry).

**Rule:** If no `_Agent:` line is present in a task, default to `software-developer-expert`.

**Rule:** `--from N` starts the loop at task N, skipping earlier tasks regardless of status. `--only N` runs exactly one task.
