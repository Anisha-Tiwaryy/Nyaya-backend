-- Run this ONCE against your database to create the table.
-- (Phase 0 explains exactly how.)

CREATE TABLE IF NOT EXISTS judgements (
    id            TEXT PRIMARY KEY,        -- e.g. "sc-2017-91938676"
    title         TEXT NOT NULL,
    citation      TEXT,
    neutral_cite  TEXT,
    court         TEXT DEFAULT 'Supreme Court of India',
    bench         TEXT,
    decided_on    DATE,
    area          TEXT,
    headnote      TEXT,
    full_text     TEXT,
    source        TEXT,                    -- 'bulk' | 'indiankanoon' | 'scraper'
    source_url    TEXT,
    cited_cases   JSONB,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);

-- Full-text search index over title + full text (fast keyword search)
CREATE INDEX IF NOT EXISTS idx_judgements_fts ON judgements
  USING GIN (to_tsvector('english', coalesce(title,'') || ' ' || coalesce(full_text,'')));

-- Filter helpers
CREATE INDEX IF NOT EXISTS idx_judgements_area ON judgements (area);
CREATE INDEX IF NOT EXISTS idx_judgements_year ON judgements (decided_on);
