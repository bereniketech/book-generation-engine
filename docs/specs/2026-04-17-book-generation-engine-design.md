# Book Generation Engine — Design Spec
**Date:** 2026-04-17  
**Status:** Approved

---

## 1. Goal

Automate the end-to-end process of generating a book (fiction or non-fiction) and producing a complete Amazon KDP-ready bundle: manuscript (EPUB/PDF), cover image, cover brief, book description, and metadata — all downloadable from a web dashboard.

---

## 2. Architecture Overview

Modular monolith with clear engine boundaries. Each engine is a Python class/module. FastAPI serves the dashboard API. A separate worker process consumes jobs from RabbitMQ and runs the engine pipeline. Supabase stores all state and files. Email delivers the final KDP bundle link on completion.

```
User (Dashboard)
    → FastAPI backend
    → RabbitMQ (job queue)
    → Worker process (runs engines in sequence)
    → Supabase (stores state, chapters, files)
    → Email (sends KDP bundle download link on completion)
```

---

## 3. LLM Interface Layer

A single `LLMClient` abstraction used by every engine. Model-agnostic — no engine knows which provider it is talking to. Configured per book via the job config.

**Supported providers (pluggable):**
- Anthropic (Claude)
- OpenAI (GPT-4o, etc.)
- Google (Gemini)
- Ollama (local models)
- Any OpenAI-compatible API

```python
llm = LLMClient(provider="anthropic", model="claude-sonnet-4-6", api_key="...")
response = llm.complete(prompt, system_prompt)
```

Image generation uses the same pluggable pattern via an `ImageClient` abstraction (DALL-E 3, Flux via Replicate, etc.).

---

## 4. Engine Pipeline

### Shared Core (both modes)
1. **Entry Gate** — validates input, sets mode (`fiction` | `non_fiction`), outputs `validated_input.json`
2. **Intent Engine** — defines what the book is trying to do, reader transformation, outcome
3. **Audience Engine** — defines who it's for, expectations, depth tolerance
4. **Positioning Engine** — unique angle, market differentiation, what the book avoids
5. **Content Blueprint Selector** — branches to Fiction or Non-Fiction path

### Fiction Path
- F1 Concept Engine — hook + unique premise
- F2 Theme Engine — meaning + moral tension
- F3 Character Engine — protagonist, antagonist, dynamics
- F4 Conflict Engine — internal + external conflict map
- F5 Structure Engine — beat-based outline (scene-level)
- F6 Ending Engine — multiple endings scored and selected
- F7 Story Memory — tracks characters, timeline, world rules

### Non-Fiction Path
- N1 Promise Engine — clear reader transformation
- N2 Framework Engine — step-by-step system
- N3 Content Map — chapter breakdown
- N4 Evidence Engine — examples, case studies
- N5 Knowledge Memory — tracks concepts introduced, frameworks used, repetition control

### Unified Generation Layer (both modes)
6. **Chapter Generator** — generates one chapter at a time using blueprint + memory + audience/tone
7. **Continuity Engine** — fiction: character/timeline consistency; non-fiction: no repeated ideas, logical progression
8. **QA Engine** — runs per chapter: clarity, pacing/density, redundancy, coherence
9. **Style Enforcer** — tone consistency, sentence variation, readability level
10. **Final Assembly** — combines all locked chapters into `manuscript_final.txt`
11. **Packaging Engine** — generates book description, positioning copy, metadata (title, subtitle, 7 keywords, 2 categories)
12. **Cover Engine** — generates cover brief (text) + cover image (via image model)

**Generation rule:** Generate → Validate → Update Memory → Lock. Never move to the next chapter until the current one is locked.

---

## 5. Dashboard (Full Editor)

**Three main views:**

### Job Creator
Form inputs:
- Title / topic / idea
- Mode: Fiction or Non-Fiction
- Target audience
- Tone
- Target length (word count or chapter count)
- LLM provider + model + API key
- Image model provider + API key
- Notification email

### Book Editor
Per-chapter view with:
- Read chapter content
- Edit chapter inline
- Regenerate individual chapter (re-runs Chapter Generator + QA for that chapter)
- View current memory state (story or knowledge)
- Approve / lock chapter manually

Progress bar showing current pipeline step (e.g., "Generating Chapter 3 of 12...")

### Export View
Download KDP bundle containing:
- `manuscript.epub` (ebook)
- `manuscript.pdf` (print interior)
- `cover.jpg` (generated cover image)
- `cover-brief.txt` (text brief for human designer)
- `description.txt` (book description / blurb)
- `metadata.json` (title, subtitle, keywords, categories)

For non-fiction deep research should be done for the given topic using notebook lm

