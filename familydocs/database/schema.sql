-- ============================================================================
-- FamilyDocs Intelligence Hub - PostgreSQL Schema
-- ============================================================================
-- Version: 1.0
-- Description: Complete database schema for Board + Chat Hybrid System
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- BOARDS & FOLDERS
-- ============================================================================

CREATE TABLE IF NOT EXISTS boards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL DEFAULT 'board', -- 'board' or 'folder'
    parent_id UUID REFERENCES boards(id) ON DELETE CASCADE,
    workspace_id VARCHAR(100) DEFAULT 'default',

    -- PC Sync
    is_synced_to_pc BOOLEAN DEFAULT FALSE,
    pc_path VARCHAR(512),
    sync_status VARCHAR(50) DEFAULT 'pending', -- 'synced', 'pending', 'error'
    sync_error TEXT,
    last_synced_at TIMESTAMP,

    -- Canvas Position (UI)
    canvas_x FLOAT DEFAULT 0,
    canvas_y FLOAT DEFAULT 0,
    canvas_zoom FLOAT DEFAULT 1.0,
    canvas_width FLOAT DEFAULT 300,
    canvas_height FLOAT DEFAULT 200,

    -- Metadata
    description TEXT,
    ai_description TEXT, -- AI-generated description
    icon VARCHAR(50) DEFAULT '📁',
    color VARCHAR(20) DEFAULT '#8b5cf6', -- Purple default

    -- Creation Info
    created_by VARCHAR(100) DEFAULT 'user', -- 'user' or 'ai'
    auto_created BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    CONSTRAINT valid_type CHECK (type IN ('board', 'folder')),
    CONSTRAINT valid_sync_status CHECK (sync_status IN ('synced', 'pending', 'error'))
);

-- Indexes for performance
CREATE INDEX idx_boards_parent ON boards(parent_id);
CREATE INDEX idx_boards_workspace ON boards(workspace_id);
CREATE INDEX idx_boards_sync_status ON boards(sync_status);
CREATE INDEX idx_boards_created_at ON boards(created_at DESC);

-- ============================================================================
-- DOCUMENTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- File Info
    filename VARCHAR(512) NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    file_type VARCHAR(100), -- 'pdf', 'image', 'txt', 'docx', etc.
    file_size BIGINT, -- bytes
    mime_type VARCHAR(100),

    -- Content
    extracted_text TEXT, -- OCR/extracted text
    summary TEXT, -- AI-generated summary

    -- Classification
    category VARCHAR(100), -- 'school', 'health', 'finance', etc.
    tags TEXT[], -- Array of tags

    -- Source
    source VARCHAR(100) DEFAULT 'upload', -- 'upload', 'gmail', 'scan', etc.
    source_metadata JSONB, -- Extra metadata from source

    -- AI Analysis
    ai_confidence FLOAT DEFAULT 0.0, -- 0.0 to 1.0
    ai_metadata JSONB, -- AI-extracted entities, dates, etc.

    -- Timestamps
    document_date DATE, -- Date from document content
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    CONSTRAINT valid_confidence CHECK (ai_confidence >= 0.0 AND ai_confidence <= 1.0)
);

-- Indexes
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_file_type ON documents(file_type);
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX idx_documents_document_date ON documents(document_date DESC);

-- Full-text search on extracted text
CREATE INDEX idx_documents_text_search ON documents USING gin(to_tsvector('german', extracted_text));

-- ============================================================================
-- BOARD-DOCUMENT RELATIONSHIPS (Many-to-Many)
-- ============================================================================

CREATE TABLE IF NOT EXISTS board_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Relationship Metadata
    added_by VARCHAR(100) DEFAULT 'user', -- 'user' or 'ai'
    relevance_score FLOAT DEFAULT 1.0, -- 0.0 to 1.0, how relevant is this doc to the board

    -- Timestamps
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint: one document can only be in a board once
    CONSTRAINT unique_board_document UNIQUE (board_id, document_id),
    CONSTRAINT valid_relevance CHECK (relevance_score >= 0.0 AND relevance_score <= 1.0)
);

-- Indexes
CREATE INDEX idx_board_docs_board ON board_documents(board_id);
CREATE INDEX idx_board_docs_document ON board_documents(document_id);
CREATE INDEX idx_board_docs_relevance ON board_documents(relevance_score DESC);

