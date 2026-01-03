-- agree to disagree database schema 

-- enable uuid extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    max_researches INTEGER DEFAULT 3,
    researches_used INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- queries table (with thread_id for conversation persistence)
CREATE TABLE IF NOT EXISTS queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    thread_id TEXT,
    query_text TEXT NOT NULL,
    title TEXT,
    is_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- reports table (full structured report data)
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_id UUID REFERENCES queries(id) ON DELETE CASCADE,
    summary TEXT,
    claim_a JSONB DEFAULT '{}'::jsonb,
    claim_b JSONB DEFAULT '{}'::jsonb,
    agreements JSONB DEFAULT '[]'::jsonb,
    disagreements JSONB DEFAULT '[]'::jsonb,
    uncertainties JSONB DEFAULT '[]'::jsonb,
    citations JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- create indexes
CREATE INDEX IF NOT EXISTS idx_queries_user_id ON queries(user_id);
CREATE INDEX IF NOT EXISTS idx_queries_thread_id ON queries(thread_id);
CREATE INDEX IF NOT EXISTS idx_queries_is_completed ON queries(is_completed);
CREATE INDEX IF NOT EXISTS idx_reports_query_id ON reports(query_id);

-- messages table to store all conversation events (progress, clarifications, reports)
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_id UUID REFERENCES queries(id) ON DELETE CASCADE,
    role TEXT NOT NULL, -- 'user', 'agent', 'clarification', 'report', 'error'
    content JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- create indexes
CREATE INDEX IF NOT EXISTS idx_messages_query_id ON messages(query_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);

-- note: langgraph checkpointer tables are created automatically by AsyncPostgresSaver.setup()
-- they include: checkpoints, checkpoint_writes, checkpoint_blobs


