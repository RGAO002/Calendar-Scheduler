-- Evlin Calendar Scheduler - Check-In (打卡) Tables
-- Run this in the Supabase SQL Editor AFTER setup_supabase.sql

-- ============================================
-- SESSION INSTANCES (concrete dated class sessions)
-- Generated from weekly schedule_slots templates.
-- Each row = one specific class on a specific date.
-- ============================================
CREATE TABLE IF NOT EXISTS session_instances (
    id               UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    schedule_id      UUID NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    schedule_slot_id UUID NOT NULL REFERENCES schedule_slots(id) ON DELETE CASCADE,
    session_date     DATE NOT NULL,
    start_time       TIME NOT NULL,
    end_time         TIME NOT NULL,
    status           VARCHAR(20) NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'completed', 'missed', 'rescheduled', 'cancelled')),
    checked_in_at    TIMESTAMPTZ,
    rescheduled_from UUID REFERENCES session_instances(id),
    rescheduled_to   UUID REFERENCES session_instances(id),
    notes            TEXT,
    created_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(schedule_slot_id, session_date)
);

CREATE INDEX IF NOT EXISTS idx_session_date ON session_instances(session_date);
CREATE INDEX IF NOT EXISTS idx_session_schedule ON session_instances(schedule_id);
CREATE INDEX IF NOT EXISTS idx_session_status ON session_instances(status);

-- ============================================
-- CHECKIN LOG (audit trail for all check-in actions)
-- ============================================
CREATE TABLE IF NOT EXISTS checkin_log (
    id                  UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_instance_id UUID NOT NULL REFERENCES session_instances(id) ON DELETE CASCADE,
    action              VARCHAR(20) NOT NULL
                        CHECK (action IN ('check_in', 'auto_miss', 'reschedule', 'cancel')),
    performed_by        VARCHAR(100),
    details             JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_checkin_log_session ON checkin_log(session_instance_id);
