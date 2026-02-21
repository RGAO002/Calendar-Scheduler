-- Evlin Calendar Scheduler - Supabase DDL
-- Run this in the Supabase SQL Editor

-- ============================================
-- STUDENTS
-- ============================================
CREATE TABLE students (
    id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    first_name    VARCHAR(100) NOT NULL,
    last_name     VARCHAR(100) NOT NULL,
    grade_level   INTEGER NOT NULL CHECK (grade_level BETWEEN 1 AND 12),
    date_of_birth DATE,
    parent_name   VARCHAR(200),
    parent_email  VARCHAR(200),
    notes         TEXT,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- COURSES
-- ============================================
CREATE TABLE courses (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    code            VARCHAR(20) UNIQUE NOT NULL,
    title           VARCHAR(200) NOT NULL,
    subject         VARCHAR(50) NOT NULL,
    grade_level_min INTEGER NOT NULL CHECK (grade_level_min BETWEEN 1 AND 12),
    grade_level_max INTEGER NOT NULL CHECK (grade_level_max BETWEEN 1 AND 12),
    description     TEXT,
    duration_weeks  INTEGER NOT NULL DEFAULT 12,
    hours_per_week  NUMERIC(3,1) NOT NULL DEFAULT 3.0,
    difficulty      VARCHAR(20) DEFAULT 'standard',
    prerequisites   TEXT[] DEFAULT '{}',
    tags            TEXT[] DEFAULT '{}',
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- AVAILABILITY (student weekly time slots)
-- ============================================
CREATE TABLE availability (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id  UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    start_time  TIME NOT NULL,
    end_time    TIME NOT NULL,
    preference  VARCHAR(20) DEFAULT 'available',
    CHECK (end_time > start_time)
);
CREATE INDEX idx_availability_student ON availability(student_id);

-- ============================================
-- SCHEDULES (student <-> course enrollment)
-- ============================================
CREATE TABLE schedules (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id  UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course_id   UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    status      VARCHAR(20) DEFAULT 'proposed',
    start_date  DATE NOT NULL,
    end_date    DATE,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE(student_id, course_id, start_date)
);
CREATE INDEX idx_schedules_student ON schedules(student_id);
CREATE INDEX idx_schedules_status ON schedules(status);

-- ============================================
-- SCHEDULE SLOTS (weekly time blocks)
-- ============================================
CREATE TABLE schedule_slots (
    id           UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    schedule_id  UUID NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    day_of_week  INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    start_time   TIME NOT NULL,
    end_time     TIME NOT NULL,
    location     VARCHAR(100) DEFAULT 'Home',
    CHECK (end_time > start_time)
);
CREATE INDEX idx_slots_schedule ON schedule_slots(schedule_id);

-- ============================================
-- GENERATED PDFs
-- ============================================
CREATE TABLE generated_pdfs (
    id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id    UUID REFERENCES students(id),
    course_id     UUID REFERENCES courses(id),
    pdf_type      VARCHAR(50) NOT NULL,
    title         VARCHAR(300) NOT NULL,
    minio_bucket  VARCHAR(100) NOT NULL DEFAULT 'evlin-pdfs',
    minio_key     VARCHAR(500) NOT NULL,
    file_size_kb  INTEGER,
    page_count    INTEGER,
    metadata      JSONB DEFAULT '{}',
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- OCR DOCUMENTS
-- ============================================
CREATE TABLE ocr_documents (
    id                UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    original_filename VARCHAR(300) NOT NULL,
    minio_key         VARCHAR(500) NOT NULL,
    extracted_text    TEXT,
    confidence        NUMERIC(5,2),
    status            VARCHAR(20) DEFAULT 'pending',
    processed_at      TIMESTAMPTZ,
    created_at        TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- AGENT CONVERSATIONS
-- ============================================
CREATE TABLE agent_conversations (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id  UUID REFERENCES students(id),
    agent_type  VARCHAR(30) NOT NULL,
    messages    JSONB NOT NULL DEFAULT '[]',
    summary     TEXT,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);
