-- AskBob.Ai Database Schema
-- Run this in Supabase SQL Editor to set up the database

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- Table: wiki_pages
-- Stores raw scraped wiki page data
-- ============================================
CREATE TABLE IF NOT EXISTS wiki_pages (
    id BIGSERIAL PRIMARY KEY,
    page_id INTEGER UNIQUE NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    categories TEXT[] DEFAULT '{}',
    page_type TEXT DEFAULT 'general',
    url TEXT NOT NULL,
    last_modified TIMESTAMPTZ,
    last_scraped TIMESTAMPTZ DEFAULT NOW(),
    content_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_wiki_pages_page_id ON wiki_pages(page_id);
CREATE INDEX idx_wiki_pages_title ON wiki_pages(title);
CREATE INDEX idx_wiki_pages_page_type ON wiki_pages(page_type);

-- ============================================
-- Table: wiki_chunks
-- Stores semantically chunked content
-- ============================================
CREATE TABLE IF NOT EXISTS wiki_chunks (
    id BIGSERIAL PRIMARY KEY,
    page_id INTEGER NOT NULL REFERENCES wiki_pages(page_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    title TEXT NOT NULL,
    section_header TEXT DEFAULT '',
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    page_type TEXT DEFAULT 'general',
    categories TEXT[] DEFAULT '{}',
    game_modes TEXT[] DEFAULT '{main,ironman,hardcore_ironman,ultimate_ironman,group_ironman}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(page_id, chunk_index)
);

CREATE INDEX idx_wiki_chunks_page_id ON wiki_chunks(page_id);
CREATE INDEX idx_wiki_chunks_page_type ON wiki_chunks(page_type);
CREATE INDEX idx_wiki_chunks_game_modes ON wiki_chunks USING GIN(game_modes);

-- ============================================
-- Table: wiki_embeddings
-- Stores vector embeddings for semantic search
-- ============================================
CREATE TABLE IF NOT EXISTS wiki_embeddings (
    id BIGSERIAL PRIMARY KEY,
    chunk_id BIGINT UNIQUE NOT NULL REFERENCES wiki_chunks(id) ON DELETE CASCADE,
    embedding vector(1536),
    model TEXT NOT NULL DEFAULT 'text-embedding-3-small',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW index for fast approximate nearest neighbor search
CREATE INDEX idx_wiki_embeddings_vector ON wiki_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ============================================
-- Table: scrape_state
-- Tracks scraping progress for resume capability
-- ============================================
CREATE TABLE IF NOT EXISTS scrape_state (
    id BIGSERIAL PRIMARY KEY,
    scrape_type TEXT NOT NULL,
    last_continue TEXT DEFAULT '',
    total_pages INTEGER DEFAULT 0,
    pages_scraped INTEGER DEFAULT 0,
    status TEXT DEFAULT 'in_progress',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Function: search_wiki
-- Performs semantic similarity search
-- ============================================
CREATE OR REPLACE FUNCTION search_wiki(
    query_embedding vector(1536),
    match_count INTEGER DEFAULT 5,
    filter_page_type TEXT DEFAULT NULL,
    filter_game_mode TEXT DEFAULT NULL
)
RETURNS TABLE (
    chunk_id BIGINT,
    page_title TEXT,
    section_header TEXT,
    content TEXT,
    page_type TEXT,
    categories TEXT[],
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        wc.id AS chunk_id,
        wc.title AS page_title,
        wc.section_header,
        wc.content,
        wc.page_type,
        wc.categories,
        1 - (we.embedding <=> query_embedding) AS similarity
    FROM wiki_embeddings we
    JOIN wiki_chunks wc ON we.chunk_id = wc.id
    WHERE
        (filter_page_type IS NULL OR wc.page_type = filter_page_type)
        AND (filter_game_mode IS NULL OR filter_game_mode = ANY(wc.game_modes))
    ORDER BY we.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
