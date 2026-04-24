---
description: End-of-session wrap-up — summarizes the session, saves memories, and pushes a session log to the project's AI Brain notebook. Run after /task-handoff or manually with /wrapup.
---

# Session Wrap-Up

Run this at the end of every session (automatically after `/task-handoff`, or manually) to capture what happened and commit it to long-term memory.

## Step 1: Ensure NotebookLM CLI Is Available

Before anything else, verify the CLI is installed and runnable:

```bash
export PATH="$HOME/bin:$PATH"
notebooklm --help > /dev/null 2>&1
```

**If the command fails:**
1. Try the venv path: `~/.notebooklm-venv/bin/notebooklm --help`
2. If that also fails, tell the user:
   > NotebookLM CLI is not installed. Install it with:
   > ```
   > pip install "notebooklm-py[browser]" && playwright install chromium
   > ```
   > Then run `notebooklm login` to authenticate.
3. Skip all NotebookLM steps — continue with memory saves only.

**If the command succeeds**, also verify auth:
```bash
notebooklm auth check
```
If auth fails, warn the user and continue without notebook push.

## Step 2: Ensure AI Brain Notebook Exists

Detect the current repo name:
```bash
basename "$(git rev-parse --show-toplevel 2>/dev/null || basename "$PWD")"
```

The brain notebook must be named `<repo-name> AI Brain` (e.g. `my-project AI Brain`).

**Check for saved notebook ID:**
Look in the memory index for a reference like `brain_notebook_id`.

**If no notebook ID is saved:**
1. List existing notebooks: `notebooklm list --json`
2. Look for one matching `<repo-name> AI Brain`
3. **If found:** Use that notebook's ID
4. **If NOT found:** Create it automatically:
   ```bash
   notebooklm create "<repo-name> AI Brain" --json
   ```
5. Save the notebook ID to a memory file:
   ```
   Memory file: reference_brain_notebook.md
   Content: Brain notebook ID, title, repo name, and when it was created
   ```
   Update the MEMORY.md index.

**If notebook ID IS saved:** Verify it still exists with `notebooklm list --json`. If deleted, recreate.

## Step 3: Check AI Brain First

Before reviewing the conversation, query the AI Brain for context on what was worked on previously:

```bash
notebooklm use <BRAIN_NOTEBOOK_ID>
notebooklm ask "What were the most recent sessions about? Any open threads?" --json
```

Use this context to identify whether any open threads from prior sessions were addressed in this session.

## Step 4: Review the Session

Look back through the entire conversation and identify:

- **Decisions made** — what was decided and why
- **Work completed** — what was built, fixed, configured, or shipped
- **Key learnings** — anything surprising or non-obvious
- **Open threads** — anything left unfinished or to revisit next time
- **User preferences revealed** — any new feedback about how the user likes to work
- **Prior open threads resolved** — any threads from the AI Brain that were addressed

## Step 5: Save Memories

Check the existing memory index and save or update memories as needed:

- **feedback** — corrections or confirmed approaches
- **project** — ongoing work, goals, deadlines, context for future sessions
- **user** — anything new about the user's role, preferences, or knowledge
- **reference** — external resources, tools, or systems referenced

Rules:
- Don't duplicate existing memories — update them instead
- Don't save things derivable from code or git history
- Convert relative dates to absolute dates
- Include **Why:** and **How to apply:** for feedback and project memories

## Step 6: Write Session Summary

Create a concise markdown session summary:

```markdown
# Session Summary — YYYY-MM-DD

## What We Did
- Bullet points of key work completed

## Decisions Made
- Key decisions and their reasoning

## Key Learnings
- Non-obvious insights or discoveries

## Open Threads
- Anything to pick up next time

## Tools & Systems Touched
- List of tools, repos, services involved
```

Save to a temp file at `/tmp/session-summary-YYYY-MM-DD.md` (append counter if multiple same-day sessions).

## Step 7: Push to AI Brain

Add the session summary as a source to the Brain notebook:

```bash
notebooklm source add /tmp/session-summary-YYYY-MM-DD.md --notebook <BRAIN_NOTEBOOK_ID>
```

If auth fails or CLI is unavailable, skip — memories are still saved locally.

## Step 8: Confirm

Tell the user:
- How many memories were saved/updated
- Whether the session summary was added to the AI Brain (or skipped)
- Any open threads to pick up next time

Keep it brief.
