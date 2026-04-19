-- Migration 002: Production Automation schema additions
-- Safe to run multiple times (IF NOT EXISTS / IF NOT EXISTS guards)

-- LLM token usage tracking
CREATE TABLE IF NOT EXISTS llm_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    stage TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INT NOT NULL DEFAULT 0,
    output_tokens INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_usage_job ON llm_usage(job_id);
CREATE INDEX IF NOT EXISTS idx_llm_usage_provider_date ON llm_usage(provider, (created_at::date));

-- Job config templates
CREATE TABLE IF NOT EXISTS job_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL,
    config JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Jobs table additions
ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS cover_status TEXT DEFAULT NULL
        CHECK (cover_status IN ('awaiting_approval', 'approved', 'revising')),
    ADD COLUMN IF NOT EXISTS cover_url TEXT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS chapter_cursor INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS batch_id UUID DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_jobs_batch ON jobs(batch_id) WHERE batch_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at) WHERE status IN ('generating', 'queued');

-- Chapters table additions
ALTER TABLE chapters
    ADD COLUMN IF NOT EXISTS qa_score FLOAT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS flesch_kincaid_grade FLOAT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS flesch_reading_ease FLOAT DEFAULT NULL;
