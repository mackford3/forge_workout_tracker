from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class WorkoutPlan(db.Model):
    __tablename__ = 'workout_plans'
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active   = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    days        = db.relationship('PlanDay', backref='plan', lazy='dynamic', cascade='all, delete-orphan')


class PlanDay(db.Model):
    __tablename__ = 'plan_days'
    id          = db.Column(db.Integer, primary_key=True)
    plan_id     = db.Column(db.Integer, db.ForeignKey('workout_plans.id'), nullable=False)
    week_number = db.Column(db.Integer, default=1)
    day_of_week = db.Column(db.String(10), nullable=False)
    name        = db.Column(db.String(100))
    notes       = db.Column(db.Text)
    order_index = db.Column(db.Integer, default=0)
    workouts    = db.relationship('Workout', backref='plan_day', lazy='dynamic')


class Exercise(db.Model):
    __tablename__ = 'exercises'
    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(100), nullable=False, unique=True)
    muscle_group = db.Column(db.String(50))
    category     = db.Column(db.String(50), default='strength')
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)


class Workout(db.Model):
    __tablename__ = 'workouts'
    id               = db.Column(db.Integer, primary_key=True)
    plan_day_id      = db.Column(db.Integer, db.ForeignKey('plan_days.id'), nullable=True)
    workout_type     = db.Column(db.String(20), nullable=False)
    name             = db.Column(db.String(100), nullable=False)
    location         = db.Column(db.String(20), default='gym')
    time_of_day      = db.Column(db.Time)
    duration_minutes = db.Column(db.Integer)
    calories         = db.Column(db.Integer)
    avg_bpm          = db.Column(db.Integer)
    notes            = db.Column(db.Text)
    completed_at     = db.Column(db.DateTime, default=datetime.utcnow)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    sets        = db.relationship('WorkoutSet',  backref='workout', lazy='dynamic', cascade='all, delete-orphan')
    cardio_sets = db.relationship('CardioSet',   backref='workout', lazy='dynamic', cascade='all, delete-orphan')
    runs        = db.relationship('Run',         backref='workout', lazy='dynamic', cascade='all, delete-orphan')
    hyrox       = db.relationship('HyroxResult', backref='workout', lazy='dynamic', cascade='all, delete-orphan')
    circuits    = db.relationship('Circuit',     backref='workout', lazy='dynamic', cascade='all, delete-orphan')


class WorkoutSet(db.Model):
    __tablename__ = 'workout_sets'
    id            = db.Column(db.Integer, primary_key=True)
    workout_id    = db.Column(db.Integer, db.ForeignKey('workouts.id'), nullable=False)
    exercise_id   = db.Column(db.Integer, db.ForeignKey('exercises.id'), nullable=False)
    set_number    = db.Column(db.Integer, nullable=False)
    weight_kg     = db.Column(db.Numeric(6, 2))
    weight_lbs    = db.Column(db.Numeric(6, 2))
    reps          = db.Column(db.Integer)
    steps         = db.Column(db.Integer)
    distance_m    = db.Column(db.Numeric(7, 1))
    assist_weight = db.Column(db.Numeric(6, 2))
    is_assisted   = db.Column(db.Boolean, default=False)
    rpe           = db.Column(db.Numeric(3, 1))
    skipped       = db.Column(db.Boolean, default=False)
    notes         = db.Column(db.Text)
    exercise      = db.relationship('Exercise')


class CardioSet(db.Model):
    __tablename__ = 'cardio_sets'
    id           = db.Column(db.Integer, primary_key=True)
    workout_id   = db.Column(db.Integer, db.ForeignKey('workouts.id'), nullable=False)
    machine      = db.Column(db.String(30), nullable=False)
    set_number   = db.Column(db.Integer, default=1)
    distance_m   = db.Column(db.Integer)
    duration_s   = db.Column(db.Integer)
    pace_split_s = db.Column(db.Integer)
    calories     = db.Column(db.Integer)
    avg_bpm      = db.Column(db.Integer)
    damper       = db.Column(db.Integer)
    rpe          = db.Column(db.Numeric(3, 1))
    notes        = db.Column(db.Text)


class Run(db.Model):
    __tablename__ = 'runs'
    id                = db.Column(db.Integer, primary_key=True)
    workout_id        = db.Column(db.Integer, db.ForeignKey('workouts.id'), nullable=False)
    run_type          = db.Column(db.String(20), default='continuous')
    total_distance_km = db.Column(db.Numeric(7, 3))
    total_duration_s  = db.Column(db.Integer)
    avg_heart_rate    = db.Column(db.Integer)
    avg_pace_s        = db.Column(db.Integer)
    route_notes       = db.Column(db.Text)
    segments          = db.relationship('RunSegment', backref='run', lazy='dynamic', cascade='all, delete-orphan')


