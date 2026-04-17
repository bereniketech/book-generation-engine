# Project Configuration

## Skill Library
Path: C:/Users/Hp/Desktop/Experiment/claude_kit

## Selected Skills
- `.kit/skills/languages/python-patterns/SKILL.md` — Python patterns for FastAPI/worker code
- `.kit/skills/frameworks-backend/python-fastapi-development/SKILL.md` — FastAPI API design
- `.kit/skills/data-science-ml/ai-engineer/SKILL.md` — LLM integration patterns
- `.kit/skills/data-backend/postgres-patterns/SKILL.md` — Supabase/Postgres data layer
- `.kit/skills/testing-quality/tdd-workflow/SKILL.md` — Test-driven development
- `.kit/skills/devops/terminal-cli-devops/SKILL.md` — CLI and worker process management
- `.kit/skills/agents-orchestration/agent-orchestrator/SKILL.md` — Pipeline orchestration patterns
- `.kit/skills/ai-platform/notebooklm/SKILL.md` — NotebookLM integration for non-fiction research
- `.kit/skills/research-docs/beautiful-prose/SKILL.md` — prose quality contract for ChapterGeneratorEngine
- `.kit/skills/research-docs/avoid-ai-writing/SKILL.md` — AI-ism audit for QA + Style Enforcer engines
- `.kit/skills/research-docs/document-content-writing-editing/SKILL.md` — long-form writing structure for chapter generation
- `.kit/skills/research-docs/copy-editing/SKILL.md` — 7-sweep editing framework for PackagingEngine (book description)
- `.kit/skills/research-docs/professional-proofreader/SKILL.md` — proofreading pass on final manuscript
- `.kit/skills/research-docs/research-information-retreival/SKILL.md` — research quality protocol for non-fiction LLM fallback (task-008)
- `.kit/skills/research-docs/copywriting/SKILL.md` — conversion-copy rules for Intent/Positioning/Promise engines (tasks 006, 007)
- `.kit/skills/_studio/batch-tasks/SKILL.md` — orchestrates all 18 tasks sequentially with /verify gates

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
- `.kit/agents/media-company/visual/image-creation-expert.md` — reviews + approves cover brief before image generation
- `.kit/agents/media-company/editorial/technical-writer-expert.md` — gates chapters flagged by QA (score < 8) before locking

## Selected Commands
- `.kit/commands/core/task-handoff.md`
- `.kit/commands/core/wrapup.md`
- `.kit/commands/development/code-review.md`
- `.kit/commands/development/build-fix.md`
- `.kit/commands/testing-quality/tdd.md`
- `.kit/commands/languages/python-review.md`

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
