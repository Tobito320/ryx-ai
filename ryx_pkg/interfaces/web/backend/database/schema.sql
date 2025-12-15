-- RyxHub Exam System - PostgreSQL Schema
-- Version: 1.0.0
-- Created based on RYXHUB_AUDIT_REPORT.json P1.2 fix

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- SCHOOLS & SUBJECTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS schools (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    country VARCHAR(100) DEFAULT 'Germany',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS subjects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,  -- "WBL", "IT Service", "Deutsch"
    full_name VARCHAR(255),       -- "Wirtschaft und Betriebslehre"
    lernfeld INT,                 -- Learning field number (IHK)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS teachers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,  -- "Herr Hakim"
    email VARCHAR(255),
    subject_ids TEXT[],          -- Array of subject IDs
    tests_count INT DEFAULT 0,
    pattern_learned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS themas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subject_id UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,  -- "Marktforschung", "Ticketprozess"
    description TEXT,
    subtopics TEXT[],
    frequency INT DEFAULT 0,     -- How often this thema appears in tests
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- CLASS TESTS (Uploaded by teachers/students)
-- ============================================================================

CREATE TABLE IF NOT EXISTS class_tests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE SET NULL,
    subject_id UUID REFERENCES subjects(id) ON DELETE SET NULL,
    teacher_id UUID REFERENCES teachers(id) ON DELETE SET NULL,

    -- OCR Data
    raw_content TEXT NOT NULL,           -- Full OCR text
    ocr_confidence FLOAT,                -- 0.0 - 1.0
    ocr_model_used VARCHAR(100),         -- "paddle_ocr", "tesseract", "claude_vision"

    -- Extracted Structure
    extracted_tasks JSONB NOT NULL DEFAULT '[]',  -- [ExtractedTask, ...]
    metadata_confidence JSONB NOT NULL DEFAULT '{}',  -- {subject: 0.95, teacher: 0.80, ...}

    -- Verification
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP WITH TIME ZONE,
    verified_by UUID,                    -- User who verified

    -- Duplicate Detection
    content_hash VARCHAR(64),            -- MD5 hash for duplicate detection
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of UUID REFERENCES class_tests(id) ON DELETE SET NULL,

    -- Metadata
    thema_ids UUID[],
    exam_date DATE,
    exam_duration_minutes INT,
    total_points INT,

    -- File Info
    original_filename VARCHAR(255),
    file_type VARCHAR(50),               -- "pdf", "image"
    file_size_bytes BIGINT,
    file_path VARCHAR(500),              -- Storage path

    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- MOCK EXAMS (AI-Generated practice exams)
-- ============================================================================

CREATE TABLE IF NOT EXISTS mock_exams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE SET NULL,
    subject_id UUID REFERENCES subjects(id) ON DELETE SET NULL,

    -- Exam Content
    title VARCHAR(255),
    tasks JSONB NOT NULL DEFAULT '[]',   -- [Task, ...]
    total_points INT NOT NULL DEFAULT 0,
    estimated_duration_minutes INT,
    difficulty_level INT CHECK (difficulty_level BETWEEN 1 AND 5),

    -- Generation Context (for reproducibility)
    generation_context JSONB NOT NULL DEFAULT '{}',  -- {themas, free_prompt, model, context_texts}
    free_prompt_used TEXT,               -- User's custom instructions
    context_texts_used TEXT[],           -- Pasted context material

    -- Teacher Pattern
    teacher_pattern_applied BOOLEAN DEFAULT FALSE,
    teacher_pattern_id UUID REFERENCES teachers(id) ON DELETE SET NULL,

    -- Metadata
    thema_ids UUID[],
    status VARCHAR(50) DEFAULT 'ready',  -- ready, archived, draft

    -- AI Generation Info
    generator_model VARCHAR(100),        -- "ollama:qwen2.5-coder:14b", "claude-opus-4.5"
    generation_time_ms INT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- ATTEMPTS (Student exam attempts)
-- ============================================================================

CREATE TABLE IF NOT EXISTS attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mock_exam_id UUID NOT NULL REFERENCES mock_exams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,               -- Student UUID

    -- Responses
    task_responses JSONB NOT NULL DEFAULT '{}',  -- {task_id: {user_answer, answered_at, time_spent}}

    -- Timing
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    finished_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INT,

    -- Scoring (populated after grading)
    total_score FLOAT,
    total_points INT,
    percentage FLOAT,
    grade FLOAT,                         -- 1.0-6.0 (German scale)
    grade_text VARCHAR(50),              -- "Sehr gut", "Gut", etc.

    -- Section Breakdown
    section_breakdown JSONB DEFAULT '{}',

    -- Flags
    status VARCHAR(50) DEFAULT 'in_progress',  -- in_progress, submitted, graded, reviewed
    flags_for_review TEXT[],             -- Task IDs flagged for manual review
    overall_feedback TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- GRADING RESULTS (AI-Generated grades)
-- ============================================================================

CREATE TABLE IF NOT EXISTS grading_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    attempt_id UUID NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
    mock_exam_id UUID NOT NULL REFERENCES mock_exams(id) ON DELETE CASCADE,

    -- Overall Score
    total_score FLOAT NOT NULL,
    total_points INT NOT NULL,
    percentage FLOAT NOT NULL,
    grade FLOAT NOT NULL,                -- 1.0-6.0
    grade_text VARCHAR(50),

    -- Per-Task Grades
    task_grades JSONB NOT NULL DEFAULT '[]',  -- [TaskGrade, ...]

    -- Feedback
    overall_feedback TEXT,
    strengths TEXT[],
    areas_for_improvement TEXT[],

    -- Grader Info
    grader_model VARCHAR(100),           -- "ollama:qwen2.5-coder:14b", "claude-opus-4.5"
    grader_confidence FLOAT,             -- 0.0-1.0
    processing_time_ms INT,

    -- Review Flags
    manual_review_flagged BOOLEAN DEFAULT FALSE,
    tasks_needing_review TEXT[],         -- Task IDs with low confidence
    reviewed_at TIMESTAMP WITH TIME ZONE,
    reviewed_by UUID,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- UPLOAD SESSIONS (Temporary storage during OCR/review flow)
-- ============================================================================

CREATE TABLE IF NOT EXISTS upload_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- File Info
    original_filename VARCHAR(255),
    file_type VARCHAR(50),
    file_size_bytes BIGINT,
    temp_file_path VARCHAR(500),
    content_hash VARCHAR(64),

    -- OCR Results
    ocr_text TEXT,
    ocr_confidence FLOAT,
    ocr_model_used VARCHAR(100),

    -- Classification Results
    classification JSONB DEFAULT '{}',   -- {subject, teacher, thema, date, ...}
    confidence_scores JSONB DEFAULT '{}',
    extracted_tasks JSONB DEFAULT '[]',

    -- Review Status
    status VARCHAR(50) DEFAULT 'pending_review',  -- pending_review, approved, rejected, expired
    requires_review BOOLEAN DEFAULT TRUE,

    -- Timing
    expires_at TIMESTAMP WITH TIME ZONE,  -- Session expiration
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- TEACHER PATTERNS (Learned exam patterns from uploaded tests)
-- ============================================================================

CREATE TABLE IF NOT EXISTS teacher_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    teacher_id UUID NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
    subject_id UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,

    -- Pattern Data
    tests_analyzed INT DEFAULT 0,
    task_type_distribution JSONB DEFAULT '{}',  -- {MC: 0.3, ShortAnswer: 0.5, ...}
    common_themas TEXT[],
    average_difficulty FLOAT,
    average_points_per_task FLOAT,

    -- Style Preferences
    prefers_case_studies BOOLEAN DEFAULT FALSE,
    prefers_calculations BOOLEAN DEFAULT FALSE,
    prefers_diagrams BOOLEAN DEFAULT FALSE,
    typical_exam_duration INT,
    typical_task_count INT,

    -- Example Questions (anonymized)
    example_questions JSONB DEFAULT '[]',

    last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- INDICES
-- ============================================================================

-- Class Tests
CREATE INDEX IF NOT EXISTS idx_class_tests_subject ON class_tests(subject_id);
CREATE INDEX IF NOT EXISTS idx_class_tests_teacher ON class_tests(teacher_id);
CREATE INDEX IF NOT EXISTS idx_class_tests_verified ON class_tests(verified);
CREATE INDEX IF NOT EXISTS idx_class_tests_content_hash ON class_tests(content_hash);
CREATE INDEX IF NOT EXISTS idx_class_tests_uploaded_at ON class_tests(uploaded_at DESC);

-- Mock Exams
CREATE INDEX IF NOT EXISTS idx_mock_exams_subject ON mock_exams(subject_id);
CREATE INDEX IF NOT EXISTS idx_mock_exams_difficulty ON mock_exams(difficulty_level);
CREATE INDEX IF NOT EXISTS idx_mock_exams_created_at ON mock_exams(created_at DESC);

-- Attempts
CREATE INDEX IF NOT EXISTS idx_attempts_user ON attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_attempts_mock_exam ON attempts(mock_exam_id);
CREATE INDEX IF NOT EXISTS idx_attempts_status ON attempts(status);
CREATE INDEX IF NOT EXISTS idx_attempts_started_at ON attempts(started_at DESC);

-- Grading Results
CREATE INDEX IF NOT EXISTS idx_grading_attempt ON grading_results(attempt_id);
CREATE INDEX IF NOT EXISTS idx_grading_mock_exam ON grading_results(mock_exam_id);
CREATE INDEX IF NOT EXISTS idx_grading_manual_review ON grading_results(manual_review_flagged);

-- Upload Sessions
CREATE INDEX IF NOT EXISTS idx_upload_sessions_status ON upload_sessions(status);
CREATE INDEX IF NOT EXISTS idx_upload_sessions_expires ON upload_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_upload_sessions_hash ON upload_sessions(content_hash);

-- Teacher Patterns
CREATE INDEX IF NOT EXISTS idx_teacher_patterns_teacher ON teacher_patterns(teacher_id);
CREATE INDEX IF NOT EXISTS idx_teacher_patterns_subject ON teacher_patterns(subject_id);

-- ============================================================================
-- SEED DATA: Default School + Subjects
-- ============================================================================

INSERT INTO schools (id, name, location, country) VALUES
    ('cuno-berufskolleg-hagen', 'Cuno Berufskolleg Hagen', 'Hagen, NRW', 'Germany')
ON CONFLICT (id) DO NOTHING;

INSERT INTO subjects (id, school_id, name, full_name) VALUES
    ('wbl', 'cuno-berufskolleg-hagen', 'WBL', 'Wirtschaft und Betriebslehre'),
    ('bwl', 'cuno-berufskolleg-hagen', 'BWL', 'Betriebswirtschaftslehre'),
    ('it-service', 'cuno-berufskolleg-hagen', 'IT Service', 'IT Service Management'),
    ('deutsch', 'cuno-berufskolleg-hagen', 'Deutsch', 'Deutsch / Kommunikation'),
    ('mathe', 'cuno-berufskolleg-hagen', 'Mathe', 'Mathematik')
ON CONFLICT (id) DO NOTHING;

INSERT INTO themas (id, subject_id, name, description) VALUES
    ('marktforschung', 'wbl', 'Marktforschung', 'Methoden der Marktforschung'),
    ('marketingmix', 'wbl', 'Marketingmix (4Ps)', 'Product, Price, Place, Promotion'),
    ('kundenakquisition', 'wbl', 'Kundenakquisition', 'Kundengewinnung und -bindung'),
    ('preismanagement', 'wbl', 'Preismanagement', 'Preisstrategien und Kalkulation'),
    ('werbung', 'wbl', 'Werbung & Kommunikation', 'Werbemittel und -träger'),
    ('incident-management', 'it-service', 'Incident Management', 'ITIL Incident Management Process'),
    ('sla', 'it-service', 'Service Level Agreements', 'SLA Definition und Monitoring'),
    ('netzwerke', 'it-service', 'Netzwerktechnik', 'Netzwerktopologien und Protokolle')
ON CONFLICT (id) DO NOTHING;
