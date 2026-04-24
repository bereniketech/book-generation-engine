---
name: karpathy-principles
description: Four coding discipline principles (Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution) that reduce unnecessary rewrites, over-engineering, and scope creep.
---

# Karpathy Principles

Four behavioral rules that reduce the most common LLM coding mistakes.

---

## 1. Think Before Coding

Before implementing anything:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

**Rule:** Never begin implementation while confused. Surface the confusion first.

---

## 2. Simplicity First

Write the minimum code that solves the problem. Nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.

**Rule:** If you write 200 lines and it could be 50, rewrite it before submitting.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

---

## 3. Surgical Changes

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless explicitly asked.

**Rule:** Every changed line must trace directly to the user's request.

---

## 4. Goal-Driven Execution

Transform tasks into verifiable goals before starting:

| Vague | Verifiable |
|-------|-----------|
| "Fix the bug" | "Write a test that reproduces it, then make it pass" |
| "Add validation" | "Write tests for invalid inputs, then make them pass" |
| "Refactor X" | "Ensure tests pass before and after" |

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

**Rule:** Weak criteria ("make it work") require clarification before proceeding — strong success criteria let you loop independently.