-- ============================================================================
-- BOARD LINKS/RELATIONSHIPS
-- ============================================================================

CREATE TABLE IF NOT EXISTS board_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    board_id_from UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    board_id_to UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,

    -- Link Type
    link_type VARCHAR(50) NOT NULL DEFAULT 'related', -- 'related', 'depends_on', 'affects', 'references'
    reason TEXT, -- Why are these boards linked?

    -- Metadata
    created_by VARCHAR(100) DEFAULT 'user', -- 'user' or 'ai'
    confidence FLOAT DEFAULT 1.0, -- For AI-suggested links

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Prevent self-links and duplicates
    CONSTRAINT no_self_link CHECK (board_id_from != board_id_to),
    CONSTRAINT unique_board_link UNIQUE (board_id_from, board_id_to, link_type),
    CONSTRAINT valid_link_type CHECK (link_type IN ('related', 'depends_on', 'affects', 'references'))
);

-- Indexes
CREATE INDEX idx_board_links_from ON board_links(board_id_from);
CREATE INDEX idx_board_links_to ON board_links(board_id_to);
CREATE INDEX idx_board_links_type ON board_links(link_type);

-- ============================================================================
-- CHAT SESSIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Session Info
    session_name VARCHAR(255),
    board_id UUID REFERENCES boards(id) ON DELETE SET NULL, -- Optional: linked to a board
    user_id VARCHAR(100) DEFAULT 'default_user',

    -- Session Type
    is_persistent BOOLEAN DEFAULT FALSE, -- Ephemeral or persistent

    -- Context Management
    active_documents UUID[], -- Array of document IDs in current context
    context_window_size INT DEFAULT 8192, -- Token limit

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP, -- NULL = persistent, otherwise ephemeral with expiry

    -- Status
    is_active BOOLEAN DEFAULT TRUE
);

-- Indexes
CREATE INDEX idx_sessions_board ON chat_sessions(board_id);
CREATE INDEX idx_sessions_user ON chat_sessions(user_id);
CREATE INDEX idx_sessions_last_activity ON chat_sessions(last_activity DESC);
CREATE INDEX idx_sessions_active ON chat_sessions(is_active) WHERE is_active = TRUE;

-- ============================================================================
-- CHAT MESSAGES
-- ============================================================================

CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,

    -- Message Content
    role VARCHAR(50) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,

    -- AI Agent Info
    agent_used VARCHAR(100), -- Which agent handled this (e.g., 'document_analyst', 'board_planner')
    model_used VARCHAR(100), -- Which LLM model was used

    -- Tool/Function Calls
    function_calls JSONB, -- Array of tool calls made
    tool_results JSONB, -- Results from tool calls

    -- Metadata
    tokens_used INT,
    response_time_ms INT, -- Response time in milliseconds

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_role CHECK (role IN ('user', 'assistant', 'system'))
);

-- Indexes
CREATE INDEX idx_messages_session ON chat_messages(session_id);
CREATE INDEX idx_messages_created_at ON chat_messages(created_at DESC);
CREATE INDEX idx_messages_agent ON chat_messages(agent_used);

-- ============================================================================
-- SMART MODULES
-- ============================================================================

CREATE TABLE IF NOT EXISTS modules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    board_id UUID REFERENCES boards(id) ON DELETE CASCADE, -- Which board this module is attached to

    -- Module Info
    module_type VARCHAR(100) NOT NULL, -- 'muellabfuhr', 'gmail_reader', 'brief_generator', etc.
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Configuration
    config JSONB NOT NULL DEFAULT '{}', -- Module-specific config (API keys, settings, etc.)

    -- Data
    data JSONB DEFAULT '{}', -- Latest data from external API

    -- Refresh Settings
    refresh_interval INT DEFAULT 86400, -- Seconds (default: 24 hours)
    last_refreshed TIMESTAMP,
    next_refresh TIMESTAMP,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_error TEXT,
    error_count INT DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_modules_board ON modules(board_id);
CREATE INDEX idx_modules_type ON modules(module_type);
CREATE INDEX idx_modules_next_refresh ON modules(next_refresh) WHERE is_active = TRUE;
CREATE INDEX idx_modules_active ON modules(is_active) WHERE is_active = TRUE;

