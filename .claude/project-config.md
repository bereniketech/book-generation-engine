# Project Configuration

## Skill Library
Path: C:/Users/Hp/Desktop/Experiment/claude_kit

## Selected Skills

### Core
- `.kit/skills/core/karpathy-principles/SKILL.md` — Karpathy engineering principles

### Languages
- `.kit/skills/languages/python-patterns/SKILL.md` — Python patterns for FastAPI/worker code

### Backend Frameworks
- `.kit/skills/frameworks-backend/fastapi-pro/SKILL.md` — FastAPI production patterns
- `.kit/skills/frameworks-backend/python-fastapi-development/SKILL.md` — FastAPI API design (legacy)

### Data Science / AI
- `.kit/skills/data-science-ml/ai-engineer/SKILL.md` — LLM integration patterns

### Data & Backend
- `.kit/skills/data-backend/postgres-patterns/SKILL.md` — Supabase/Postgres data layer

### Testing & Quality
- `.kit/skills/testing-quality/tdd-workflow/SKILL.md` — Test-driven development

### DevOps
- `.kit/skills/devops/terminal-cli-devops/SKILL.md` — CLI and worker process management

### Observability
- `.kit/skills/observability/observability-engineer/SKILL.md` — Structured logging, metrics, tracing

### Development
- `.kit/skills/development/systematic-debugging/SKILL.md` — Systematic debugging patterns

### Studio
- `.kit/skills/_studio/batch-tasks/SKILL.md` — Orchestrate sequential tasks with /verify gates

### Research & Content (retained from prior bootstrap)
- `.kit/skills/research-docs/beautiful-prose/SKILL.md`
- `.kit/skills/research-docs/avoid-ai-writing/SKILL.md`
- `.kit/skills/research-docs/document-content-writing-editing/SKILL.md`
- `.kit/skills/research-docs/copy-editing/SKILL.md`
- `.kit/skills/research-docs/professional-proofreader/SKILL.md`
- `.kit/skills/research-docs/research-information-retreival/SKILL.md`
- `.kit/skills/research-docs/copywriting/SKILL.md`

## Selected Agents
- `.kit/agents/board/company-coo.md` — master router across all companies
- `.kit/agents/software-company/software-cto.md` — software-company CEO
- `.kit/agents/software-company/engineering/architect.md`
- `.kit/agents/software-company/engineering/software-developer-expert.md`
- `.kit/agents/software-company/engineering/web-backend-expert.md`
- `.kit/agents/software-company/engineering/web-frontend-expert.md`
- `.kit/agents/software-company/ai/ai-cto.md`
- `.kit/agents/software-company/ai/ai-ml-expert.md`
- `.kit/agents/software-company/qa/test-expert.md`
- `.kit/agents/software-company/devops/devops-infra-expert.md`

## Selected Commands
- `.kit/commands/core/task-handoff.md`
- `.kit/commands/core/wrapup.md`
- `.kit/commands/development/code-review.md`
- `.kit/commands/development/build-fix.md`
- `.kit/commands/testing-quality/tdd.md`
- `.kit/commands/languages/python-review.md`
- `.kit/commands/planning/plan.md`

## Rules Active
- `.kit/rules/common/` (10 files: agents, coding-style, development-workflow, git-workflow, hooks, patterns, performance, security, testing, token-cost)
- `.kit/rules/python/` (5 files: coding-style, hooks, patterns, security, testing)

## Stack
- Language: Python 3.12
- Backend: FastAPI (REST + WebSocket)
- Queue: RabbitMQ (aio-pika)
- Database/Storage: Supabase (Postgres + Storage via supabase-py)
- Validation: Pydantic v2
- LLM: Anthropic SDK (primary), OpenAI, Google Gemini, Ollama (pluggable via LLMClient)
- Image: DALL-E 3, Flux via Replicate (pluggable via ImageClient)
- EPUB: ebooklib
- PDF: ReportLab
- Email: SMTP
- Frontend: React or Next.js
- Research: NotebookLM (non-fiction deep research)
