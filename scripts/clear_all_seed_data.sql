-- Clear all seed data (students + related) so you can re-run seed_data.py without duplicates.
-- Run this in Supabase SQL Editor, then run: python seed_data.py --supabase

-- Order matters (foreign keys)
DELETE FROM schedule_slots;
DELETE FROM schedules;
DELETE FROM availability;
DELETE FROM agent_conversations;
DELETE FROM generated_pdfs;
DELETE FROM students;

-- Courses are kept (they have no student FK). To reset courses too, uncomment:
-- DELETE FROM courses;
