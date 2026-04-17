# Requirements: Book Generation Engine

## Introduction

The Book Generation Engine automates end-to-end book production (fiction and non-fiction) and delivers a complete Amazon KDP-ready bundle. A FastAPI backend accepts book generation jobs, a RabbitMQ worker executes the engine pipeline, and a React/Next.js dashboard allows authors to monitor progress, edit chapters, and download the final bundle (EPUB, PDF, cover, metadata). All LLM and image providers are pluggable via a single abstraction layer.

---

## Requirements

### Requirement 1: Job Submission

**User Story:** As an author, I want to submit a book generation job via a web form so that I can start the automated pipeline without any technical setup.

#### Acceptance Criteria

1. WHEN the author fills in title, mode (fiction|non_fiction), audience, tone, target length, LLM provider config, image provider config, and notification email and submits the form THEN the system SHALL create a job record in Supabase and publish a message to RabbitMQ.
2. WHEN the job is published THEN the system SHALL return a job ID and a WebSocket URL for progress streaming.
3. IF any required field is missing THEN the system SHALL return HTTP 422 with a field-level validation error message.
4. IF the RabbitMQ broker is unreachable THEN the system SHALL return HTTP 503 and log the error without creating a partial job record.

---

### Requirement 2: LLM & Image Client Abstraction

**User Story:** As an engineer, I want all engines to call a single `LLMClient` and `ImageClient` interface so that no engine is coupled to a specific provider.

#### Acceptance Criteria

1. WHEN an engine calls `llm.complete(prompt, system_prompt)` THEN the system SHALL route the call to the configured provider (anthropic | openai | google | ollama | openai-compatible) and return a normalised string response.
2. WHEN an engine calls `image.generate(prompt, width, height)` THEN the system SHALL route the call to the configured image provider (dall-e-3 | replicate-flux) and return a URL or byte stream.
3. IF the provider raises a rate-limit error THEN the system SHALL apply exponential backoff with a maximum of 3 retries before raising `ProviderRateLimitError`.
4. IF an unsupported provider name is given THEN the system SHALL raise `UnsupportedProviderError` at LLMClient construction time, not at call time.
5. The system SHALL expose provider selection purely via the job config — no engine shall import a provider SDK directly.

---

### Requirement 3: Entry Gate & Shared Core Engines

**User Story:** As the system, I want the pipeline to validate input and produce structured planning artifacts before any generation so that all downstream engines work from consistent, validated data.

#### Acceptance Criteria

1. WHEN the worker receives a job THEN the system SHALL run Entry Gate → Intent Engine → Audience Engine → Positioning Engine → Content Blueprint Selector in sequence.
2. WHEN Entry Gate runs THEN the system SHALL produce `validated_input.json` stored in Supabase and update job status to `planning`.
3. WHEN Content Blueprint Selector runs THEN the system SHALL branch: if mode is `fiction` execute F1–F7 engines; if mode is `non_fiction` run NotebookLM deep research then execute N1–N5 engines.
4. IF any core engine fails THEN the system SHALL update job status to `failed`, store the error, and stop processing without advancing to the generation layer.

---

### Requirement 4: Fiction Path Engines (F1–F7)

**User Story:** As an author creating a fiction book, I want the pipeline to generate a complete story scaffold — concept, themes, characters, conflict, structure, ending, and memory — before writing any chapter so that the resulting manuscript is coherent.

#### Acceptance Criteria

1. WHEN mode is `fiction` THEN the system SHALL execute F1 Concept Engine → F2 Theme Engine → F3 Character Engine → F4 Conflict Engine → F5 Structure Engine → F6 Ending Engine → F7 Story Memory in sequence.
2. WHEN F7 Story Memory is initialised THEN the system SHALL persist the memory object to Supabase keyed by job ID.
3. IF any fiction engine returns an empty or invalid response from the LLM THEN the system SHALL retry once, then fail the job with status `fiction_planning_failed`.

---

### Requirement 5: Non-Fiction Path Engines (N1–N5) with NotebookLM Research

**User Story:** As an author creating a non-fiction book, I want the pipeline to conduct deep research via NotebookLM before outlining so that the book is evidence-based and authoritative.

#### Acceptance Criteria

1. WHEN mode is `non_fiction` THEN the system SHALL create a NotebookLM notebook, upload the book topic as a source, trigger audio/summary generation, and store the research summary in Supabase.
2. WHEN NotebookLM research is complete THEN the system SHALL execute N1 Promise Engine → N2 Framework Engine → N3 Content Map → N4 Evidence Engine → N5 Knowledge Memory in sequence.
3. IF NotebookLM API is unavailable THEN the system SHALL fall back to LLM-based research synthesis and log a warning; the job SHALL NOT fail.
4. WHEN N5 Knowledge Memory is initialised THEN the system SHALL persist it to Supabase keyed by job ID.