-- ============================================================================
-- AUDIT LOG (for learning & debugging)
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Action Info
    action VARCHAR(100) NOT NULL, -- 'board_created', 'doc_uploaded', 'link_suggested', etc.
    entity_type VARCHAR(100), -- 'board', 'document', 'link', 'module', etc.
    entity_id UUID,

    -- User Decision (for AI learning)
    user_decision VARCHAR(100), -- 'accepted', 'rejected', 'modified', null
    ai_confidence FLOAT, -- Original AI confidence

    -- Context
    context JSONB, -- Additional context data

    -- Timestamp
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_audit_action ON audit_log(action);
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp DESC);

-- ============================================================================
-- VECTOR EMBEDDINGS (for RAG)
-- ============================================================================
-- NOTE: We'll use LanceDB for vector storage, but keep metadata here

CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Chunk Info
    chunk_index INT NOT NULL, -- Which chunk of the document
    chunk_text TEXT NOT NULL,

    -- Vector Info (metadata only, actual vector in LanceDB)
    vector_id VARCHAR(255), -- Reference to LanceDB vector
    embedding_model VARCHAR(100) DEFAULT 'qwen2.5-32b', -- Model used for embedding

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint
    CONSTRAINT unique_doc_chunk UNIQUE (document_id, chunk_index)
);

-- Indexes
CREATE INDEX idx_embeddings_document ON embeddings(document_id);
CREATE INDEX idx_embeddings_vector_id ON embeddings(vector_id);

-- ============================================================================
-- TRIGGERS FOR AUTO-UPDATE
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to tables
CREATE TRIGGER boards_updated_at BEFORE UPDATE ON boards
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER modules_updated_at BEFORE UPDATE ON modules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Auto-update last_activity on new chat message
CREATE OR REPLACE FUNCTION update_session_activity()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE chat_sessions
    SET last_activity = CURRENT_TIMESTAMP
    WHERE id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER message_updates_session AFTER INSERT ON chat_messages
    FOR EACH ROW EXECUTE FUNCTION update_session_activity();

-- ============================================================================
-- INITIAL DATA (Optional)
-- ============================================================================

-- Create default workspace board
INSERT INTO boards (name, type, description, workspace_id, icon, color)
VALUES
    ('FamilyDocs', 'folder', 'Root workspace for family documents', 'default', '🏠', '#8b5cf6')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- VIEWS FOR CONVENIENCE
-- ============================================================================

-- Board with document count
CREATE OR REPLACE VIEW board_stats AS
SELECT
    b.id,
    b.name,
    b.type,
    b.parent_id,
    COUNT(DISTINCT bd.document_id) as document_count,
    COUNT(DISTINCT bl_from.id) as outgoing_links,
    COUNT(DISTINCT bl_to.id) as incoming_links,
    b.created_at,
    b.updated_at
FROM boards b
LEFT JOIN board_documents bd ON b.id = bd.board_id
LEFT JOIN board_links bl_from ON b.id = bl_from.board_id_from
LEFT JOIN board_links bl_to ON b.id = bl_to.board_id_to
GROUP BY b.id;

-- Active chat sessions with message count
CREATE OR REPLACE VIEW active_sessions AS
SELECT
    cs.id,
    cs.session_name,
    cs.board_id,
    b.name as board_name,
    COUNT(cm.id) as message_count,
    cs.last_activity,
    cs.created_at
FROM chat_sessions cs
LEFT JOIN boards b ON cs.board_id = b.id
LEFT JOIN chat_messages cm ON cs.id = cm.session_id
WHERE cs.is_active = TRUE
GROUP BY cs.id, cs.session_name, cs.board_id, b.name, cs.last_activity, cs.created_at
ORDER BY cs.last_activity DESC;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE boards IS 'Boards and folders for organizing documents';
COMMENT ON TABLE documents IS 'Uploaded documents with AI analysis';
COMMENT ON TABLE board_documents IS 'Many-to-many relationship between boards and documents';
COMMENT ON TABLE board_links IS 'Relationships between boards (graph edges)';
COMMENT ON TABLE chat_sessions IS 'Chat sessions (ephemeral or persistent)';
COMMENT ON TABLE chat_messages IS 'Messages within chat sessions';
COMMENT ON TABLE modules IS 'Smart modules (widgets) attached to boards';
COMMENT ON TABLE audit_log IS 'Audit log for user actions and AI suggestions';
COMMENT ON TABLE embeddings IS 'Document chunk embeddings for RAG (metadata only)';

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
