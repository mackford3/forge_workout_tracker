-- Workout Templates Migration
-- Adds the workout_templates table for user-saved single workout templates.
-- Safe to re-run (uses IF NOT EXISTS).
-- Run against your database before restarting the app:
--   psql -d forge_workouts -f scripts/migrate_workout_templates.sql

CREATE TABLE IF NOT EXISTS forge.workout_templates (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(150) NOT NULL,
    description   TEXT,
    workout_type  VARCHAR(20) NOT NULL DEFAULT 'strength',
    source        VARCHAR(200),
    template_data TEXT,
    created_at    TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE INDEX IF NOT EXISTS idx_workout_templates_created_at
  ON forge.workout_templates(created_at DESC);