class RunSegment(db.Model):
    __tablename__ = 'run_segments'
    id             = db.Column(db.Integer, primary_key=True)
    run_id         = db.Column(db.Integer, db.ForeignKey('runs.id'), nullable=False)
    segment_type   = db.Column(db.String(20), nullable=False)
    segment_number = db.Column(db.Integer, nullable=False)
    distance_km    = db.Column(db.Numeric(6, 4))
    duration_s     = db.Column(db.Integer)
    pace_per_km_s  = db.Column(db.Integer)
    avg_bpm        = db.Column(db.Integer)
    skipped        = db.Column(db.Boolean, default=False)
    notes          = db.Column(db.Text)


class HyroxResult(db.Model):
    __tablename__ = 'hyrox_results'
    id             = db.Column(db.Integer, primary_key=True)
    workout_id     = db.Column(db.Integer, db.ForeignKey('workouts.id'), nullable=False)
    total_time_s   = db.Column(db.Integer)
    running_time_s = db.Column(db.Integer)
    workout_time_s = db.Column(db.Integer)
    location       = db.Column(db.String(100))
    race_type      = db.Column(db.String(20), default='singles')
    notes          = db.Column(db.Text)
    stations       = db.relationship('HyroxStation', backref='result', lazy='dynamic', cascade='all, delete-orphan')


HYROX_DEFAULT_STATIONS = [
    ("1km Run",           1,  None, None),
    ("SkiErg",            2,  1000, None),
    ("1km Run",           3,  None, None),
    ("Sled Push",         4,  50,   None),
    ("1km Run",           5,  None, None),
    ("Sled Pull",         6,  50,   None),
    ("1km Run",           7,  None, None),
    ("Burpee Broad Jump", 8,  80,   None),
    ("1km Run",           9,  None, None),
    ("Row",               10, 1000, None),
    ("1km Run",           11, None, None),
    ("Farmers Carry",     12, 200,  None),
    ("1km Run",           13, None, None),
    ("Sandbag Lunges",    14, 100,  None),
    ("1km Run",           15, None, None),
    ("Wall Balls",        16, None, 100),
]


class HyroxStation(db.Model):
    __tablename__ = 'hyrox_stations'
    id              = db.Column(db.Integer, primary_key=True)
    hyrox_result_id = db.Column(db.Integer, db.ForeignKey('hyrox_results.id'), nullable=False)
    station_order   = db.Column(db.Integer, nullable=False)
    station_name    = db.Column(db.String(100), nullable=False)
    time_s          = db.Column(db.Integer)
    weight_kg       = db.Column(db.Numeric(6, 2))
    weight_lbs      = db.Column(db.Numeric(6, 2))
    distance_m      = db.Column(db.Integer)
    reps            = db.Column(db.Integer)
    notes           = db.Column(db.Text)


class Circuit(db.Model):
    __tablename__ = 'circuits'
    id               = db.Column(db.Integer, primary_key=True)
    workout_id       = db.Column(db.Integer, db.ForeignKey('workouts.id'), nullable=False)
    circuit_type     = db.Column(db.String(10), default='circuit')
    rounds_target    = db.Column(db.Integer)
    rounds_completed = db.Column(db.Numeric(4, 1))
    time_cap_s       = db.Column(db.Integer)
    total_time_s     = db.Column(db.Integer)
    notes            = db.Column(db.Text)
    exercises        = db.relationship('CircuitExercise', backref='circuit', lazy='dynamic',
                                       order_by='CircuitExercise.order_index', cascade='all, delete-orphan')


class CircuitExercise(db.Model):
    __tablename__ = 'circuit_exercises'
    id                = db.Column(db.Integer, primary_key=True)
    circuit_id        = db.Column(db.Integer, db.ForeignKey('circuits.id'), nullable=False)
    exercise_id       = db.Column(db.Integer, db.ForeignKey('exercises.id'), nullable=False)
    order_index       = db.Column(db.Integer, nullable=False)
    target_reps       = db.Column(db.Integer)
    target_weight_lbs = db.Column(db.Numeric(6, 2))
    target_distance_m = db.Column(db.Integer)
    notes             = db.Column(db.Text)
    exercise          = db.relationship('Exercise')
    round_sets        = db.relationship('CircuitRoundSet', backref='circuit_exercise',
                                        lazy='dynamic', cascade='all, delete-orphan')


class CircuitRoundSet(db.Model):
    __tablename__ = 'circuit_round_sets'
    id                  = db.Column(db.Integer, primary_key=True)
    circuit_exercise_id = db.Column(db.Integer, db.ForeignKey('circuit_exercises.id'), nullable=False)
    round_number        = db.Column(db.Integer, nullable=False)
    reps                = db.Column(db.Integer)
    weight_lbs          = db.Column(db.Numeric(6, 2))
    weight_kg           = db.Column(db.Numeric(6, 2))
    duration_s          = db.Column(db.Integer)
    distance_m          = db.Column(db.Numeric(7, 1))
    steps               = db.Column(db.Integer)
    skipped             = db.Column(db.Boolean, default=False)
    notes               = db.Column(db.Text)


# ── Structured Program ──────────────────────────────────────

