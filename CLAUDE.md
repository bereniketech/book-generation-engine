# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Status

This project is in the **design/approved** phase. The spec is finalized; implementation has not yet begun. The single source of truth for intended behavior is [2026-04-17-book-generation-engine-design.md](2026-04-17-book-generation-engine-design.md).

---

## What This Is

An end-to-end automated book generation system that produces Amazon KDP-ready bundles (manuscript EPUB/PDF, cover image, cover brief, description, metadata) from a web dashboard. Supports both fiction and non-fiction modes.

---

## Planned Stack

| Layer | Technology |
|---|---|
| API | FastAPI (Python) |
| Job queue | RabbitMQ |
| State + storage | Supabase |
| Notifications | Email |
| LLM | Pluggable via `LLMClient` (Anthropic, OpenAI, Gemini, Ollama, any OpenAI-compatible) |
| Image generation | Pluggable via `ImageClient` (DALL-E 3, Flux/Replicate) |
| Non-fiction research | NotebookLM integration |

---

## Architecture

**Modular monolith.** Each engine is a Python class/module. FastAPI serves the dashboard API. A separate worker process consumes jobs from RabbitMQ and runs the engine pipeline sequentially.

```
User (Dashboard)
    → FastAPI backend
    → RabbitMQ (job queue)
    → Worker process (runs engines in sequence)
    → Supabase (stores state, chapters, files)
    → Email (sends KDP bundle download link on completion)
```

### LLM Abstraction

Every engine uses a single `LLMClient` — no engine is aware of which provider it's talking to. Configured per-book via the job config:

```python
llm = LLMClient(provider="anthropic", model="claude-sonnet-4-6", api_key="...")
response = llm.complete(prompt, system_prompt)
```

Same pattern for `ImageClient`.

---

## Engine Pipeline

### Shared Core (both modes)
1. **Entry Gate** — validates input, sets mode (`fiction` | `non_fiction`), outputs `validated_input.json`
2. **Intent Engine** — reader transformation and book purpose
3. **Audience Engine** — target reader, depth tolerance, expectations
4. **Positioning Engine** — unique angle, market differentiation
5. **Content Blueprint Selector** — branches to fiction or non-fiction path

### Fiction Path (F1–F7)
F1 Concept → F2 Theme → F3 Character → F4 Conflict → F5 Structure (beat-based scene outline) → F6 Ending (scored + selected) → F7 Story Memory (tracks characters, timeline, world rules)

### Non-Fiction Path (N1–N5)
N1 Promise → N2 Framework → N3 Content Map → N4 Evidence → N5 Knowledge Memory (tracks concepts, frameworks, repetition control)

Non-fiction deep research must be done using NotebookLM before content generation.

### Unified Generation Layer (both modes)
6. **Chapter Generator** — one chapter at a time, using blueprint + memory + audience/tone
7. **Continuity Engine** — fiction: character/timeline consistency; non-fiction: no repeated ideas, logical flow
8. **QA Engine** — per chapter: clarity, pacing/density, redundancy, coherence
9. **Style Enforcer** — tone consistency, sentence variation, readability
10. **Final Assembly** — combines all locked chapters into `manuscript_final.txt`
11. **Packaging Engine** — book description, positioning copy, metadata (title, subtitle, 7 keywords, 2 categories)
12. **Cover Engine** — cover brief (text) + cover image (via `ImageClient`)

**Critical rule:** Generate → Validate → Update Memory → Lock. Never advance to the next chapter until the current one is locked.

---

## Dashboard Views

- **Job Creator** — form: title/topic/idea, mode, audience, tone, target length, LLM config (provider + model + API key), image model config, notification email
- **Book Editor** — per-chapter inline editing, regenerate individual chapters (re-runs Chapter Generator + QA), view memory state, approve/lock chapters manually, pipeline progress bar
- **Export View** — download KDP bundle: `manuscript.epub`, `manuscript.pdf`, `cover.jpg`, `cover-brief.txt`, `description.txt`, `metadata.json`
