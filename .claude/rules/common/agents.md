# Agent Orchestration

## Universal Planning Gate (CRITICAL — Applies to ALL Specialists)

**Every specialist agent MUST invoke the correct company planning skill before any execution:**
- software-company specialists → `planning-specification-architecture-software`
- marketing-company specialists → `planning-specification-architecture-marketing`
- media-company specialists → `planning-specification-architecture-media`

This is non-negotiable, regardless of how simple or obvious the task appears.

```
[Specialist receives task]
  → Invoke: skills/planning/planning-specification-architecture-software/SKILL.md
      → Phase 1: requirements.md — STOP, wait for user approval
      → Phase 2: design.md      — STOP, wait for user approval
      → Phase 3: tasks/*.md     — STOP, wait for user approval
  → Only then: execute
```

**What counts as "explicit approval":** "yes", "approved", "looks good", "go ahead", or equivalent.

**Rule:** A task brief, CEO delegation, or feature spec is NOT permission to execute. It is permission to PLAN. The spec received is input to the appropriate planning skill — not an approved plan itself.

**Rule:** CEOs (software-cto, chief-marketing-officer, etc.) enforce this gate when delegating. Specialists enforce it when they receive work. Both layers check — neither skips.

## Available Agents

The kit ships 82 agents organized as a holding company OS, located in `~/.claude/agents/`:

- **board/** (4) — `company-coo`, `chief-of-staff`, `chief-design-officer`, `people-operations-expert`
- **software-company/** (60) — CEO `software-cto` over engineering, ai (sub-lead `ai-cto`), devops, data, qa, languages, product (sub-lead `chief-product-officer`), design, security (sub-lead `chief-security-officer`), specialists
- **marketing-company/** (7) — CEO `chief-marketing-officer` over strategy, campaigns, brand
- **media-company/** (11) — CEO `chief-content-officer` over video, audio, editorial, visual, distribution

For multi-step work in a domain, call the operating company CEO and let them route internally. For single-task work where the specialist is obvious, call the specialist directly.

| Specialist | Purpose | When to Use |
|---|---|---|
| `planner` | Implementation planning | Complex features, refactoring |
| `architect` | System design | Architectural decisions |
| `tdd-guide` | Test-driven development | New features, bug fixes |
| `code-reviewer` | Code review | After writing code |
| `security-reviewer` | Security analysis | Before commits |
| `build-error-resolver` | Fix build errors | When build fails |
| `e2e-runner` | E2E testing | Critical user flows |
| `refactor-cleaner` | Dead code cleanup | Code maintenance |
| `doc-updater` | Documentation | Updating docs |

## Immediate Agent Usage

No user prompt needed:
1. Multi-company initiatives → **company-coo**
2. Anything inside software-company (multi-step) → **software-cto**
3. Complex feature requests → **planner**
4. Code just written/modified → **code-reviewer**
5. Bug fix or new feature → **tdd-guide**
6. Architectural decision → **architect**

## Parallel Task Execution

ALWAYS use parallel Task execution for independent operations:

```markdown
# GOOD: Parallel execution
Launch 3 agents in parallel:
1. Agent 1: Security analysis of auth module
2. Agent 2: Performance review of cache system
3. Agent 3: Type checking of utilities

# BAD: Sequential when unnecessary
First agent 1, then agent 2, then agent 3
```

## Multi-Perspective Analysis

For complex problems, use split role sub-agents:
- Factual reviewer
- Senior engineer
- Security expert
- Consistency reviewer
- Redundancy checker
