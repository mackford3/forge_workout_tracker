-- Fix workout_type check constraint to include 'fortime'
ALTER TABLE workouts DROP CONSTRAINT IF EXISTS workouts_workout_type_check;
ALTER TABLE workouts ADD CONSTRAINT workouts_workout_type_check
  CHECK (workout_type IN (
    'strength','strength+cardio','cardio','run','bike',
    'mobility','hyrox','circuit','amrap','emom','fortime'
  ));

-- Add round_splits column to circuits for For Time split tracking
ALTER TABLE circuits ADD COLUMN IF NOT EXISTS round_splits JSONB;
