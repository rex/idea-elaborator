CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE ideas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    concept TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    explanation TEXT,
    mvp TEXT,
    core_features TEXT,
    creative_features TEXT,
    roadmap TEXT,
    enhancements TEXT,
    issues TEXT,
    names TEXT,
    related TEXT,
    claude_code_prompt TEXT,
    roadmap_prompts TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Full-text search index
CREATE INDEX idx_concept_trgm ON ideas USING gin (concept gin_trgm_ops);
CREATE INDEX idx_explanation_trgm ON ideas USING gin (explanation gin_trgm_ops);
CREATE INDEX idx_created_at ON ideas (created_at DESC);

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_ideas_updated_at BEFORE UPDATE ON ideas
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
