-- Seed mobility exercises into the forge schema
-- Run with: psql -d forge_workouts -f scripts/seed_mobility_exercises.sql

-- Hips
INSERT INTO forge.exercises (name, muscle_group, category) VALUES
  ('90/90 Hip Stretch',   'Hips', 'mobility'),
  ('Pigeon Pose',         'Hips', 'mobility'),
  ('Hip Flexor Stretch',  'Hips', 'mobility'),
  ('Couch Stretch',       'Hips', 'mobility'),
  ('Lateral Hip Opener',  'Hips', 'mobility'),
  ('Deep Squat Hold',     'Hips', 'mobility')
ON CONFLICT (name) DO NOTHING;

-- Shoulders
INSERT INTO forge.exercises (name, muscle_group, category) VALUES
  ('Shoulder Dislocates',     'Shoulders', 'mobility'),
  ('Wall Slides',             'Shoulders', 'mobility'),
  ('Doorframe Chest Stretch', 'Shoulders', 'mobility'),
  ('Thread the Needle',       'Shoulders', 'mobility'),
  ('Overhead Band Stretch',   'Shoulders', 'mobility')
ON CONFLICT (name) DO NOTHING;

-- Ankles
INSERT INTO forge.exercises (name, muscle_group, category) VALUES
  ('Ankle Circles',              'Ankles', 'mobility'),
  ('Banded Ankle Distraction',   'Ankles', 'mobility'),
  ('Calf Stretch (Wall)',        'Ankles', 'mobility'),
  ('Soleus Stretch',             'Ankles', 'mobility'),
  ('Ankle Dorsiflexion Stretch', 'Ankles', 'mobility')
ON CONFLICT (name) DO NOTHING;

-- Thoracic Spine
INSERT INTO forge.exercises (name, muscle_group, category) VALUES
  ('Thoracic Rotation',        'Thoracic Spine', 'mobility'),
  ('Cat-Cow',                  'Thoracic Spine', 'mobility'),
  ('Foam Roll Thoracic Spine', 'Thoracic Spine', 'mobility'),
  ('Seated Spinal Twist',      'Thoracic Spine', 'mobility'),
  ('Open Book Stretch',        'Thoracic Spine', 'mobility')
ON CONFLICT (name) DO NOTHING;

-- Hamstrings
INSERT INTO forge.exercises (name, muscle_group, category) VALUES
  ('Standing Hamstring Stretch', 'Hamstrings', 'mobility'),
  ('Seated Forward Fold',        'Hamstrings', 'mobility'),
  ('Lying Hamstring Stretch',    'Hamstrings', 'mobility'),
  ('Good Morning Stretch',       'Hamstrings', 'mobility')
ON CONFLICT (name) DO NOTHING;

-- Full Body / General
INSERT INTO forge.exercises (name, muscle_group, category) VALUES
  ('World''s Greatest Stretch', 'Full Body', 'mobility'),
  ('Inchworm',                  'Full Body', 'mobility'),
  ('Bear Crawl',                'Full Body', 'mobility'),
  ('Yoga Flow',                 'Full Body', 'mobility'),
  ('Foam Rolling (General)',    'Full Body', 'mobility')
ON CONFLICT (name) DO NOTHING;
