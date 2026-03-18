from flask import Blueprint, render_template, request, jsonify
from ..models import db, Exercise, WorkoutSet, Workout
from sqlalchemy import func
from datetime import datetime, timedelta

progress_bp = Blueprint('progress', __name__)


@progress_bp.route('')
def index():
    exercises = Exercise.query.filter(
        Exercise.category == 'strength'
    ).order_by(Exercise.name).all()

    # ── Hero stats (no selection needed) ──────────────────
    total_workouts = Workout.query.count()
    week_start     = datetime.utcnow() - timedelta(days=7)
    month_start    = datetime.utcnow() - timedelta(days=30)
    week_workouts  = Workout.query.filter(Workout.completed_at >= week_start).count()
    month_workouts = Workout.query.filter(Workout.completed_at >= month_start).count()

    # Streak — consecutive days from today backwards
    all_dates = sorted(set(
        w.completed_at.date()
        for w in Workout.query.order_by(Workout.completed_at.desc()).limit(100).all()
    ), reverse=True)
    streak = 0
    today = datetime.utcnow().date()
    check = today
    for d in all_dates:
        if d == check or d == check - timedelta(days=1):
            streak += 1
            check = d - timedelta(days=1)
        elif d < check - timedelta(days=1):
            break

    # Recent PRs — top 6 exercises by most recently logged max weight
    recent_prs = (
        db.session.query(
            Exercise.name,
            Exercise.id,
            func.max(WorkoutSet.weight_lbs).label('max_lbs'),
            func.max(Workout.completed_at).label('last_date')
        )
        .join(WorkoutSet, WorkoutSet.exercise_id == Exercise.id)
        .join(Workout, Workout.id == WorkoutSet.workout_id)
        .filter(WorkoutSet.skipped == False, WorkoutSet.weight_lbs != None)
        .group_by(Exercise.id, Exercise.name)
        .order_by(func.max(Workout.completed_at).desc())
        .limit(6)
        .all()
    )

    try:
        from ..models import PremadeWorkout
        premade_workouts = PremadeWorkout.query.order_by(PremadeWorkout.name).all()
    except Exception:
        premade_workouts = []

    return render_template('progress/index.html',
        exercises=exercises,
        premade_workouts=premade_workouts,
        total_workouts=total_workouts,
        week_workouts=week_workouts,
        month_workouts=month_workouts,
        recent_prs=recent_prs,
        streak=streak,
    )


@progress_bp.route('/data')
def data():
    ex_id = request.args.get('exercise_id', type=int)
    if not ex_id:
        return jsonify([])

    # Get all sets for this exercise ordered by date
    rows = (
        db.session.query(
            WorkoutSet.weight_lbs,
            WorkoutSet.weight_kg,
            WorkoutSet.reps,
            WorkoutSet.set_number,
            Workout.completed_at,
            Workout.id.label('workout_id'),
            Workout.name.label('workout_name'),
        )
        .join(Workout, Workout.id == WorkoutSet.workout_id)
        .filter(
            WorkoutSet.exercise_id == ex_id,
            WorkoutSet.skipped == False,
            WorkoutSet.weight_lbs != None,
        )
        .order_by(Workout.completed_at.asc())
        .all()
    )

    # Group by workout date — take the max weight lifted per session
    from collections import defaultdict
    by_date = defaultdict(lambda: {'max_lbs': 0, 'max_kg': 0, 'sets': [], 'workout_name': '', 'workout_id': 0})
    for r in rows:
        date_key = r.completed_at.strftime('%Y-%m-%d')
        entry    = by_date[date_key]
        entry['workout_name'] = r.workout_name
        entry['workout_id']   = r.workout_id
        lbs = float(r.weight_lbs) if r.weight_lbs else 0
        kg  = float(r.weight_kg)  if r.weight_kg  else 0
        if lbs > entry['max_lbs']:
            entry['max_lbs'] = lbs
            entry['max_kg']  = kg
        entry['sets'].append({
            'set': r.set_number,
            'lbs': lbs,
            'reps': r.reps,
        })

    result = []
    for date_key in sorted(by_date.keys()):
        e = by_date[date_key]
        # Volume = sum(weight_lbs * reps) for all sets this session
        volume_lbs = sum(
            s['lbs'] * s['reps'] for s in e['sets']
            if s['lbs'] and s['reps']
        )
        # Best estimated 1RM (Epley) across all sets this session
        best_1rm = 0
        for s in e['sets']:
            if s['lbs'] and s['reps']:
                r = s['reps']
                est = s['lbs'] if r == 1 else s['lbs'] * (1 + r / 30)
                if est > best_1rm:
                    best_1rm = est
        result.append({
            'date':         date_key,
            'max_lbs':      e['max_lbs'],
            'max_kg':       e['max_kg'],
            'volume_lbs':   round(volume_lbs, 1),
            'volume_kg':    round(volume_lbs / 2.20462, 1),
            'est_1rm_lbs':  round(best_1rm, 1),
            'est_1rm_kg':   round(best_1rm / 2.20462, 1),
            'sets':         e['sets'],
            'workout_name': e['workout_name'],
            'workout_id':   e['workout_id'],
        })

    return jsonify(result)


@progress_bp.route('/run-data')
def run_data():
    from ..models import Run, RunSegment
    from flask import jsonify

    # Get all runs with their segments
    runs = (
        db.session.query(Run)
        .join(Workout, Workout.id == Run.workout_id)
        .order_by(Workout.completed_at.asc())
        .all()
    )

    result = []
    for run in runs:
        workout = run.workout

        # Distance: use stored total, or sum active segments
        dist_km = float(run.total_distance_km) if run.total_distance_km else None
        if not dist_km:
            seg_total = sum(
                float(s.distance_km) for s in run.segments
                if s.distance_km and not s.skipped
            )
            dist_km = seg_total if seg_total > 0 else None

        if not dist_km:
            continue  # skip runs with no distance at all

        # Duration: use stored total, or sum active segments
        dur_s = run.total_duration_s or None
        if not dur_s:
            seg_dur = sum(
                s.duration_s for s in run.segments
                if s.duration_s and not s.skipped
            )
            dur_s = seg_dur if seg_dur > 0 else None

        # Pace per km
        pace_s   = int(dur_s / dist_km) if dur_s and dist_km else None
        pace_str = f"{pace_s//60}:{pace_s%60:02d}" if pace_s else None

        # Interval count
        interval_count = sum(1 for s in run.segments if s.segment_type == 'interval' and not s.skipped)

        result.append({
            'date':           workout.completed_at.strftime('%Y-%m-%d'),
            'distance_km':    round(dist_km, 3),
            'duration_s':     dur_s,
            'pace_s':         pace_s,
            'pace_str':       pace_str,
            'run_type':       run.run_type,
            'interval_count': interval_count,
            'workout_id':     workout.id,
            'workout_name':   workout.name,
        })

    return jsonify(result)