class Program(db.Model):
    __tablename__ = 'programs'
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    total_weeks = db.Column(db.Integer, nullable=False)
    is_active   = db.Column(db.Boolean, default=False)
    start_date  = db.Column(db.Date)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    phases      = db.relationship('ProgramPhase', backref='program', lazy='dynamic',
                                  order_by='ProgramPhase.phase_number', cascade='all, delete-orphan')
    days        = db.relationship('ProgramDay',   backref='program', lazy='dynamic',
                                  cascade='all, delete-orphan')


class ProgramPhase(db.Model):
    __tablename__ = 'program_phases'
    id           = db.Column(db.Integer, primary_key=True)
    program_id   = db.Column(db.Integer, db.ForeignKey('programs.id'), nullable=False)
    phase_number = db.Column(db.Integer, nullable=False)
    name         = db.Column(db.String(150))
    focus        = db.Column(db.Text)
    week_start   = db.Column(db.Integer, nullable=False)
    week_end     = db.Column(db.Integer, nullable=False)


class ProgramDay(db.Model):
    __tablename__ = 'program_days'
    id              = db.Column(db.Integer, primary_key=True)
    program_id      = db.Column(db.Integer, db.ForeignKey('programs.id'), nullable=False)
    phase_id        = db.Column(db.Integer, db.ForeignKey('program_phases.id'))
    week_number     = db.Column(db.Integer, nullable=False)
    day_of_week     = db.Column(db.String(10), nullable=False)
    day_number      = db.Column(db.Integer, nullable=False)
    sequence_number = db.Column(db.Integer)  # global order for delay shifting
    name            = db.Column(db.String(150))
    exercises       = db.Column(db.Text)   # JSON array string
    notes           = db.Column(db.Text)
    completions     = db.relationship('ProgramCompletion', backref='day', lazy='dynamic',
                                      cascade='all, delete-orphan')


class ProgramCompletion(db.Model):
    __tablename__ = 'program_completions'
    id         = db.Column(db.Integer, primary_key=True)
    day_id     = db.Column(db.Integer, db.ForeignKey('program_days.id'), nullable=False)
    workout_id = db.Column(db.Integer, db.ForeignKey('workouts.id'), nullable=True)
    completed  = db.Column(db.Boolean, default=False)
    status     = db.Column(db.String(20), default='done')  # done/skipped/altered/delayed
    done_date  = db.Column(db.Date)
    skipped_at = db.Column(db.Date)
    notes      = db.Column(db.Text)
    workout    = db.relationship('Workout')

# Status options
COMPLETION_STATUSES = ['done', 'skipped', 'altered', 'delayed']


# ── Premade Workouts (Fitness Tests / Benchmarks) ──────────

class PremadeWorkout(db.Model):
    __tablename__ = 'premade_workouts'
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    category    = db.Column(db.String(50), default='fitness_test')
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    stations    = db.relationship('PremadeStation', backref='workout',
                                  order_by='PremadeStation.station_order',
                                  lazy='dynamic', cascade='all, delete-orphan')
    results     = db.relationship('PremadeResult', backref='premade_workout',
                                  lazy='dynamic', cascade='all, delete-orphan')


class PremadeStation(db.Model):
    __tablename__ = 'premade_stations'
    id                 = db.Column(db.Integer, primary_key=True)
    premade_workout_id = db.Column(db.Integer, db.ForeignKey('premade_workouts.id'), nullable=False)
    station_order      = db.Column(db.Integer, nullable=False)
    name               = db.Column(db.String(150), nullable=False)
    target_reps        = db.Column(db.Integer)
    target_distance_m  = db.Column(db.Numeric(8, 2))
    target_weight_lbs  = db.Column(db.Numeric(6, 2))
    notes              = db.Column(db.Text)


class PremadeResult(db.Model):
    __tablename__ = 'premade_results'
    id                 = db.Column(db.Integer, primary_key=True)
    premade_workout_id = db.Column(db.Integer, db.ForeignKey('premade_workouts.id'), nullable=False)
    workout_id         = db.Column(db.Integer, db.ForeignKey('workouts.id'), nullable=True)
    total_time_s       = db.Column(db.Integer)
    completed          = db.Column(db.Boolean, default=True)
    notes              = db.Column(db.Text)
    done_at            = db.Column(db.DateTime, default=datetime.utcnow)
    station_results    = db.relationship('PremadeStationResult', backref='result',
                                         order_by='PremadeStationResult.station_order',
                                         lazy='dynamic', cascade='all, delete-orphan')


class PremadeStationResult(db.Model):
    __tablename__ = 'premade_station_results'
    id                = db.Column(db.Integer, primary_key=True)
    premade_result_id = db.Column(db.Integer, db.ForeignKey('premade_results.id'), nullable=False)
    station_id        = db.Column(db.Integer, db.ForeignKey('premade_stations.id'), nullable=False)
    station_order     = db.Column(db.Integer, nullable=False)
    time_s            = db.Column(db.Integer)
    reps_completed    = db.Column(db.Integer)
    effort            = db.Column(db.Numeric(3, 1))
    notes             = db.Column(db.Text)
    skipped           = db.Column(db.Boolean, default=False)
    station           = db.relationship('PremadeStation')