---

### Requirement 6: Chapter Generation with Memory & QA Loop

**User Story:** As an author, I want each chapter generated, validated, and locked before the next one starts so that the manuscript is consistent and high-quality.

#### Acceptance Criteria

1. WHEN the planning phase is complete THEN the system SHALL iterate over each chapter in the content blueprint, running: Chapter Generator → Continuity Engine → QA Engine → Style Enforcer for each chapter.
2. WHEN all four engines pass for a chapter THEN the system SHALL mark the chapter as `locked` in Supabase and update the memory state.
3. WHEN a chapter is locked THEN the system SHALL NOT regenerate it unless the author explicitly requests a regenerate action.
4. IF the QA Engine or Style Enforcer returns a failure score THEN the system SHALL regenerate the chapter up to 2 additional times before marking the chapter as `qa_failed` and pausing the job.
5. WHEN chapter generation progresses THEN the system SHALL emit a WebSocket progress event: `{ job_id, chapter_index, total_chapters, step, status }`.

---

### Requirement 7: Final Assembly & Packaging

**User Story:** As an author, I want the pipeline to assemble all locked chapters and produce a complete KDP bundle automatically so that I can download it without manual work.

#### Acceptance Criteria

1. WHEN all chapters are locked THEN the system SHALL run Final Assembly Engine, concatenating chapters into `manuscript_final.txt` stored in Supabase Storage.
2. WHEN Final Assembly completes THEN the system SHALL run Packaging Engine producing: `description.txt`, `metadata.json` (title, subtitle, 7 keywords, 2 categories).
3. WHEN Packaging Engine completes THEN the system SHALL run Cover Engine producing: `cover-brief.txt` and `cover.jpg` (via ImageClient).
4. WHEN all packaging is done THEN the system SHALL run Formatting Engine producing `manuscript.epub` (via ebooklib) and `manuscript.pdf` (via ReportLab).
5. WHEN formatting is complete THEN the system SHALL bundle all artifacts into a downloadable zip in Supabase Storage and update job status to `complete`.

---

### Requirement 8: Email Delivery

**User Story:** As an author, I want to receive an email with the download link when my book is ready so that I don't have to monitor the dashboard continuously.

#### Acceptance Criteria

1. WHEN job status becomes `complete` THEN the system SHALL send an email to the notification address containing a signed Supabase Storage URL valid for 7 days.
2. IF email delivery fails THEN the system SHALL log the error and retry once after 60 seconds; the job status SHALL remain `complete` regardless of email outcome.

---

### Requirement 9: Dashboard — Job Creator

**User Story:** As an author, I want a web form to configure and submit a book generation job so that I can control all generation parameters from a UI.

#### Acceptance Criteria

1. WHEN the author visits the dashboard THEN the system SHALL display a Job Creator form with fields: title, mode, audience, tone, target length, LLM provider (dropdown + model + API key), image provider (dropdown + API key), notification email.
2. WHEN the form is submitted successfully THEN the system SHALL navigate to the Book Editor view for the new job and begin showing real-time progress.
3. IF validation errors are returned THEN the system SHALL display them inline next to the relevant fields.

---

### Requirement 10: Dashboard — Book Editor

**User Story:** As an author, I want to read, edit, regenerate, and lock each chapter from a web UI so that I have full control over the manuscript before export.

#### Acceptance Criteria

1. WHEN the author opens the Book Editor for a job THEN the system SHALL display each chapter with its content, lock status, and current memory state.
2. WHEN the author edits a chapter inline THEN the system SHALL save the edit to Supabase on blur.
3. WHEN the author clicks "Regenerate" on a chapter THEN the system SHALL re-run Chapter Generator + QA for that chapter only and update the UI.
4. WHEN the author clicks "Lock" THEN the system SHALL mark the chapter as locked and disable further editing unless manually unlocked.
5. WHEN pipeline progress events arrive via WebSocket THEN the system SHALL update the progress bar and current step label without a page reload.

---

### Requirement 11: Dashboard — Export View

**User Story:** As an author, I want to download the complete KDP bundle from the dashboard when the book is ready so that I can upload it directly to Amazon KDP.

#### Acceptance Criteria

1. WHEN job status is `complete` THEN the system SHALL display the Export View with a download button for the zip bundle.
2. WHEN the author clicks download THEN the system SHALL redirect to the signed Supabase Storage URL.
3. WHEN the author expands the bundle preview THEN the system SHALL show a list of included files: manuscript.epub, manuscript.pdf, cover.jpg, cover-brief.txt, description.txt, metadata.json.
