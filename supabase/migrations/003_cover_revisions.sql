-- Migration 003: Cover Revisions audit trail table
-- Safe to run multiple times (IF NOT EXISTS guard)

CREATE TABLE IF NOT EXISTS cover_revisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    feedback TEXT NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revision_number INT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cover_revisions_job_number ON cover_revisions(job_id, revision_number DESC);
CREATE INDEX IF NOT EXISTS idx_cover_revisions_job_time ON cover_revisions(job_id, requested_at DESC);
