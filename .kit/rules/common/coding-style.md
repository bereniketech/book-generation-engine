# Coding Style

## Immutability (CRITICAL)

ALWAYS create new objects, NEVER mutate existing ones:

```
// Pseudocode
WRONG:  modify(original, field, value) → changes original in-place
CORRECT: update(original, field, value) → returns new copy with change
```

Rationale: Immutable data prevents hidden side effects, makes debugging easier, and enables safe concurrency.

## File Organization

MANY SMALL FILES > FEW LARGE FILES:
- High cohesion, low coupling
- 200-400 lines typical, 800 max
- Extract utilities from large modules
- Organize by feature/domain, not by type

## Error Handling

ALWAYS handle errors comprehensively:
- Handle errors explicitly at every level
- Provide user-friendly error messages in UI-facing code
- Log detailed error context on the server side
- Never silently swallow errors

## Input Validation

ALWAYS validate at system boundaries:
- Validate all user input before processing
- Use schema-based validation where available
- Fail fast with clear error messages
- Never trust external data (API responses, user input, file content)

## Code Quality Checklist

Before marking work complete:
- [ ] Code is readable and well-named
- [ ] Functions are small (<50 lines)
- [ ] Files are focused (<800 lines)
- [ ] No deep nesting (>4 levels)
- [ ] Proper error handling
- [ ] No hardcoded values (use constants or config)
- [ ] No mutation (immutable patterns used)

---

## Karpathy Principles

### Think Before Coding

State assumptions explicitly before implementing. If uncertain, ask — don't guess silently.
If multiple interpretations exist, present them — don't pick one without saying so.
If a simpler approach exists, say so and push back when warranted.

**Rule:** Stop and name what's confusing before writing any code.

### Simplicity First

Minimum code that solves the problem. Nothing speculative.
No features beyond what was asked. No abstractions for single-use code.
No "flexibility" or "configurability" that wasn't requested.

**Rule:** If you write 200 lines and it could be 50, rewrite it.

### Surgical Changes

Touch only what the request requires. Don't "improve" adjacent code, comments, or formatting.
Match existing style, even if you'd do it differently.
If you notice unrelated dead code, mention it — don't delete it.

**Rule:** Every changed line must trace directly to the user's request.

Remove only imports/variables/functions that YOUR changes made unused — not pre-existing dead code.

### Goal-Driven Execution

Transform tasks into verifiable goals before starting:
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Add validation" → "Write tests for invalid inputs, then make them pass"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
```

**Rule:** Weak criteria ("make it work") require clarification before proceeding.
