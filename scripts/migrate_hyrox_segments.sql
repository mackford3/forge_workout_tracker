-- Hyrox Enhancement Migration
-- Adds missing columns to workouts + hyrox_stations, and creates hyrox_station_segments.
-- All statements use IF NOT EXISTS guards — safe to re-run.
-- Run against your database before restarting the app:
--   psql -d forge_workouts -f scripts/migrate_hyrox_segments.sql

-- workouts table: session_rpe was added to the model but not yet to the DB
ALTER TABLE forge.workouts
  ADD COLUMN IF NOT EXISTS session_rpe NUMERIC(3,1);

-- Add new columns to hyrox_stations
ALTER TABLE forge.hyrox_stations
  ADD COLUMN IF NOT EXISTS is_substituted     BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS sub_exercise_name  VARCHAR(100),
  ADD COLUMN IF NOT EXISTS had_break          BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS damper             INTEGER,
  ADD COLUMN IF NOT EXISTS rest_after_s       INTEGER;

-- Create new hyrox_station_segments table
CREATE TABLE IF NOT EXISTS forge.hyrox_station_segments (
    id               SERIAL PRIMARY KEY,
    hyrox_station_id INTEGER NOT NULL REFERENCES forge.hyrox_stations(id) ON DELETE CASCADE,
    segment_order    INTEGER NOT NULL,
    distance_m       INTEGER,
    reps             INTEGER,
    weight_kg        NUMERIC(6, 2),
    weight_lbs       NUMERIC(6, 2),
    time_s           INTEGER,
    notes            TEXT
);

CREATE INDEX IF NOT EXISTS idx_hyrox_station_segments_station_id
  ON forge.hyrox_station_segments(hyrox_station_id);
