-- Quiz Sessions table for interactive concept quizzes
CREATE TABLE IF NOT EXISTS quiz_sessions (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id      UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course_id       UUID REFERENCES courses(id),
    topic           TEXT NOT NULL,
    difficulty      VARCHAR(20) DEFAULT 'standard',
    concept         JSONB,
    questions       JSONB NOT NULL DEFAULT '[]',
    quiz_html       TEXT,
    status          VARCHAR(20) DEFAULT 'generated',
    score           INTEGER,
    total           INTEGER,
    answers         JSONB,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Index for student quiz history lookups
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_student
    ON quiz_sessions(student_id, created_at DESC);

-- RLS
ALTER TABLE quiz_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow quiz read" ON quiz_sessions
    FOR SELECT USING (true);

CREATE POLICY "Allow quiz insert" ON quiz_sessions
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow quiz update" ON quiz_sessions
    FOR UPDATE USING (true) WITH CHECK (true);
