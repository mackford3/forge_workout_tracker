-- Migration: add unit_type to exercises and duration_s to workout_sets
-- Run with: psql -U <user> -d <dbname> -f scripts/migrate_unit_type.sql

ALTER TABLE exercises
  ADD COLUMN IF NOT EXISTS unit_type VARCHAR(12) DEFAULT 'reps';

ALTER TABLE workout_sets
  ADD COLUMN IF NOT EXISTS duration_s INTEGER;
